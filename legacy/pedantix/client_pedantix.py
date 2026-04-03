import html
import re
from typing import Any

import httpx

from legacy.pedantix.models import GuessResult, normalize_text

BASE_URL = "https://pedantix.certitudes.org"
BROWSER_HEADERS = {
    "Content-Type": "application/json",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
}

SCRIPT_TAG_RE = re.compile(r'<script id="script"[^>]*data-puzzle-number="(?P<puzzle>\d+)"', re.IGNORECASE)
WIKI_BLOCK_RE = re.compile(
    r'<div id="wiki"class="game">(?P<content>[\s\S]+?)</div></div></div></div></div></article>', re.IGNORECASE
)
MASK_SPAN_RE = re.compile(r'<span class="(?:h )?w">([\s\S]*?)</span>')
TAG_RE = re.compile(r"<[^>]+>")


def extract_homepage_metadata(page_html: str) -> tuple[int, list[int], list[int], str]:
    script_match = SCRIPT_TAG_RE.search(page_html)
    if not script_match:
        raise RuntimeError("Impossible de trouver le numéro de puzzle.")

    block_match = WIKI_BLOCK_RE.search(page_html)
    if not block_match:
        raise RuntimeError("Impossible de localiser le bloc masqué.")

    content = block_match.group("content")

    title_lengths: list[int] = []
    h_match = re.search(r"<h[12][^>]*>([\s\S]*?)</h[12]>", content, re.IGNORECASE)
    if h_match:
        spans = MASK_SPAN_RE.findall(h_match.group(1))
        title_lengths = [max(0, len(s) - 2) for s in spans]

    slot_lengths: list[int] = []

    def replace_slot(match: re.Match[str]) -> str:
        slot_len = max(0, len(match.group(1)) - 2)
        slot_lengths.append(slot_len)
        return f"[#{len(slot_lengths) - 1}:{slot_len}]"

    masked = MASK_SPAN_RE.sub(replace_slot, content)
    masked = TAG_RE.sub(" ", masked)
    masked = html.unescape(masked)
    masked = re.sub(r"\s+", " ", masked).strip()
    return int(script_match.group("puzzle")), title_lengths, slot_lengths, masked


def build_score_payload(puzzle_number: int, word: str) -> dict[str, object]:
    return {"num": puzzle_number, "word": word, "answer": [word]}


def parse_guess_result(word: str, data: dict[str, object]) -> GuessResult:
    raw_hits = data.get("x") or {}
    exact_hits, approx_hits = {}, {}

    if isinstance(raw_hits, dict):
        for key, positions in raw_hits.items():
            if not isinstance(positions, list):
                continue
            if key.startswith("#"):
                approx_hits[key] = positions
            else:
                exact_hits[key] = positions

    solved = False
    solution = None
    revealed = data.get("d")
    if isinstance(revealed, list) and revealed:
        solution = str(revealed[0])
        solved = True

    ranking = data.get("v")
    return GuessResult(
        word=word,
        ranking=int(ranking) if isinstance(ranking, int) else None,
        exact_hits=exact_hits,
        approx_hits=approx_hits,
        solved=solved,
        solution=solution,
    )


async def score_word_raw(client: httpx.AsyncClient, puzzle_number: int, word: str) -> tuple[str, dict[str, Any]]:
    response = await client.post(
        f"{BASE_URL}/score",
        params={"n": puzzle_number},
        headers=BROWSER_HEADERS,
        json=build_score_payload(puzzle_number, word),
    )
    response.raise_for_status()
    return normalize_text(word), response.json()
