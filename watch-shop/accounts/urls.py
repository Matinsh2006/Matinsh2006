from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("verify/", views.verify_view, name="verify"),
    path("resend/", views.resend_view, name="resend"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.profile_view, name="profile"),
    path("edit/", views.profile_edit_view, name="profile_edit"),
    path("phone/", views.change_phone_view, name="change_phone"),
    path("phone/verify/", views.change_phone_verify_view, name="change_phone_verify"),
    path("addresses/new/", views.address_create, name="address_create"),
    path("addresses/<int:pk>/edit/", views.address_update, name="address_update"),
    path("addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),
]
