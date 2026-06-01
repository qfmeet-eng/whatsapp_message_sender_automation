from django.urls import path

from . import views


app_name = "sender"

urlpatterns = [
    path("", views.index, name="index"),
    path("start/", views.start, name="start"),
    path("stop/", views.stop, name="stop"),
    path("status/", views.status, name="status"),
]
