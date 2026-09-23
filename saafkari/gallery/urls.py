from django.urls import path

from . import views

app_name = "gallery"

urlpatterns = [
    path("", views.portfolio_list, name="list"),
    path("<str:slug>/", views.portfolio_detail, name="detail"),
]
