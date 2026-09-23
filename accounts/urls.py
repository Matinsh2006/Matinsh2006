from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_request, name="login"),
    path("login/verify/", views.login_verify, name="login_verify"),
    path("logout/", views.logout_view, name="logout"),
    path("otp/resend/", views.resend_otp, name="resend_otp"),
    path("profile/", views.profile, name="profile"),
    path("profile/change-phone/", views.change_phone_request, name="change_phone_request"),
    path(
        "profile/change-phone/verify/",
        views.change_phone_verify,
        name="change_phone_verify",
    ),
]
