"""Web search tool."""

import json


async def search_web(query: str) -> str:
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(query, max_results=5)
        return json.dumps(results, ensure_ascii=False)
    except ImportError:
        return "Error: 'duckduckgo-search' not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"Search error: {e}"
