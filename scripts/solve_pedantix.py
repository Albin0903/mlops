"""
Solveur Pédantix généraliste s'appuyant sur un service LLM.
Fournit une approche itérative asynchrone pour la découverte et la validation de titres Wikipedia.

La stratégie suit plusieurs phases :
1. Extraction du puzzle et des longueurs des premiers mots de l'article.
2. Sondes initiales (mots fréquents) pour dégrossir le domaine.
3. Sondes heuristiques ciblées selon les premiers résultats.
4. Boucle de convergence assistée par IA :
   - Suggestions de nouveaux mots de sonde.
   - Prédictions de titres potentiels.
   - Validation croisée avec l'API Wikipedia.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.llm_service import llm_service

BASE_URL = "https://pedantix.certitudes.org"
WIKIPEDIA_API = "https://fr.wikipedia.org/w/api.php"

DEFAULT_INITIAL_PROBES =[
    "pays", "ville", "etat", "guerre", "empire", "roi", "art", "musique",
    "film", "roman", "science", "chimie", "physique", "animal", "plante",
    "espece", "langue", "religion", "sport", "football", "informatique",
    "internet", "entreprise", "medecine", "maladie", "amerique", "europe", "france",
]

FALLBACK_PROBE_PACKS = {
    "animal":["mammifere", "canide", "felin", "canis", "latrans", "faune", "predateur", "nahuatl", "mexique", "canada", "centrale", "espece"],
    "geography":["canada", "mexique", "bresil", "suisse", "russie", "italie", "capitale", "population", "continent", "province", "frontiere", "ocean"],
    "biography":["homme", "femme", "ne", "mort", "francais", "auteur", "acteur", "peintre", "politique", "histoire", "guerre", "vie"],
    "science":["biologie", "chimie", "physique", "cellule", "virus", "bacterie", "maladie", "medecine", "molecule", "energie", "espece", "organisme"],
    "culture":["film", "roman", "musique", "album", "chanson", "acteur", "realisateur", "peinture", "artiste", "auteur", "theatre", "poesie"],
}

STOPWORDS = {
    "page", "pages", "mot", "mots", "article", "articles", "pays", "ville",
    "etat", "etats", "art", "science", "animal", "animale", "animaux", "langue", "langues",
}

BROWSER_HEADERS = {
    "Content-Type": "application/json",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}

WIKIPEDIA_HEADERS = {
    "User-Agent": "mlops-pedantix-solver/2.0 (https://github.com/Albin0903/mlops)",
    "Accept": "application/json",
}

SCRIPT_TAG_RE = re.compile(r'<script id="script"[^>]*data-puzzle-number="(?P<puzzle>\d+)"', re.IGNORECASE)
WIKI_BLOCK_RE = re.compile(r'<div id="wiki"class="game">(?P<content>[\s\S]+?)</div></div></div></div></div></article>', re.IGNORECASE)
MASK_SPAN_RE = re.compile(r'<span class="(?:h )?w">([\s\S]*?)</span>')
TAG_RE = re.compile(r"<[^>]+>")
JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(?P<json>[\s\S]*?)```", re.IGNORECASE)


@dataclass(slots=True)
class GuessResult:
    word: str
    ranking: int | None
    exact_hits: dict[str, list[int]]
    approx_hits: dict[str, list[int]]
    solved: bool
    solution: str | None


def normalize_text(value: str) -> str:
    replacements = str.maketrans({
        "é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i", "ô": "o", "ö": "o", "ù": "u", "û": "u", "ü": "u",
        "ç": "c", "œ": "oe", "æ": "ae",
    })
    return value.lower().strip().translate(replacements)


def extract_homepage_metadata(page_html: str) -> tuple[int, list[int], str]:
    script_match = SCRIPT_TAG_RE.search(page_html)
    if not script_match:
        raise RuntimeError("Impossible de trouver le numéro de puzzle.")

    block_match = WIKI_BLOCK_RE.search(page_html)
    if not block_match:
        raise RuntimeError("Impossible de localiser le bloc masque.")

    slot_lengths: list[int] =[]

    def replace_slot(match: re.Match[str]) -> str:
        slot_index = len(slot_lengths)
        slot_len = max(0, len(match.group(1)) - 2)
        slot_lengths.append(slot_len)
        return f"[#{slot_index}:{slot_len}]"

    masked = MASK_SPAN_RE.sub(replace_slot, block_match.group("content"))
    masked = TAG_RE.sub(" ", masked)
    masked = html.unescape(masked)
    masked = re.sub(r"\s+", " ", masked).strip()
    return int(script_match.group("puzzle")), slot_lengths, masked


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


def extract_best_score(approx_hits: dict[str, list[int]]) -> float | None:
    best_score: float | None = None
    for key in approx_hits:
        try:
            score = float(key.removeprefix("#"))
            best_score = score if best_score is None else max(best_score, score)
        except ValueError:
            continue
    return best_score


async def score_word(client: httpx.AsyncClient, puzzle_number: int, word: str) -> GuessResult:
    response = await client.post(
        f"{BASE_URL}/score",
        params={"n": puzzle_number},
        headers=BROWSER_HEADERS,
        json=build_score_payload(puzzle_number, word),
    )
    response.raise_for_status()
    return parse_guess_result(word, response.json())


async def score_words_concurrently(
    client: httpx.AsyncClient,
    puzzle_number: int,
    words: list[str],
    known_words: set[str],
    concurrency_limit: int = 15,
    verbose: bool = False,
    tag: str = "probe"
) -> tuple[list[GuessResult], GuessResult | None]:
    """Exécute les scores de mots en parallèle avec une limite de concurrence."""
    semaphore = asyncio.Semaphore(concurrency_limit)

    async def bound_score(w: str) -> GuessResult:
        async with semaphore:
            for attempt in range(3):
                try:
                    return await score_word(client, puzzle_number, w)
                except httpx.HTTPError:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.5)
            raise RuntimeError("Unreachable")

    words_to_test =[]
    for w in words:
        if not isinstance(w, str): continue
        norm = normalize_text(w)
        if norm and norm not in known_words and norm not in words_to_test:
            words_to_test.append(norm)

    results: list[GuessResult] =[]
    solution_result: GuessResult | None = None

    if not words_to_test:
        return results, solution_result

    tasks =[asyncio.create_task(bound_score(w)) for w in words_to_test]

    try:
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results.append(result)
                known_words.add(normalize_text(result.word))
                if verbose:
                    print(
                        f"[{tag}] {result.word:<14} solved={result.solved!s:<5} "
                        f"exact={len(result.exact_hits):<2} approx={len(result.approx_hits):<2}"
                    )
                if result.solved:
                    solution_result = result
                    break
            except Exception as e:
                if verbose:
                    print(f"[{tag}] Erreur sur le mot: {e}")
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    return results, solution_result


def summarize_results(results: list[GuessResult]) -> dict[str, Any]:
    exact_counter: Counter[str] = Counter()
    exact_positions: dict[str, list[int]] = {}
    probe_scores: list[dict[str, Any]] =[]

    for result in results:
        for term, positions in result.exact_hits.items():
            exact_counter[term] += len(positions)
            exact_positions.setdefault(term, [])
            exact_positions[term].extend(positions)

        best_score = extract_best_score(result.approx_hits)
        if best_score is not None:
            probe_scores.append({
                "word": result.word,
                "best_score": round(best_score, 2),
                "approx_markers": len(result.approx_hits),
            })

    probe_scores.sort(key=lambda item: item["best_score"], reverse=True)
    sorted_exact =[
        {"term": term, "count": exact_counter[term], "positions": sorted(set(exact_positions[term]))[:12]}
        for term in sorted(exact_counter, key=lambda term: (-exact_counter[term], term))
        if normalize_text(term) not in STOPWORDS
    ]

    return {"exact_terms": sorted_exact, "best_probes": probe_scores[:20]}


def infer_probe_pack_order(summary: dict[str, Any]) -> list[str]:
    words = {normalize_text(item["word"]) for item in summary["best_probes"]}
    exact_terms = {normalize_text(item["term"]) for item in summary["exact_terms"]}
    signals = words | exact_terms

    scored_packs =[
        ("animal", len(signals & {"animal", "espece", "amerique", "faune", "langue"})),
        ("geography", len(signals & {"amerique", "europe", "pays", "ville", "continent", "etat"})),
        ("biography", len(signals & {"guerre", "empire", "politique", "histoire", "homme", "femme"})),
        ("science", len(signals & {"science", "physique", "chimie", "medecine", "maladie"})),
        ("culture", len(signals & {"film", "roman", "musique", "art"}))
    ]
    return list(dict.fromkeys(name for name, _ in sorted(scored_packs, key=lambda item: item[1], reverse=True)))


def build_fallback_probes(summary: dict[str, Any], known_words: set[str]) -> list[str]:
    probes: list[str] =[]
    for pack_name in infer_probe_pack_order(summary):
        probes.extend(FALLBACK_PROBE_PACKS[pack_name])
    return probes


def extract_json_payload(text: str) -> dict[str, Any]:
    raw = text.strip()
    block_match = JSON_BLOCK_RE.search(raw)
    if block_match:
        raw = block_match.group("json").strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Réponse LLM non exploitable: {text}")
    return json.loads(raw[start : end + 1])


async def ask_llm_for_probes(
    first_words_lengths: list[int],
    masked_preview: str,
    summary: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    system_message = (
        "Tu aides à résoudre Pédantix en trouvant une page Wikipedia cachée. "
        "Tu dois répondre uniquement en JSON valide. Propose des mots de sondage en français, simples, sans ponctuation."
    )
    prompt = (
        "Contexte du puzzle Pédantix:\n"
        f"- longueurs des premiers mots de l'article : {first_words_lengths}\n"
        f"- aperçu du masque : {masked_preview[:800]}\n"
        f"- indices exacts : {json.dumps(summary['exact_terms'], ensure_ascii=False)}\n"
        f"- meilleures sondes sémantiques : {json.dumps(summary['best_probes'], ensure_ascii=False)}\n\n"
        "Retourne un objet JSON strict avec cette forme:\n"
        '{"hypothesis":"résumé bref", "next_probes":["mot1","mot2"], "wikipedia_queries":["requete 1"]}\n'
        "Contraintes:\n"
        "- 15 à 25 next_probes (mots uniques ou groupes très courts, nouveaux mots pertinents pour explorer tes hypothèses)\n"
        "- wikipedia_queries doit contenir des requêtes par mots-clés simples pour la recherche (PAS d'URL, PAS de site:).\n"
    )
    response = await llm_service.get_full_response(prompt=prompt, system_message=system_message, mode="question", provider=provider)
    return extract_json_payload(response)


async def ask_llm_for_candidates(
    first_words_lengths: list[int],
    masked_preview: str,
    summary: dict[str, Any],
    tested_candidates: list[str],
    provider: str,
) -> dict[str, Any]:
    system_message = (
        "Tu aides à identifier le titre exact d'une page Wikipedia cachée dans Pédantix. "
        "Tu dois proposer des titres Wikipedia francophones plausibles et testables. "
        "Réponds uniquement en JSON valide."
    )
    tested_str = json.dumps(tested_candidates[-50:], ensure_ascii=False) if tested_candidates else "Aucun"
    prompt = (
        "Contexte du puzzle Pédantix:\n"
        f"- longueurs des premiers mots de l'article : {first_words_lengths}\n"
        f"- aperçu du masque : {masked_preview[:1200]}\n"
        f"- indices exacts : {json.dumps(summary['exact_terms'], ensure_ascii=False)}\n"
        f"- meilleures sondes sémantiques testées : {json.dumps(summary['best_probes'], ensure_ascii=False)}\n"
        f"- Titres déjà testés (qui ont échoué) : {tested_str}\n\n"
        "Retourne un objet JSON strict avec cette forme:\n"
        '{"hypothesis":"résumé bref", "candidate_titles":["Titre 1","Titre 2"], "wikipedia_queries":["requete 1"]}\n'
        "Contraintes:\n"
        "- 15 à 30 candidate_titles\n"
        "- seulement des titres de pages Wikipedia existantes en français\n"
        "- Ne propose PAS les titres déjà testés.\n"
        "- wikipedia_queries doit contenir des mots-clés simples pour la recherche (ex: 'religion angleterre', pas d'URL ni de site:).\n"
    )
    response = await llm_service.get_full_response(prompt=prompt, system_message=system_message, mode="question", provider=provider)
    return extract_json_payload(response)


def filter_candidate_titles(candidates: list[str]) -> list[str]:
    cleaned, seen =[], set()
    for candidate in candidates:
        if not isinstance(candidate, str): continue
        title = candidate.strip()
        if not title: continue
        lowered = title.lower()
        if lowered not in seen:
            seen.add(lowered)
            cleaned.append(title)
    return cleaned


async def search_wikipedia_titles(client: httpx.AsyncClient, queries: list[str], per_query: int = 10) -> list[str]:
    candidates: list[str] =[]
    
    async def search_single(query: str):
        try:
            response = await client.get(
                WIKIPEDIA_API,
                headers=WIKIPEDIA_HEADERS,
                params={"action": "query", "list": "search", "format": "json", "utf8": 1, "srsearch": query, "srlimit": per_query},
                timeout=15.0,
            )
            response.raise_for_status()
            for item in response.json().get("query", {}).get("search",[]):
                title = item.get("title")
                if isinstance(title, str):
                    candidates.append(title)
        except Exception:
            pass
            
    await asyncio.gather(*(search_single(q) for q in queries))
    return filter_candidate_titles(candidates)


def format_exact_hits(summary: dict[str, Any]) -> str:
    lines = [f"- {i['term']} -> count={i['count']} positions={i['positions']}" for i in summary["exact_terms"][:20]]
    return "\n".join(lines) if lines else "- aucun indice exact utile"


def format_probe_scores(summary: dict[str, Any]) -> str:
    lines = [f"- {i['word']} -> best_score={i['best_score']} markers={i['approx_markers']}" for i in summary["best_probes"][:20]]
    return "\n".join(lines) if lines else "- aucune proximité notable"


async def solve_pedantix(provider: str, max_candidates: int, verbose: bool) -> None:
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, limits=limits) as client:
        homepage = await client.get(f"{BASE_URL}/")
        homepage.raise_for_status()

        puzzle_number, slot_lengths, masked_preview = extract_homepage_metadata(homepage.text)
        first_words_lengths = slot_lengths[:15] if slot_lengths else[]

        print(f"Puzzle         : {puzzle_number}")
        print(f"Longueurs mots : {first_words_lengths}")
        print(f"Nb de slots    : {len(slot_lengths)}")
        print(f"Provider LLM   : {provider}")
        print(f"Aperçu masque  : {masked_preview[:220]}...\n")

        all_results: list[GuessResult] =[]
        known_words: set[str] = set()
        tested_titles: list[str] =[]

        # Phase 1: Vague initiale
        results, solution = await score_words_concurrently(
            client, puzzle_number, DEFAULT_INITIAL_PROBES, known_words, verbose=verbose, tag="probe-1"
        )
        all_results.extend(results)
        if solution:
            print(f"\nSolution trouvée directement : {solution.solution}")
            print(f"Lien Wikipedia : https://fr.wikipedia.org/wiki/{solution.solution.replace(' ', '_')}")
            return

        summary = summarize_results(all_results)
        print("Indices exacts après première vague :\n" + format_exact_hits(summary))
        print("\nMeilleures proximités après première vague :\n" + format_probe_scores(summary) + "\n")

        # Phase 2: Vague heuristique
        fallback_probes = build_fallback_probes(summary, known_words)
        print(f"Sondes heuristiques : {', '.join(fallback_probes[:15])}...\n")
        
        results, solution = await score_words_concurrently(
            client, puzzle_number, fallback_probes, known_words, verbose=verbose, tag="probe-fallback"
        )
        all_results.extend(results)
        if solution:
            print(f"\nSolution trouvée (heuristique) : {solution.solution}")
            print(f"Lien Wikipedia : https://fr.wikipedia.org/wiki/{solution.solution.replace(' ', '_')}")
            return

        summary = summarize_results(all_results)
        print("Indices exacts après vague heuristique :\n" + format_exact_hits(summary))
        print("\nMeilleures proximités après vague heuristique :\n" + format_probe_scores(summary) + "\n")

        # BOUCLE CONVERGENCE (Amélioration par LLM)
        max_iterations = 4
        for iteration in range(1, max_iterations + 1):
            print(f"================ ITERATION CONVERGENCE {iteration}/{max_iterations} ================\n")
            
            # Phase 3: Sondes suggérées
            probe_plan = await ask_llm_for_probes(first_words_lengths, masked_preview, summary, provider)
            llm_probes = probe_plan.get("next_probes",[])

            print("Hypothèse de recherche (Sondes) :\n" + probe_plan.get("hypothesis", "Aucune"))
            print("\nSondes suggérées : " + ", ".join(llm_probes) + "\n")

            results, solution = await score_words_concurrently(
                client, puzzle_number, llm_probes, known_words, verbose=verbose, tag=f"probe-llm-{iteration}"
            )
            all_results.extend(results)
            if solution:
                print(f"\nSolution trouvée (Sondes suggérées) : {solution.solution}")
                print(f"Lien Wikipedia : https://fr.wikipedia.org/wiki/{solution.solution.replace(' ', '_')}")
                return

            summary = summarize_results(all_results)
            print("Indices exacts après sondes suggérées :\n" + format_exact_hits(summary))
            print("\nMeilleures proximités après sondes suggérées :\n" + format_probe_scores(summary) + "\n")
            
            # Phase 4: Candidats potentiels
            candidate_plan = await ask_llm_for_candidates(first_words_lengths, masked_preview, summary, tested_titles, provider)
            llm_candidates = filter_candidate_titles(candidate_plan.get("candidate_titles",[]))
            
            # Nettoyage des requêtes pour éviter l'opérateur "site:" inutile
            new_queries =[q.strip() for q in candidate_plan.get("wikipedia_queries", []) if isinstance(q, str)]
            clean_queries =[]
            for q in new_queries:
                q_clean = re.sub(r"site:fr\.wikipedia\.org", "", q).strip()
                if q_clean and q_clean not in clean_queries:
                    clean_queries.append(q_clean)

            print("Hypothèse de recherche (Titres) :\n" + candidate_plan.get("hypothesis", "Aucune") + "\n")
            print("Requêtes Wikipedia : \n" + "\n".join(f"- {q}" for q in clean_queries) + "\n")

            wiki_candidates = await search_wikipedia_titles(client, clean_queries)
            title_candidates = filter_candidate_titles(llm_candidates + wiki_candidates)
            
            # Tri et limitation des candidats
            valid_candidates =[]
            for c in title_candidates:
                if c not in tested_titles and normalize_text(c) not in known_words:
                    valid_candidates.append(c)
            title_candidates = valid_candidates[:max_candidates]

            print("Titres candidats testés :")
            for candidate in title_candidates:
                print(f"- {candidate}")
            print()

            results, solution = await score_words_concurrently(
                client, puzzle_number, title_candidates, known_words, concurrency_limit=10, verbose=verbose, tag=f"candidate-{iteration}"
            )
            all_results.extend(results)
            tested_titles.extend(title_candidates)

            if solution:
                print(f"\nSolution validée : {solution.solution}")
                print(f"Lien Wikipedia : https://fr.wikipedia.org/wiki/{solution.solution.replace(' ', '_')}")
                return

            summary = summarize_results(all_results)
            print(f"Aucun candidat n'a résolu la page à l'itération {iteration}. Poursuite de la recherche...\n")

        raise RuntimeError("Aucun candidat n'a résolu la page après toutes les itérations. Relancez avec --verbose ou augmentez --max-candidates.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solveur généraliste Pédantix avec IA et boucle itérative")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "groq", "instant", "medium", "gpt"])
    parser.add_argument("--max-candidates", type=int, default=30)
    parser.add_argument("--verbose", action="store_true", help="Affiche chaque requête API effectuée")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(solve_pedantix(provider=args.provider, max_candidates=args.max_candidates, verbose=args.verbose))