import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path
from typing import Any

import httpx

# Fix for Windows console unicode errors
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Include root dir to path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.pedantix.cache import get_cached_results, init_db, save_results_to_cache  # noqa: E402
from scripts.pedantix.client_pedantix import (  # noqa: E402
    BASE_URL,
    extract_homepage_metadata,
    parse_guess_result,
    score_word_raw,
)
from scripts.pedantix.client_wikipedia import search_wikipedia_titles  # noqa: E402
from scripts.pedantix.intelligence import (  # noqa: E402
    ask_llm_candidates,
    ask_llm_probes,
    build_fallback_probes,
    render_virtual_window,
    summarize_results,
)
from scripts.pedantix.models import GuessResult, extract_words_from_phrase, normalize_text  # noqa: E402

DEFAULT_INITIAL_PROBES = [
    "le",
    "la",
    "les",
    "l",
    "un",
    "une",
    "des",
    "d",
    "du",
    "de",
    "et",
    "ou",
    "qui",
    "que",
    "quoi",
    "dont",
    "au",
    "aux",
    "par",
    "pour",
    "sur",
    "dans",
    "avec",
    "en",
    "y",
    "a",
    "est",
    "sont",
    "etre",
    "avoir",
    "ne",
    "pas",
    "plus",
    "se",
    "s",
    "son",
    "sa",
    "ses",
    "ces",
    "ce",
    "c",
    "m",
    "t",
    "j",
    "n",
    "il",
    "elle",
    "ils",
    "elles",
    "on",
    "tout",
    "tous",
    "comme",
    "meme",
    "bien",
    "aussi",
    "entre",
    "sous",
    "vers",
    "jusque",
    "lors",
    "mais",
    "où",
    "donc",
    "ni",
    "car",
    "très",
    "peu",
    "beaucoup",
    "trop",
    "assez",
    "moins",
    "sans",
    "avant",
    "après",
    "ici",
    "là",
    "ainsi",
    "toujours",
    "jamais",
    "souvent",
    "faire",
    "fait",
    "font",
    "pouvoir",
    "peut",
    "peuvent",
    "devoir",
    "doit",
    "doivent",
    "aller",
    "va",
    "vont",
    "voir",
    "voit",
    "voient",
    "savoir",
    "sait",
    "savent",
    "falloir",
    "faut",
    "vouloir",
    "veut",
    "veulent",
    "dire",
    "dit",
    "disent",
    "donner",
    "donne",
    "donnent",
    "prendre",
    "prend",
    "prennent",
    "mettre",
    "met",
    "mettent",
    "siecle",
    "annee",
    "temps",
    "premier",
    "grand",
    "partie",
    "histoire",
    "pays",
    "ville",
    "etat",
    "guerre",
    "empire",
    "roi",
    "art",
    "musique",
    "film",
    "roman",
    "science",
    "chimie",
    "physique",
    "animal",
    "plante",
    "espece",
    "langue",
    "religion",
    "sport",
    "football",
    "informatique",
    "internet",
    "entreprise",
    "medecine",
    "maladie",
    "amerique",
    "europe",
    "france",
]


def print_exact_hits(summary: dict[str, Any]) -> None:
    lines = [f"  - {i['term']} -> count={i['count']} positions={i['positions']}" for i in summary["exact_terms"][:15]]
    print("Indices exacts:\n" + ("\n".join(lines) if lines else "  (aucun)"))


def print_probe_scores(summary: dict[str, Any]) -> None:
    lines = [f"  - {i['word']} -> score={i['best_score']}" for i in summary["best_probes"][:15]]
    print("Meilleures proximités:\n" + ("\n".join(lines) if lines else "  (aucune)"))


def print_window(slot_lengths: list[int], summary: dict[str, Any], label: str) -> None:
    print(f"\nFenêtre ({label}):")
    print(render_virtual_window(slot_lengths, summary, max_slots=90))


def print_solution(solution: GuessResult, label: str, source_detail: str | None = None) -> None:
    print(f"info: SOLUTION TROUVÉE ({label}) : {solution.solution}")
    if source_detail:
        print(f"Source : {source_detail}")
    print(f"Lien : https://fr.wikipedia.org/wiki/{solution.solution.replace(' ', '_')}")


async def score_words_batch(
    client: httpx.AsyncClient,
    puzzle_number: int,
    words: list[str],
    known_words: set[str],
    db_conn: sqlite3.Connection,
    concurrency: int = 15,
    verbose: bool = False,
    tag: str = "probe",
) -> tuple[list[GuessResult], GuessResult | None]:
    """Score une liste de mots en parallèle avec cache SQLite. Retourne (résultats, solution_ou_None)."""
    sem = asyncio.Semaphore(concurrency)
    to_test = []
    for w in words:
        if not isinstance(w, str):
            continue
        norm = normalize_text(w)
        if norm and norm not in known_words and norm not in to_test:
            to_test.append(norm)

    if not to_test:
        return [], None

    cached_raw = get_cached_results(db_conn, puzzle_number, to_test)
    words_to_fetch = [w for w in to_test if w not in cached_raw]

    if verbose and words_to_fetch:
        print(f"  [{tag}] {len(cached_raw)} en cache, {len(words_to_fetch)} à appeler via API.")

    async def _fetch(w: str) -> tuple[str, dict[str, Any]]:
        async with sem:
            for attempt in range(3):
                try:
                    return await score_word_raw(client, puzzle_number, w)
                except httpx.HTTPError as e:
                    if attempt == 2:
                        raise RuntimeError("API fetch failed") from e
                    await asyncio.sleep(0.5)
            raise RuntimeError("Unreachable")

    fetched_raw: dict[str, dict[str, Any]] = {}
    if words_to_fetch:
        tasks = [asyncio.create_task(_fetch(w)) for w in words_to_fetch]
        try:
            for coro in asyncio.as_completed(tasks):
                try:
                    w, r_json = await coro
                    fetched_raw[w] = r_json
                except Exception as e:
                    if verbose:
                        print(f"  [{tag}] Erreur API: {e}")
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

        save_results_to_cache(db_conn, puzzle_number, fetched_raw)

    all_raw = {**cached_raw, **fetched_raw}
    results: list[GuessResult] = []
    solution: GuessResult | None = None

    for w, data in all_raw.items():
        parsed = parse_guess_result(w, data)
        results.append(parsed)
        known_words.add(normalize_text(w))
        if verbose and w not in cached_raw:
            print(
                f"  [{tag}] API -> {parsed.word:<14} exact={len(parsed.exact_hits):<2} approx={len(parsed.approx_hits):<2}"
            )
        if parsed.solved:
            solution = parsed

    return results, solution

class SolverContext:
    def __init__(
        self, client: httpx.AsyncClient, db_conn: sqlite3.Connection, puzzle_number: int, verbose: bool = False
    ):
        self.client = client
        self.db_conn = db_conn
        self.puzzle_number = puzzle_number
        self.verbose = verbose
        self.all_results: list[GuessResult] = []
        self.known_words: set[str] = set()

    async def score_batch(self, words: list[str], tag: str = "probe") -> tuple[list[GuessResult], GuessResult | None]:
        results, solution = await score_words_batch(
            self.client, self.puzzle_number, words, self.known_words, self.db_conn, verbose=self.verbose, tag=tag
        )
        self.all_results.extend(results)
        return results, solution


async def solve_pedantix(
    provider: str, max_candidates: int, max_iterations: int, verbose: bool, thinking: str, mode: str = "classic"
) -> None:
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, limits=limits, headers=headers) as client:
        homepage = await client.get(f"{BASE_URL}/")
        homepage.raise_for_status()

        puzzle_number, title_lengths, slot_lengths, masked_preview = extract_homepage_metadata(homepage.text)

        print(f"Puzzle         : {puzzle_number}")
        print(f"Longueurs titre: {title_lengths}")
        print(f"Nb de slots    : {len(slot_lengths)}")
        print(f"Provider LLM   : {provider}")
        print(f"Thinking       : {thinking}")
        print(f"Aperçu masque  : {masked_preview[:200]}...\n")

        db_conn = init_db()
        ctx = SolverContext(client, db_conn, puzzle_number, verbose=verbose)

        if mode == "agent":
            from scripts.pedantix.agent import PedantixAgent

            agent = PedantixAgent(
                puzzle_number, title_lengths, slot_lengths, masked_preview, ctx, provider=provider, thinking=thinking
            )
            await agent.run()
            return

        def check_victory(summary: dict[str, Any] | None) -> bool:
            if not summary:
                return False
            exacts = summary.get("exact_terms") or []
            covered_positions = set()
            for item in exacts:
                if not isinstance(item, dict):
                    continue
                p_list = item.get("positions")
                if p_list is None:
                    continue
                for p in p_list:
                    if p < len(title_lengths):
                        covered_positions.add(p)
            return len(covered_positions) == len(title_lengths)

        # Phase 1
        print("info: Phase 1 : Sondes initiales")
        results, solution = await ctx.score_batch(DEFAULT_INITIAL_PROBES, tag="init")
        summary = summarize_results(ctx.all_results)
        if solution or check_victory(summary):
            print_solution(solution if solution else GuessResult("", None, {}, {}, True, ""), "phase initiale")
            return

        print_exact_hits(summary)
        print_probe_scores(summary)

        # Phase 2
        print("info: Phase 2 : Sondes heuristiques")
        results, solution = await ctx.score_batch(build_fallback_probes(summary), tag="heur")
        summary = summarize_results(ctx.all_results)
        if solution or check_victory(summary):
            print_solution(solution if solution else GuessResult("", None, {}, {}, True, ""), "phase heuristique")
            return

        tested_titles = []
        searched_queries = set()

        # Boucle Classique
        for iteration in range(1, max_iterations + 1):
            print(f"info: ITÉRATION {iteration}/{max_iterations}")
            probe_plan = await ask_llm_probes(
                title_lengths, masked_preview, summary, provider, ctx.known_words, thinking=thinking
            )
            llm_probes = probe_plan.get("next_probes", [])
            llm_queries = [q for q in probe_plan.get("wikipedia_queries", []) if isinstance(q, str) and q.strip()]

            results, solution = await ctx.score_batch(llm_probes, tag=f"llm-{iteration}")
            summary = summarize_results(ctx.all_results)
            if solution or check_victory(summary):
                print_solution(solution if solution else GuessResult("", None, {}, {}, True, ""), f"sondes LLM {iteration}")
                return

            # Wiki
            new_queries = [q for q in llm_queries if normalize_text(q) not in searched_queries]
            for q in new_queries:
                searched_queries.add(normalize_text(q))

            if new_queries:
                wiki_titles = await search_wikipedia_titles(client, new_queries[:5], per_query=5)
                wiki_candidates = [t for t in wiki_titles if t not in tested_titles][:max_candidates]
                if wiki_candidates:
                    print(f"  Candidats Wiki: {wiki_candidates[:5]}")
                    words = []
                    for c in wiki_candidates:
                        words.extend(extract_words_from_phrase(c))
                    results, solution = await ctx.score_batch(words, tag=f"wiki-{iteration}")
                    tested_titles.extend(wiki_candidates)
                    summary = summarize_results(ctx.all_results)
                    if solution:
                        print_solution(solution, f"Wiki {iteration}")
                        return

            # Candidates
            llm_candidates = await ask_llm_candidates(
                title_lengths, masked_preview, summary, tested_titles, provider, thinking=thinking
            )
            if llm_candidates:
                words = []
                for c in llm_candidates[:max_candidates]:
                    words.extend(extract_words_from_phrase(c))
                results, solution = await ctx.score_batch(words, tag=f"cand-{iteration}")
                tested_titles.extend(llm_candidates)
                summary = summarize_results(ctx.all_results)
                if solution:
                    print_solution(solution, f"Candidats {iteration}")
                    return

            print_exact_hits(summary)
            print_probe_scores(summary)

        print("info: ÉCHEC : Aucun candidat n'a résolu la page.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solveur Pédantix avec mode Agent")
    parser.add_argument("--mode", default="classic", choices=["classic", "agent"])
    parser.add_argument(
        "--provider",
        default="groq",
        choices=[
            "gemini",
            "groq",
            "instant",
            "medium",
            "gpt",
            "ollama",
            "ollama-medium",
            "ollama-small",
            "ollama-mini",
        ],
    )
    parser.add_argument("--max-candidates", type=int, default=20)
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument(
        "--thinking",
        default=None,
        choices=["off", "low", "medium", "high"],
        help="Niveau de réflexion universel (pour tout LLM)",
    )
    parser.add_argument("--verbose", action="store_true", help="Affiche chaque requête API")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        solve_pedantix(
            provider=args.provider,
            max_candidates=args.max_candidates,
            max_iterations=args.max_iterations,
            verbose=args.verbose,
            thinking=args.thinking or "off",
            mode=args.mode,
        )
    )

