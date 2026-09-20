from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("start/<str:ref_code>/", views.start, name="start"),
    path("sandbox/<int:payment_id>/", views.sandbox, name="sandbox"),
    path("callback/<int:payment_id>/", views.callback, name="callback"),
    path("result/<str:ref_code>/", views.result, name="result"),
]
