import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .agent import run_agent


@csrf_exempt  # Read-only endpoint — same pattern as GeoNode's /api/v2/ endpoints
@require_POST
def chat_view(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    message = body.get("message", "").strip()
    if not message:
        return JsonResponse({"error": "Empty message"}, status=400)

    history = body.get("history", [])
    if not isinstance(history, list):
        history = []

    site_url = getattr(settings, "SITEURL", request.build_absolute_uri("/")).rstrip("/")

    try:
        reply = run_agent(
            user_message=message,
            conversation_history=history,
            base_url=site_url,
        )
        return JsonResponse({"reply": reply})
    except Exception as exc:
        return JsonResponse({"error": "Agent error", "detail": str(exc)}, status=500)
