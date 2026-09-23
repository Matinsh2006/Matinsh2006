from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import OTPCodeForm, PhoneForm, ProfileForm
from .models import OTP, User
from .otp import OTPCooldownError, OTPExpiredError, OTPInvalidError, request_otp, verify_otp

LOGIN_PURPOSE = OTP.PURPOSE_LOGIN
CHANGE_PHONE_PURPOSE = OTP.PURPOSE_CHANGE_PHONE


def login_request(request):
    """Step 1 of login/registration: ask for a phone number and send an OTP."""
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    if request.method == "POST":
        form = PhoneForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data["phone_number"]
            try:
                request_otp(phone_number, LOGIN_PURPOSE)
            except OTPCooldownError as exc:
                messages.error(request, f"لطفاً {exc.wait_seconds} ثانیه دیگر دوباره تلاش کنید.")
            else:
                request.session["otp_phone"] = phone_number
                request.session["otp_purpose"] = LOGIN_PURPOSE
                return redirect("accounts:login_verify")
    else:
        form = PhoneForm()
    return render(request, "accounts/login.html", {"form": form})


def login_verify(request):
    """Step 2 of login/registration: check the OTP and log the user in."""
    phone_number = request.session.get("otp_phone")
    purpose = request.session.get("otp_purpose")
    if not phone_number or purpose != LOGIN_PURPOSE:
        return redirect("accounts:login")

    if request.method == "POST":
        form = OTPCodeForm(request.POST)
        if form.is_valid():
            try:
                verify_otp(phone_number, LOGIN_PURPOSE, form.cleaned_data["code"])
            except (OTPInvalidError, OTPExpiredError) as exc:
                messages.error(request, str(exc))
            else:
                user, created = User.objects.get_or_create(
                    phone_number=phone_number,
                    defaults={"is_phone_verified": True},
                )
                if not user.is_phone_verified:
                    user.is_phone_verified = True
                    user.save(update_fields=["is_phone_verified"])
                auth_login(request, user)
                request.session.pop("otp_phone", None)
                request.session.pop("otp_purpose", None)
                if created:
                    messages.success(request, "خوش آمدید! حساب کاربری شما ساخته شد.")
                else:
                    messages.success(request, "با موفقیت وارد شدید.")
                return redirect("accounts:profile")
    else:
        form = OTPCodeForm()
    return render(
        request,
        "accounts/verify.html",
        {"form": form, "phone_number": phone_number},
    )


@require_POST
def resend_otp(request):
    phone_number = request.session.get("otp_phone")
    purpose = request.session.get("otp_purpose")
    if not phone_number or not purpose:
        return redirect("accounts:login")
    try:
        request_otp(phone_number, purpose)
    except OTPCooldownError as exc:
        messages.error(request, f"لطفاً {exc.wait_seconds} ثانیه دیگر دوباره تلاش کنید.")
    else:
        messages.success(request, "کد تایید مجدداً پیامک شد.")
    if purpose == CHANGE_PHONE_PURPOSE:
        return redirect("accounts:change_phone_verify")
    return redirect("accounts:login_verify")


@require_POST
def logout_view(request):
    auth_logout(request)
    messages.success(request, "با موفقیت از حساب کاربری خارج شدید.")
    return redirect("core:home")


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "اطلاعات پروفایل به‌روزرسانی شد.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)

    appointments = request.user.appointments.select_related("service").order_by(
        "-date", "-start_time"
    )
    return render(
        request,
        "accounts/profile.html",
        {"form": form, "appointments": appointments},
    )


@login_required
def change_phone_request(request):
    if request.method == "POST":
        form = PhoneForm(request.POST)
        if form.is_valid():
            new_phone = form.cleaned_data["phone_number"]
            if new_phone == request.user.phone_number:
                form.add_error("phone_number", "این شماره همان شماره فعلی شماست.")
            elif User.objects.filter(phone_number=new_phone).exclude(pk=request.user.pk).exists():
                form.add_error("phone_number", "این شماره قبلاً در سایت ثبت شده است.")
            else:
                try:
                    request_otp(new_phone, CHANGE_PHONE_PURPOSE)
                except OTPCooldownError as exc:
                    messages.error(
                        request, f"لطفاً {exc.wait_seconds} ثانیه دیگر دوباره تلاش کنید."
                    )
                else:
                    request.session["otp_phone"] = new_phone
                    request.session["otp_purpose"] = CHANGE_PHONE_PURPOSE
                    return redirect("accounts:change_phone_verify")
    else:
        form = PhoneForm()
    return render(request, "accounts/change_phone.html", {"form": form})


@login_required
def change_phone_verify(request):
    new_phone = request.session.get("otp_phone")
    purpose = request.session.get("otp_purpose")
    if not new_phone or purpose != CHANGE_PHONE_PURPOSE:
        return redirect("accounts:change_phone_request")

    if request.method == "POST":
        form = OTPCodeForm(request.POST)
        if form.is_valid():
            try:
                verify_otp(new_phone, CHANGE_PHONE_PURPOSE, form.cleaned_data["code"])
            except (OTPInvalidError, OTPExpiredError) as exc:
                messages.error(request, str(exc))
            else:
                if User.objects.filter(phone_number=new_phone).exclude(pk=request.user.pk).exists():
                    messages.error(request, "این شماره هم‌زمان توسط شخص دیگری ثبت شد.")
                    return redirect("accounts:change_phone_request")
                request.user.phone_number = new_phone
                request.user.is_phone_verified = True
                request.user.save(update_fields=["phone_number", "is_phone_verified"])
                request.session.pop("otp_phone", None)
                request.session.pop("otp_purpose", None)
                messages.success(request, "شماره موبایل شما با موفقیت تغییر کرد.")
                return redirect("accounts:profile")
    else:
        form = OTPCodeForm()
    return render(
        request,
        "accounts/verify.html",
        {
            "form": form,
            "phone_number": new_phone,
            "is_change_phone": True,
        },
    )
