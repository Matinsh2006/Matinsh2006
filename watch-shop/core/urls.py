from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("contact/", views.contact, name="contact"),
    path("pages/<str:slug>/", views.page_detail, name="page"),
    path("robots.txt", views.robots_txt, name="robots"),
]
