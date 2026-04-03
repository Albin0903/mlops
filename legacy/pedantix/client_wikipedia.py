import asyncio

import httpx

from legacy.pedantix.models import normalize_wikipedia_title_for_match

WIKIPEDIA_API = "https://fr.wikipedia.org/w/api.php"
WIKIPEDIA_HEADERS = {
    "User-Agent": "mlops-pedantix-solver/2.0 (https://github.com/Albin0903/mlops)",
    "Accept": "application/json",
}


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        s = item.strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


async def search_wikipedia_titles(client: httpx.AsyncClient, queries: list[str], per_query: int = 10) -> list[str]:
    candidates: list[str] = []

    async def _search(query: str):
        try:
            resp = await client.get(
                WIKIPEDIA_API,
                headers=WIKIPEDIA_HEADERS,
                params={
                    "action": "query",
                    "list": "search",
                    "format": "json",
                    "utf8": 1,
                    "srsearch": query,
                    "srlimit": per_query,
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            for item in resp.json().get("query", {}).get("search", []):
                title = item.get("title")
                if isinstance(title, str):
                    candidates.append(title)
        except Exception:
            pass

    await asyncio.gather(*(_search(q) for q in queries))
    return _dedup(candidates)


async def resolve_wikipedia_title(client: httpx.AsyncClient, title: str) -> str | None:
    """Résout un titre Wikipédia FR exact ou canonicalisé, sinon renvoie None."""
    candidate_norm = normalize_wikipedia_title_for_match(title)

    try:
        resp = await client.get(
            WIKIPEDIA_API,
            headers=WIKIPEDIA_HEADERS,
            params={"action": "query", "titles": title, "format": "json", "redirects": 1, "converttitles": 1},
            timeout=10.0,
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1" or not isinstance(page, dict):
                continue
            page_title = page.get("title")
            if isinstance(page_title, str):
                return page_title
    except Exception:
        pass

    try:
        resp = await client.get(
            WIKIPEDIA_API,
            headers=WIKIPEDIA_HEADERS,
            params={"action": "opensearch", "search": title, "limit": 10, "format": "json"},
            timeout=10.0,
        )
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, list) and len(payload) >= 2:
            for item in payload[1]:
                if not isinstance(item, str):
                    continue
                if normalize_wikipedia_title_for_match(item) == candidate_norm:
                    return item
    except Exception:
        pass

    return None
