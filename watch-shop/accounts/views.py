from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.utils import fa_digits

from . import otp as otp_service
from .forms import AddressForm, ChangePhoneForm, OTPForm, PhoneForm, ProfileForm
from .models import Address, OneTimePassword, User
from .sms import is_console_backend
from .utils import client_ip, mask_phone

SESSION_LOGIN_PHONE = "otp_login_phone"
SESSION_NEXT = "otp_next"
SESSION_NEW_PHONE = "otp_new_phone"
AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"
LOGIN = OneTimePassword.Purpose.LOGIN
CHANGE_PHONE = OneTimePassword.Purpose.CHANGE_PHONE


def _safe_next(request, fallback=""):
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return fallback


def _flash_debug_code(request, code):
    """In development (console SMS backend) show the code so the flow is testable."""
    if settings.OTP_DEBUG_SHOW_CODE and is_console_backend():
        messages.info(request, f"حالت آزمایشی پنل پیامکی — کد تایید شما: {fa_digits(code)}")


def _otp_context(phone, purpose):
    return {
        "phone": phone,
        "masked_phone": mask_phone(phone),
        "resend_in": otp_service.seconds_until_resend(phone, purpose),
        "otp_length": settings.OTP_LENGTH,
        "otp_ttl": settings.OTP_TTL_SECONDS,
        "purpose": purpose,
    }


# ---------------------------------------------------------------------------
# Login / sign-up with a one-time SMS code
# ---------------------------------------------------------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect(_safe_next(request, reverse("accounts:profile")))

    form = PhoneForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        try:
            _, code = otp_service.send_otp(phone, LOGIN, ip=client_ip(request))
        except otp_service.OTPError as exc:
            if exc.wait_seconds:
                # A code was sent moments ago: continue with it.
                request.session[SESSION_LOGIN_PHONE] = phone
                request.session[SESSION_NEXT] = _safe_next(request)
                messages.info(request, exc.message)
                return redirect("accounts:verify")
            form.add_error("phone", exc.message)
        else:
            request.session[SESSION_LOGIN_PHONE] = phone
            request.session[SESSION_NEXT] = _safe_next(request)
            messages.success(request, f"کد تایید به شماره {fa_digits(mask_phone(phone))} پیامک شد.")
            _flash_debug_code(request, code)
            return redirect("accounts:verify")

    return render(request, "accounts/login.html", {"form": form, "next": _safe_next(request)})


def verify_view(request):
    phone = request.session.get(SESSION_LOGIN_PHONE)
    if not phone:
        return redirect("accounts:login")

    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            otp_service.verify_otp(phone, LOGIN, form.cleaned_data["code"])
        except otp_service.OTPError as exc:
            form.add_error("code", exc.message)
        else:
            user = User.objects.filter(phone=phone).first()
            created = user is None
            if created:
                try:
                    user = User.objects.create_user(phone=phone)
                except IntegrityError:
                    user, created = User.objects.get(phone=phone), False

            if not user.is_active:
                form.add_error(None, "حساب کاربری شما غیرفعال شده است. لطفاً با پشتیبانی تماس بگیرید.")
            else:
                user.phone_verified_at = timezone.now()
                user.save(update_fields=["phone_verified_at"])
                next_url = request.session.pop(SESSION_NEXT, "")
                request.session.pop(SESSION_LOGIN_PHONE, None)
                login(request, user, backend=AUTH_BACKEND)

                if created or not user.has_complete_profile:
                    messages.success(request, "حساب کاربری شما ساخته شد؛ لطفاً نام خود را تکمیل کنید.")
                    edit_url = reverse("accounts:profile_edit")
                    return redirect(f"{edit_url}?next={next_url}" if next_url else edit_url)
                messages.success(request, f"{user.get_short_name()} عزیز، خوش آمدید.")
                return redirect(next_url or "accounts:profile")

    return render(request, "accounts/verify.html", {"form": form, **_otp_context(phone, LOGIN)})


@require_POST
def resend_view(request):
    purpose = request.POST.get("purpose")
    if purpose == CHANGE_PHONE:
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        phone, user = request.session.get(SESSION_NEW_PHONE), request.user
        back, start = "accounts:change_phone_verify", "accounts:change_phone"
    else:
        purpose = LOGIN
        phone, user = request.session.get(SESSION_LOGIN_PHONE), None
        back, start = "accounts:verify", "accounts:login"

    if not phone:
        return redirect(start)
    try:
        _, code = otp_service.send_otp(phone, purpose, user=user, ip=client_ip(request))
    except otp_service.OTPError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, "کد تایید جدید ارسال شد.")
        _flash_debug_code(request, code)
    return redirect(back)


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "از حساب کاربری خود خارج شدید.")
    return redirect("core:home")


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@login_required
def profile_view(request):
    orders = request.user.orders.prefetch_related("items")[:5]
    return render(
        request,
        "accounts/profile.html",
        {"orders": orders, "addresses": request.user.addresses.all()},
    )


@login_required
def profile_edit_view(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "اطلاعات حساب شما ذخیره شد.")
        return redirect(_safe_next(request, reverse("accounts:profile")))
    return render(request, "accounts/profile_edit.html", {"form": form, "next": _safe_next(request)})


# ---------------------------------------------------------------------------
# Changing the phone number (= username) after SMS verification
# ---------------------------------------------------------------------------
@login_required
def change_phone_view(request):
    form = ChangePhoneForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        new_phone = form.cleaned_data["phone"]
        try:
            _, code = otp_service.send_otp(
                new_phone, CHANGE_PHONE, user=request.user, ip=client_ip(request)
            )
        except otp_service.OTPError as exc:
            if exc.wait_seconds and request.session.get(SESSION_NEW_PHONE) == new_phone:
                messages.info(request, exc.message)
                return redirect("accounts:change_phone_verify")
            form.add_error("phone", exc.message)
        else:
            request.session[SESSION_NEW_PHONE] = new_phone
            messages.success(
                request, f"کد تایید به شماره جدید {fa_digits(mask_phone(new_phone))} پیامک شد."
            )
            _flash_debug_code(request, code)
            return redirect("accounts:change_phone_verify")

    return render(request, "accounts/change_phone.html", {"form": form, "step": 1})


@login_required
def change_phone_verify_view(request):
    new_phone = request.session.get(SESSION_NEW_PHONE)
    if not new_phone:
        return redirect("accounts:change_phone")

    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            otp_service.verify_otp(new_phone, CHANGE_PHONE, form.cleaned_data["code"], user=request.user)
        except otp_service.OTPError as exc:
            form.add_error("code", exc.message)
        else:
            user = request.user
            try:
                with transaction.atomic():
                    if User.objects.filter(phone=new_phone).exclude(pk=user.pk).exists():
                        raise IntegrityError
                    user.phone = new_phone
                    user.phone_verified_at = timezone.now()
                    user.save(update_fields=["phone", "phone_verified_at"])
            except IntegrityError:
                form.add_error("code", "این شماره در این فاصله برای حساب دیگری ثبت شده است.")
            else:
                request.session.pop(SESSION_NEW_PHONE, None)
                messages.success(
                    request, f"نام کاربری شما با موفقیت به {fa_digits(new_phone)} تغییر کرد."
                )
                return redirect("accounts:profile")

    return render(
        request,
        "accounts/change_phone.html",
        {"form": form, "step": 2, **_otp_context(new_phone, CHANGE_PHONE)},
    )


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------
@login_required
def address_create(request):
    user = request.user
    form = AddressForm(
        request.POST or None,
        initial={"recipient_name": user.get_full_name(), "recipient_phone": user.phone},
    )
    if request.method == "POST" and form.is_valid():
        address = form.save(commit=False)
        address.user = user
        address.save()
        messages.success(request, "نشانی جدید ذخیره شد.")
        return redirect(_safe_next(request, reverse("accounts:profile") + "#addresses"))
    return render(request, "accounts/address_form.html", {"form": form, "next": _safe_next(request)})


@login_required
def address_update(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    form = AddressForm(request.POST or None, instance=address)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "نشانی ویرایش شد.")
        return redirect(_safe_next(request, reverse("accounts:profile") + "#addresses"))
    return render(
        request,
        "accounts/address_form.html",
        {"form": form, "address": address, "next": _safe_next(request)},
    )


@login_required
@require_POST
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    was_default = address.is_default
    address.delete()
    if was_default:
        replacement = request.user.addresses.order_by("-created_at").first()
        if replacement:
            replacement.is_default = True
            replacement.save()
    messages.info(request, "نشانی حذف شد.")
    return redirect(_safe_next(request, reverse("accounts:profile") + "#addresses"))
