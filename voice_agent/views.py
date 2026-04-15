from django.conf import settings
from django.shortcuts import render


def voice_ui_view(request):
    context = {
        "vapi_public_key": settings.VAPI_PUBLIC_KEY,
        "vapi_assistant_id": settings.VAPI_ASSISTANT_ID,
    }
    return render(request, "voice_agent/voice.html", context)
