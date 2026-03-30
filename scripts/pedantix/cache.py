import json
import os
import sqlite3
from typing import Any

from scripts.pedantix.models import normalize_text

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
CACHE_DB_PATH = os.path.join(DATA_DIR, "pedantix_cache.db")


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pedantix_guesses (
            puzzle_num INTEGER,
            word TEXT,
            response_json TEXT,
            PRIMARY KEY (puzzle_num, word)
        )
    """)
    conn.commit()
    return conn


def get_cached_results(conn: sqlite3.Connection, puzzle_num: int, words: list[str]) -> dict[str, dict[str, Any]]:
    if not words:
        return {}

    placeholders = ",".join("?" for _ in words)
    cursor = conn.execute(
        f"SELECT word, response_json FROM pedantix_guesses WHERE puzzle_num = ? AND word IN ({placeholders})",
        [puzzle_num] + words,
    )

    results = {}
    for word, response_json in cursor.fetchall():
        try:
            results[word] = json.loads(response_json)
        except json.JSONDecodeError:
            print(f"  [DEBUG] Failed to decode JSON from cache for {word}")
    return results


def save_results_to_cache(conn: sqlite3.Connection, puzzle_num: int, raw_responses: dict[str, dict[str, Any]]) -> None:
    if not raw_responses:
        return

    records = []
    for word, data in raw_responses.items():
        norm_w = normalize_text(word)
        records.append((puzzle_num, norm_w, json.dumps(data, ensure_ascii=False)))

    conn.executemany(
        "INSERT OR REPLACE INTO pedantix_guesses (puzzle_num, word, response_json) VALUES (?, ?, ?)", records
    )
    conn.commit()
