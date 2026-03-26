import html
import re
from dataclasses import dataclass


@dataclass(slots=True)
class GuessResult:
    word: str
    ranking: int | None
    exact_hits: dict[str, list[int]]
    approx_hits: dict[str, list[int]]
    solved: bool
    solution: str | None


def normalize_text(value: str) -> str:
    # On ne retire PAS les accents car l'API de Pedantix en a besoin pour certains mots.
    # On se contente de mettre en minuscules et d'enlever les espaces inutiles.
    return value.lower().strip()


def extract_words_from_phrase(phrase: str) -> list[str]:
    """Pédantix teste les mots un par un. Coupe un titre comme 'Panthéon (Rome)' en ['Panthéon', 'Rome']."""
    return [w for w in re.findall(r"[a-zà-ÿ0-9\-]+", phrase.lower()) if len(w) > 0]


def normalize_wikipedia_title_for_match(title: str) -> str:
    cleaned = normalize_text(html.unescape(title))
    cleaned = re.sub(r"[\(\)\[\]\{\}\'\"\.,;:!?/\\_\-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
