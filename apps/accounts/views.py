from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.orders.models import Order

from .forms import ChangePhoneForm, OTPForm, PhoneForm, ProfileForm
from .models import OTPCode, OTPPurpose, User
from .sms import send_otp

SESSION_PHONE = "otp_phone"
SESSION_PURPOSE = "otp_purpose"
SESSION_NEXT = "otp_next"


def _issue_code(request, phone, purpose, user=None):
    """ساخت و ارسال کد یکبارمصرف و نگه‌داشتن وضعیت در سشن."""
    otp = OTPCode.generate(phone, purpose=purpose, user=user)
    send_otp(phone, otp.code)
    request.session[SESSION_PHONE] = phone
    request.session[SESSION_PURPOSE] = purpose
    if settings.SMS_BACKEND == "console":
        messages.info(request, f"حالت دمو: کد تایید شما {otp.code} است.")
    else:
        messages.success(request, "کد تایید پیامک شد.")
    return otp


@require_http_methods(["GET", "POST"])
def login_view(request):
    """گام اول ورود/ثبت‌نام با شماره موبایل."""
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    form = PhoneForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        last = OTPCode.last_for(phone, OTPPurpose.LOGIN)
        if last and not last.can_resend and not last.is_used:
            messages.warning(
                request, f"کد قبلی هنوز معتبر است؛ {last.seconds_left} ثانیه دیگر دوباره تلاش کنید."
            )
        else:
            _issue_code(request, phone, OTPPurpose.LOGIN)
        request.session[SESSION_PHONE] = phone
        request.session[SESSION_PURPOSE] = OTPPurpose.LOGIN
        if request.GET.get("next"):
            request.session[SESSION_NEXT] = request.GET["next"]
        return redirect("accounts:verify")

    return render(request, "accounts/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_view(request):
    """گام دوم ورود: بررسی کد پیامکی و ساخت کاربر در صورت نیاز."""
    phone = request.session.get(SESSION_PHONE)
    if not phone:
        messages.error(request, "ابتدا شماره موبایل خود را وارد کنید.")
        return redirect("accounts:login")

    otp = OTPCode.last_for(phone, OTPPurpose.LOGIN)
    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if otp is None or not otp.verify(form.cleaned_data["code"]):
            messages.error(request, "کد وارد شده نادرست یا منقضی شده است.")
        else:
            user, created = User.objects.get_or_create(phone=phone)
            user.phone_verified = True
            user.save(update_fields=["phone_verified"])
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(
                request, "خوش آمدید! حساب شما ساخته شد." if created else "با موفقیت وارد شدید."
            )
            next_url = request.session.pop(SESSION_NEXT, None)
            request.session.pop(SESSION_PHONE, None)
            request.session.pop(SESSION_PURPOSE, None)
            return redirect(next_url or reverse("accounts:profile"))

    context = {
        "form": form,
        "phone": phone,
        "seconds_left": otp.seconds_left if otp else 0,
        "resend_url": reverse("accounts:resend"),
    }
    return render(request, "accounts/verify.html", context)


@require_http_methods(["POST", "GET"])
def resend_view(request):
    """ارسال دوباره کد برای همان شماره ثبت‌شده در سشن."""
    phone = request.session.get(SESSION_PHONE)
    purpose = request.session.get(SESSION_PURPOSE, OTPPurpose.LOGIN)
    if not phone:
        return redirect("accounts:login")

    last = OTPCode.last_for(phone, purpose)
    if last and not last.can_resend:
        messages.warning(request, f"تا ارسال دوباره {settings.OTP_RESEND_SECONDS} ثانیه صبر کنید.")
    else:
        _issue_code(
            request,
            phone,
            purpose,
            user=request.user if request.user.is_authenticated else None,
        )
    target = "accounts:phone_verify" if purpose == OTPPurpose.CHANGE_PHONE else "accounts:verify"
    return redirect(target)


def logout_view(request):
    logout(request)
    messages.info(request, "از حساب خود خارج شدید.")
    return redirect("core:home")


@login_required
def profile_view(request):
    """صفحه پروفایل کاربری."""
    profile = request.user.profile
    form = ProfileForm(
        request.POST or None, request.FILES or None, instance=profile
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "اطلاعات پروفایل به‌روزرسانی شد.")
        return redirect("accounts:profile")

    orders = Order.objects.filter(user=request.user).prefetch_related("items")[:10]
    return render(request, "accounts/profile.html", {"form": form, "orders": orders})


@login_required
@require_http_methods(["GET", "POST"])
def change_phone_view(request):
    """گام اول تغییر نام کاربری (شماره موبایل)."""
    form = ChangePhoneForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        _issue_code(request, phone, OTPPurpose.CHANGE_PHONE, user=request.user)
        return redirect("accounts:phone_verify")
    return render(request, "accounts/change_phone.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def verify_phone_view(request):
    """گام دوم تغییر شماره: تایید کد پیامکی و ثبت شماره جدید."""
    phone = request.session.get(SESSION_PHONE)
    if not phone or request.session.get(SESSION_PURPOSE) != OTPPurpose.CHANGE_PHONE:
        return redirect("accounts:change_phone")

    otp = OTPCode.last_for(phone, OTPPurpose.CHANGE_PHONE)
    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if otp is None or otp.user_id != request.user.id or not otp.verify(form.cleaned_data["code"]):
            messages.error(request, "کد وارد شده نادرست یا منقضی شده است.")
        elif User.objects.filter(phone=phone).exclude(pk=request.user.pk).exists():
            messages.error(request, "این شماره در فاصله تایید توسط کاربر دیگری ثبت شد.")
        else:
            request.user.phone = phone
            request.user.phone_verified = True
            request.user.save(update_fields=["phone", "phone_verified"])
            request.session.pop(SESSION_PHONE, None)
            request.session.pop(SESSION_PURPOSE, None)
            messages.success(request, "نام کاربری (شماره موبایل) شما با موفقیت تغییر کرد.")
            return redirect("accounts:profile")

    context = {
        "form": form,
        "phone": phone,
        "seconds_left": otp.seconds_left if otp else 0,
        "is_change_phone": True,
        "resend_url": reverse("accounts:resend"),
    }
    return render(request, "accounts/verify.html", context)
