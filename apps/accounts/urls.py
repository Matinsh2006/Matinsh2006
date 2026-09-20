from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("verify/", views.verify_view, name="verify"),
    path("resend/", views.resend_view, name="resend"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("phone/change/", views.change_phone_view, name="change_phone"),
    path("phone/verify/", views.verify_phone_view, name="phone_verify"),
]
