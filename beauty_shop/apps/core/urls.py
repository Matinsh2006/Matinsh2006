from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("contact/", views.contact, name="contact"),
    path("page/<uslug:slug>/", views.page_detail, name="page"),
    path("editor/upload/", views.editor_upload, name="editor_upload"),
]
