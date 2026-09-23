from django.urls import path

from . import views

app_name = "appointments"

urlpatterns = [
    path("", views.booking_view, name="booking"),
    path("slots/", views.slots_api, name="slots"),
    path("mine/", views.my_appointments, name="mine"),
    path("track/", views.track_view, name="track"),
    path("<str:code>/", views.appointment_detail, name="detail"),
    path("<str:code>/cancel/", views.cancel_appointment, name="cancel"),
]
