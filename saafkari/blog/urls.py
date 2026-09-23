from django.urls import path

from . import views

app_name = "blog"

urlpatterns = [
    path("", views.article_list, name="list"),
    path("<str:slug>/", views.article_detail, name="detail"),
]
