from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("success/<int:pk>/", views.booking_success, name="success"),
    path("api/available-slots/", views.available_slots_api, name="available_slots_api"),
    path("<str:slug>/", views.book_service, name="book"),
]
