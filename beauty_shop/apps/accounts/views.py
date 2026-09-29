from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.utils.text import mask_phone, to_persian_digits

from . import otp
from .forms import AddressForm, ChangePhoneForm, OTPForm, PhoneForm, ProfileForm
from .models import Address, OTPCode, User
from .utils import get_client_ip, get_safe_next_url

SESSION_AUTH_PHONE = "auth_phone"
SESSION_AUTH_NEXT = "auth_next"
SESSION_NEW_PHONE = "change_phone_new"

LOGIN = OTPCode.Purpose.LOGIN
CHANGE_PHONE = OTPCode.Purpose.CHANGE_PHONE


def _announce_code(request, phone, code):
    # LRI…PDI keeps the masked number left-to-right inside the Persian sentence.
    masked = f"\u2066{to_persian_digits(mask_phone(phone))}\u2069"
    messages.success(request, f"کد تایید به شماره {masked} پیامک شد.")
    if settings.OTP_SHOW_CODE_IN_MESSAGE and code:
        messages.info(request, f"حالت آزمایشی — کد تایید: {code}")


def _issue_code(request, form, phone, purpose, user=None):
    """Send a code; on throttling fall back to the still-valid code. Returns success."""
    try:
        code = otp.send_code(phone, purpose, user=user, ip=get_client_ip(request))
    except otp.OTPThrottled as exc:
        if not otp.has_active_code(phone, purpose, user=user):
            form.add_error("phone", str(exc))
            return False
        messages.info(request, "کد تایید قبلاً برای شما ارسال شده است؛ همان کد را وارد کنید.")
    except otp.OTPError as exc:
        form.add_error("phone", str(exc))
        return False
    else:
        _announce_code(request, phone, code)
    return True


def _resend_code(request, phone, purpose, user=None):
    try:
        code = otp.send_code(phone, purpose, user=user, ip=get_client_ip(request))
    except otp.OTPError as exc:
        messages.error(request, str(exc))
    else:
        _announce_code(request, phone, code)


# --- Login / sign-up ---------------------------------------------------------


@require_http_methods(["GET", "POST"])
def login_view(request):
    next_url = get_safe_next_url(request, request.POST.get("next") or request.GET.get("next"))
    if request.user.is_authenticated:
        return redirect(next_url or "accounts:profile")

    form = PhoneForm(request.POST or None, initial={"phone": request.session.get(SESSION_AUTH_PHONE, "")})
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        if _issue_code(request, form, phone, LOGIN):
            request.session[SESSION_AUTH_PHONE] = phone
            request.session[SESSION_AUTH_NEXT] = next_url
            return redirect("accounts:verify")
    return render(request, "accounts/login.html", {"form": form, "next": next_url})


@require_http_methods(["GET", "POST"])
def verify_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")
    phone = request.session.get(SESSION_AUTH_PHONE)
    if not phone:
        return redirect("accounts:login")

    if request.method == "POST" and request.POST.get("action") == "resend":
        _resend_code(request, phone, LOGIN)
        return redirect("accounts:verify")

    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            otp.verify_code(phone, LOGIN, form.cleaned_data["code"])
        except otp.OTPError as exc:
            form.add_error("code", str(exc))
        else:
            user, created = _get_or_create_user(phone)
            if not user.is_active:
                form.add_error(None, "حساب کاربری شما غیرفعال شده است. لطفاً با پشتیبانی تماس بگیرید.")
            else:
                return _complete_login(request, user, created)

    context = {
        "form": form,
        "phone": phone,
        "resend_wait": otp.resend_wait_seconds(phone, LOGIN),
        "otp_length": settings.OTP_LENGTH,
    }
    return render(request, "accounts/verify.html", context)


def _get_or_create_user(phone):
    user = User.objects.filter(phone=phone).first()
    if user is not None:
        return user, False
    try:
        with transaction.atomic():
            return User.objects.create_user(phone=phone), True
    except IntegrityError:  # created concurrently
        return User.objects.get(phone=phone), False


def _complete_login(request, user, created):
    next_url = request.session.pop(SESSION_AUTH_NEXT, "")
    request.session.pop(SESSION_AUTH_PHONE, None)
    user.phone_verified_at = timezone.now()
    user.save(update_fields=["phone_verified_at"])
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    if created or not user.is_profile_complete:
        messages.success(request, "خوش آمدید! لطفاً نام و نام خانوادگی خود را برای تکمیل پروفایل وارد کنید.")
        url = reverse("accounts:profile_edit")
        return redirect(f"{url}?{urlencode({'next': next_url})}" if next_url else url)
    messages.success(request, f"{user.get_short_name()} عزیز، خوش آمدید.")
    return redirect(next_url or "accounts:profile")


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "از حساب کاربری خود خارج شدید.")
    return redirect("core:home")


# --- Profile -----------------------------------------------------------------


@login_required
def profile_view(request):
    context = {
        "recent_orders": request.user.orders.prefetch_related("items").order_by("-created_at")[:3],
        "addresses_count": request.user.addresses.count(),
        "orders_count": request.user.orders.count(),
    }
    return render(request, "accounts/profile.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit_view(request):
    next_url = get_safe_next_url(request, request.POST.get("next") or request.GET.get("next"))
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "اطلاعات حساب کاربری شما ذخیره شد.")
        return redirect(next_url or "accounts:profile")
    return render(request, "accounts/profile_edit.html", {"form": form, "next": next_url})


# --- Change phone number (verified by SMS to the new number) -----------------


@login_required
@require_http_methods(["GET", "POST"])
def change_phone_view(request):
    form = ChangePhoneForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        new_phone = form.cleaned_data["phone"]
        if _issue_code(request, form, new_phone, CHANGE_PHONE, user=request.user):
            request.session[SESSION_NEW_PHONE] = new_phone
            return redirect("accounts:change_phone_verify")
    return render(request, "accounts/change_phone.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def change_phone_verify_view(request):
    new_phone = request.session.get(SESSION_NEW_PHONE)
    if not new_phone:
        return redirect("accounts:change_phone")
    user = request.user

    if request.method == "POST" and request.POST.get("action") == "resend":
        _resend_code(request, new_phone, CHANGE_PHONE, user=user)
        return redirect("accounts:change_phone_verify")

    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            otp.verify_code(new_phone, CHANGE_PHONE, form.cleaned_data["code"], user=user)
            old_phone = user.phone
            user.phone = new_phone
            user.phone_verified_at = timezone.now()
            with transaction.atomic():
                user.save(update_fields=["phone", "phone_verified_at"])
        except otp.OTPError as exc:
            form.add_error("code", str(exc))
        except IntegrityError:
            user.refresh_from_db()
            form.add_error(None, "این شماره همزمان توسط حساب دیگری ثبت شده است.")
        else:
            request.session.pop(SESSION_NEW_PHONE, None)
            messages.success(
                request,
                f"شماره موبایل شما از {to_persian_digits(old_phone)} به {to_persian_digits(new_phone)} تغییر کرد. "
                "از این پس با شماره جدید وارد شوید.",
            )
            return redirect("accounts:profile")

    context = {
        "form": form,
        "phone": new_phone,
        "resend_wait": otp.resend_wait_seconds(new_phone, CHANGE_PHONE),
        "otp_length": settings.OTP_LENGTH,
    }
    return render(request, "accounts/change_phone_verify.html", context)


# --- Addresses -----------------------------------------------------------------


@login_required
def address_list_view(request):
    return render(request, "accounts/address_list.html", {"addresses": request.user.addresses.all()})


@login_required
@require_http_methods(["GET", "POST"])
def address_create_view(request):
    next_url = get_safe_next_url(request, request.POST.get("next") or request.GET.get("next"))
    initial = {"receiver_name": request.user.get_full_name(), "receiver_phone": request.user.phone}
    form = AddressForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        address.save()
        messages.success(request, "آدرس جدید ذخیره شد.")
        return redirect(next_url or "accounts:address_list")
    return render(request, "accounts/address_form.html", {"form": form, "next": next_url, "is_new": True})


@login_required
@require_http_methods(["GET", "POST"])
def address_update_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    next_url = get_safe_next_url(request, request.POST.get("next") or request.GET.get("next"))
    form = AddressForm(request.POST or None, instance=address)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "آدرس ویرایش شد.")
        return redirect(next_url or "accounts:address_list")
    return render(request, "accounts/address_form.html", {"form": form, "next": next_url, "is_new": False})


@login_required
@require_POST
def address_delete_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    was_default = address.is_default
    address.delete()
    if was_default:
        replacement = request.user.addresses.first()
        if replacement:
            replacement.is_default = True
            replacement.save(update_fields=["is_default"])
    messages.info(request, "آدرس حذف شد.")
    return redirect("accounts:address_list")


@login_required
@require_POST
def address_set_default_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, "آدرس پیش‌فرض تغییر کرد.")
    return redirect("accounts:address_list")
