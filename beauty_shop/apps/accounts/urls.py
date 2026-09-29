from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("verify/", views.verify_view, name="verify"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.profile_view, name="profile"),
    path("edit/", views.profile_edit_view, name="profile_edit"),
    path("change-phone/", views.change_phone_view, name="change_phone"),
    path("change-phone/verify/", views.change_phone_verify_view, name="change_phone_verify"),
    path("addresses/", views.address_list_view, name="address_list"),
    path("addresses/new/", views.address_create_view, name="address_create"),
    path("addresses/<int:pk>/edit/", views.address_update_view, name="address_update"),
    path("addresses/<int:pk>/delete/", views.address_delete_view, name="address_delete"),
    path("addresses/<int:pk>/default/", views.address_set_default_view, name="address_set_default"),
]
