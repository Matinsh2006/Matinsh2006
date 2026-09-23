"""نشانی‌های ورود، پروفایل و تغییر شماره."""
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("login/verify/", views.login_verify_view, name="login_verify"),
    path("login/resend/", views.resend_code_view, name="resend_code"),
    path("login/staff/", views.staff_login_view, name="staff_login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit_view, name="profile_edit"),
    path("profile/phone/", views.phone_change_view, name="phone_change"),
    path("profile/phone/verify/", views.phone_change_verify_view, name="phone_change_verify"),
]
