from django.urls import path

from .views import chat_view

app_name = "ai_agent"

urlpatterns = [
    path("chat/", chat_view, name="chat"),
]
