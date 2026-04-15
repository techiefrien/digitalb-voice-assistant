from django.urls import path
from . import views
from .webhook import vapi_webhook

urlpatterns = [
    path("", views.voice_ui_view, name="voice_index"),
    path("webhook/", vapi_webhook , name="vapi_webhook"),
]

