from django.template.loader import render_to_string
from django.templatetags.static import static


class AIAgentWidgetMiddleware:
    """
    Injects the AI Agent chat widget into every HTML response.
    Appends widget HTML, CSS, and JS just before </body>.
    This approach avoids GeoNode template inheritance complexity.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only inject into HTML responses that have a </body> tag
        content_type = response.get("Content-Type", "")
        if (
            hasattr(response, "content")
            and "text/html" in content_type
            and b"</body>" in response.content
        ):
            try:
                widget_html = render_to_string("ai_agent/widget.html", request=request)
                # v2 forces cache-bust so browsers always load the latest widget files
                _v = "v2"
                inject = (
                    f'<link rel="stylesheet" href="{static("ai_agent/css/widget.css")}?{_v}">\n'
                    f'<script>window.AI_AGENT_CHAT_URL = "/ai-agent/chat/";</script>\n'
                    f"{widget_html}\n"
                    f'<script src="{static("ai_agent/js/widget.js")}?{_v}"></script>\n'
                ).encode("utf-8")

                response.content = response.content.replace(
                    b"</body>", inject + b"</body>"
                )

                # Update Content-Length if it was set
                if response.has_header("Content-Length"):
                    response["Content-Length"] = len(response.content)

            except Exception:
                pass  # Never break pages due to widget injection errors

        return response
