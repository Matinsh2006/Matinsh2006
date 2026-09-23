"""ورود با کد پیامکی، پروفایل کاربری و تغییر شماره موبایل."""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from core.validators import mask_phone

from .forms import OTPVerifyForm, PhoneChangeForm, PhoneForm, ProfileForm, StaffLoginForm
from .models import OTPCode, OTPPurpose
from .otp import client_ip, request_otp, verify_otp
from .sms import send_sms

User = get_user_model()

SESSION_PHONE = "otp_phone"
SESSION_PURPOSE = "otp_purpose"
SESSION_NEXT = "otp_next"


def _safe_next(request, fallback: str) -> str:
    """بررسی امن بودن نشانی بازگشت پس از ورود."""
    candidate = request.POST.get("next") or request.GET.get("next") or request.session.get(SESSION_NEXT)
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return fallback


def _otp_context(phone: str, purpose: str, **extra) -> dict:
    """اطلاعات لازم برای صفحه‌ی ورود کد (زمان انقضا و شمارش معکوس)."""
    otp = OTPCode.last_for(phone, purpose)
    context = {
        "phone": phone,
        "masked_phone": mask_phone(phone),
        "seconds_left": otp.seconds_left if otp else 0,
        "resend_seconds": otp.resend_seconds_left if otp else 0,
        "code_length": settings.OTP_LENGTH,
    }
    context.update(extra)
    return context


# ---------------------------------------------------------------------------
# ورود و ثبت‌نام با کد پیامکی
# ---------------------------------------------------------------------------
@require_http_methods(["GET", "POST"])
def login_view(request):
    """مرحله‌ی اول ورود: گرفتن شماره موبایل و ارسال کد."""
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    form = PhoneForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        result = request_otp(phone, OTPPurpose.LOGIN, ip=client_ip(request))
        if result.ok:
            request.session[SESSION_PHONE] = phone
            request.session[SESSION_PURPOSE] = OTPPurpose.LOGIN
            request.session[SESSION_NEXT] = _safe_next(request, reverse("accounts:profile"))
            messages.success(request, f"کد تایید به شماره {mask_phone(phone)} پیامک شد.")
            if result.debug_code:
                messages.info(request, f"حالت توسعه — کد تایید: {result.debug_code}")
            return redirect("accounts:login_verify")
        messages.error(request, result.error)

    return render(request, "accounts/login.html", {"form": form, "next": request.GET.get("next", "")})


@require_http_methods(["GET", "POST"])
def login_verify_view(request):
    """مرحله‌ی دوم ورود: بررسی کد و ساخت/ورود کاربر."""
    phone = request.session.get(SESSION_PHONE)
    if not phone or request.session.get(SESSION_PURPOSE) != OTPPurpose.LOGIN:
        messages.info(request, "ابتدا شماره موبایل خود را وارد کنید.")
        return redirect("accounts:login")

    form = OTPVerifyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ok, error = verify_otp(phone, OTPPurpose.LOGIN, form.cleaned_data["code"])
        if ok:
            user, created = User.objects.get_or_create(phone=phone, defaults={"is_phone_verified": True})
            if not user.is_active:
                messages.error(request, "حساب کاربری شما غیرفعال است. با مغازه تماس بگیرید.")
                return redirect("core:home")
            if not user.is_phone_verified:
                user.is_phone_verified = True
                user.save(update_fields=["is_phone_verified"])
            login(request, user, backend="accounts.backends.PhoneBackend")
            destination = request.session.pop(SESSION_NEXT, None) or reverse("accounts:profile")
            request.session.pop(SESSION_PHONE, None)
            request.session.pop(SESSION_PURPOSE, None)
            if created:
                messages.success(request, "خوش آمدید! حساب شما ساخته شد. نام خود را کامل کنید.")
                return redirect("accounts:profile_edit")
            messages.success(request, "خوش آمدید 🌟")
            return redirect(destination)
        messages.error(request, error)

    return render(request, "accounts/verify.html", _otp_context(phone, OTPPurpose.LOGIN, form=form, mode="login"))


@require_http_methods(["POST"])
def resend_code_view(request):
    """ارسال دوباره‌ی کد تایید برای همان مرحله‌ی در جریان."""
    phone = request.session.get(SESSION_PHONE)
    purpose = request.session.get(SESSION_PURPOSE)
    if not phone or not purpose:
        return redirect("accounts:login")

    user = request.user if request.user.is_authenticated else None
    result = request_otp(phone, purpose, user=user, ip=client_ip(request))
    if result.ok:
        messages.success(request, "کد تایید دوباره ارسال شد.")
        if result.debug_code:
            messages.info(request, f"حالت توسعه — کد تایید: {result.debug_code}")
    else:
        messages.error(request, result.error)
    target = "accounts:phone_change_verify" if purpose == OTPPurpose.PHONE_CHANGE else "accounts:login_verify"
    return redirect(target)


@require_http_methods(["GET", "POST"])
def staff_login_view(request):
    """ورود کارفرما/کارکنان با رمز عبور (بدون نیاز به پیامک)."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("dashboard:home")

    form = StaffLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request, username=form.cleaned_data["phone"], password=form.cleaned_data["password"]
        )
        if user is None:
            messages.error(request, "شماره موبایل یا رمز عبور درست نیست.")
        elif not user.is_staff:
            messages.error(request, "این حساب دسترسی پنل مدیریت ندارد.")
        else:
            login(request, user, backend="accounts.backends.PhoneBackend")
            messages.success(request, "به پنل مدیریت خوش آمدید.")
            return redirect(_safe_next(request, reverse("dashboard:home")))

    return render(request, "accounts/staff_login.html", {"form": form})


@require_http_methods(["POST", "GET"])
def logout_view(request):
    """خروج از حساب کاربری."""
    logout(request)
    messages.success(request, "از حساب خود خارج شدید.")
    return redirect("core:home")


# ---------------------------------------------------------------------------
# پروفایل کاربری
# ---------------------------------------------------------------------------
@login_required
def profile_view(request):
    """صفحه‌ی پروفایل: اطلاعات کاربر، نوبت‌ها و پرداخت‌ها."""
    appointments = (
        request.user.appointments.select_related("service")
        .prefetch_related("photos", "payments")
        .order_by("-date", "-start_time")[:10]
    )
    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": request.user,
            "appointments": appointments,
            "appointment_count": request.user.appointments.count(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit_view(request):
    """ویرایش نام، تصویر و مشخصات خودرو."""
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "اطلاعات پروفایل ذخیره شد.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile_edit.html", {"form": form})


# ---------------------------------------------------------------------------
# تغییر شماره موبایل (نام کاربری) با تایید پیامکی
# ---------------------------------------------------------------------------
@login_required
@require_http_methods(["GET", "POST"])
def phone_change_view(request):
    """مرحله‌ی اول تغییر شماره: گرفتن شماره‌ی جدید و ارسال کد به آن."""
    form = PhoneChangeForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        new_phone = form.cleaned_data["new_phone"]
        result = request_otp(new_phone, OTPPurpose.PHONE_CHANGE, user=request.user, ip=client_ip(request))
        if result.ok:
            request.session[SESSION_PHONE] = new_phone
            request.session[SESSION_PURPOSE] = OTPPurpose.PHONE_CHANGE
            messages.success(request, f"کد تایید به شماره‌ی جدید {mask_phone(new_phone)} پیامک شد.")
            if result.debug_code:
                messages.info(request, f"حالت توسعه — کد تایید: {result.debug_code}")
            return redirect("accounts:phone_change_verify")
        messages.error(request, result.error)
    return render(request, "accounts/phone_change.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def phone_change_verify_view(request):
    """مرحله‌ی دوم تغییر شماره: بررسی کد و ثبت شماره‌ی جدید."""
    new_phone = request.session.get(SESSION_PHONE)
    if not new_phone or request.session.get(SESSION_PURPOSE) != OTPPurpose.PHONE_CHANGE:
        return redirect("accounts:phone_change")

    form = OTPVerifyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ok, error = verify_otp(new_phone, OTPPurpose.PHONE_CHANGE, form.cleaned_data["code"])
        if ok:
            if User.objects.filter(phone=new_phone).exclude(pk=request.user.pk).exists():
                messages.error(request, "این شماره در فاصله‌ی تایید، توسط کاربر دیگری ثبت شد.")
                return redirect("accounts:phone_change")
            old_phone = request.user.phone
            request.user.phone = new_phone
            request.user.is_phone_verified = True
            request.user.phone_changed_at = timezone.now()
            request.user.save(update_fields=["phone", "is_phone_verified", "phone_changed_at"])
            update_session_auth_hash(request, request.user)
            request.session.pop(SESSION_PHONE, None)
            request.session.pop(SESSION_PURPOSE, None)
            try:
                send_sms(old_phone, f"شماره‌ی حساب شما به {mask_phone(new_phone)} تغییر کرد.")
            except Exception:  # pragma: no cover - خطای پنل نباید مانع تغییر شود
                pass
            messages.success(request, "شماره موبایل (نام کاربری) شما با موفقیت تغییر کرد.")
            return redirect("accounts:profile")
        messages.error(request, error)

    context = _otp_context(new_phone, OTPPurpose.PHONE_CHANGE, form=form, mode="phone_change")
    return render(request, "accounts/verify.html", context)
