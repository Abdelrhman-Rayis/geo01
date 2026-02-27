import os
import requests
import anthropic
from django.conf import settings

CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 1024

SEARCH_LAYERS_TOOL = {
    "name": "search_geonode_layers",
    "description": (
        "Search for GIS layers in GeoNode by keyword. Returns a list of matching "
        "layers with their title, abstract, and direct link. Use this when the user "
        "asks to find, search, or discover geographic layers or datasets."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query, e.g. 'flood risk zones'",
            },
            "page_size": {
                "type": "integer",
                "description": "Number of results to return (1-10). Default 5.",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

SYSTEM_PROMPT = """You are a helpful GIS assistant embedded in a GeoNode geospatial data portal.
Your primary job is to help users find relevant map layers and datasets.
When a user asks about finding layers, maps, or geographic data, always use the
search_geonode_layers tool to search the actual catalog — do not guess.
Keep responses concise and actionable. Format layer results as a numbered list.
If no layers are found, suggest the user try different keywords."""


def _search_layers(query: str, page_size: int = 5, base_url: str = "") -> dict:
    """Call GeoNode REST API to search layers. Uses Docker internal hostname."""
    try:
        resp = requests.get(
            "http://django:8000/api/v2/layers/",
            params={"search": query, "page_size": min(page_size, 10), "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        layers = []
        for item in data.get("datasets", data.get("layers", [])):
            layers.append({
                "title": item.get("title", "Untitled"),
                "abstract": (item.get("abstract") or "No description available.")[:200],
                "link": f"{base_url}/layers/{item.get('alternate', item.get('pk', ''))}",
            })
        return {"count": data.get("total", len(layers)), "layers": layers}
    except Exception as exc:
        return {"count": 0, "layers": [], "error": str(exc)}


def run_agent(user_message: str, conversation_history: list, base_url: str = "") -> str:
    """
    Run one turn of the Claude agent with tool use.

    Args:
        user_message: The user's latest message.
        conversation_history: Previous turns as list of {role, content} dicts.
        base_url: GeoNode site URL for building layer links.

    Returns:
        The assistant's text response.
    """
    api_key = getattr(settings, "ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key:
        return "AI agent is not configured. Please set the ANTHROPIC_API_KEY environment variable."

    client = anthropic.Anthropic(api_key=api_key)
    messages = list(conversation_history) + [{"role": "user", "content": user_message}]

    # Agentic loop — Claude may call tools multiple times before responding
    while True:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=[SEARCH_LAYERS_TOOL],
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            # Append Claude's tool_use response to the message history
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call and collect results
            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "search_geonode_layers":
                    result = _search_layers(
                        query=block.input.get("query", ""),
                        page_size=block.input.get("page_size", 5),
                        base_url=base_url,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })

            # Feed tool results back so Claude can produce a final response
            messages.append({"role": "user", "content": tool_results})

        else:
            # stop_reason == "end_turn" — extract text from response
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "I couldn't generate a response. Please try again."
