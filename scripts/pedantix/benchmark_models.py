"""
scripts/pedantix/benchmark_models.py -- benchmark comparatif des modeles LLM.

Teste chaque provider sur un prompt Pedantix identique et mesure :
- latence (secondes)
- tokens generes
- JSON valide (oui/non)
- nombre de probes utiles extraites
- qualite du francais (heuristique simple)

Usage :
    python -m scripts.pedantix.benchmark_models
    python -m scripts.pedantix.benchmark_models --rounds 3
"""

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app.infrastructure.composition import get_llm_service
from app.services.provider_registry import PROVIDER_MODELS
from scripts.pedantix.intelligence import extract_json

llm_service = get_llm_service()

# -- Prompt fixe reproduisant un etat de puzzle reel (puzzle 1420 = Soudage) --

BENCH_SYSTEM = (
    "Tu joues a un benchmark de resolution Pedantix. "
    "Objectif: proposer des actions utiles, pas de texte inutile. "
    "Reponds UNIQUEMENT avec un objet JSON valide. "
    "Format strict:\n"
    "{\n"
    '  "hypothesis": "titre court plausible",\n'
    '  "next_probes": ["mot1", "mot2"],\n'
    '  "wikipedia_queries": ["requete utile 1", "requete utile 2"]\n'
    "}\n"
    "Regles: next_probes doit contenir des mots unitaires (pas de phrase), utiles, dedupes, non generiques.\n"
)

BENCH_PROMPT = (
    "Contexte du puzzle Pedantix :\n"
    "- Titre cible : 1 mot de 7 lettres\n"
    "- Indices exacts trouves : l(18x), la(16x), les(15x), des(12x), de(11x), le(8x), est(7x), un(7x)\n"
    "- Meilleures proximites :\n"
    "  soudure (score=75.76)\n"
    "  energie (score=75.32)\n"
    "  electricite (score=75.32)\n"
    "  car (score=82.86)\n"
    "  peut (score=81.3)\n"
    "  mais (score=80.82)\n"
    "- Mots deja testes : force, mouvement, masse, acceleration, newton, gravitation, travail, "
    "puissance, vitesse, chaleur, pression, tension, frottement\n\n"
    "Le meilleur indice thematique est 'soudure' (75.76). "
    "Propose des mots proches de ce champ lexical et des titres Wikipedia d'un seul mot de 7 lettres.\n"
)

# Modeles Ollama qui ne sont pas toujours disponibles
OPTIONAL_OLLAMA_MODELS = [
    ("gemma4-e4b", "gemma4:e4b"),
    ("gemma4-e2b", "gemma4:e2b"),
    ("gemma4-26b", "gemma4:26b"),
    ("ollama-llama3", "llama3.1:8b"),
]

# Mots attendus dans une bonne reponse pour ce puzzle
EXPECTED_TERMS = {"soudage", "souder", "soudeur", "brasure", "brasage", "metal", "acier", "arc", "fusion", "assemblage"}


@dataclass
class ModelResult:
    provider: str
    model: str
    latency_s: float
    tokens: int
    tokens_per_s: float
    json_valid: bool
    probe_count: int
    relevant_probes: int
    quality_score: float
    raw_output: str
    error: str


def _check_ollama_model_available(model_tag: str) -> bool:
    """Verifie si un modele Ollama est present localement."""
    import shutil
    import subprocess

    if not shutil.which("ollama"):
        return False
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=5
        )
        return model_tag in result.stdout
    except Exception:
        return False


def _count_relevant_probes(probes: list[str]) -> int:
    """Compte les probes uniques qui correspondent au champ lexical attendu."""
    seen: set[str] = set()
    count = 0
    for probe in probes:
        normalized = probe.lower().strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        if normalized in EXPECTED_TERMS:
            count += 1
        # Partial match pour des variantes (soud* -> soudage, soudeur, etc.)
        elif any(normalized.startswith(t[:4]) for t in EXPECTED_TERMS if len(t) >= 4):
            count += 1
    return count


def _compute_quality_score(
    json_valid: bool, probe_count: int, relevant_probes: int, latency: float
) -> float:
    """Score composite 0-100 combinant qualite et vitesse."""
    if not json_valid:
        return 0.0

    # Qualite des probes (60% du score)
    probe_quality = min(probe_count / 15.0, 1.0) * 30  # Avoir assez de probes
    relevance = min(relevant_probes / 5.0, 1.0) * 30  # Probes pertinentes

    # Vitesse (40% du score)
    if latency <= 2.0:
        speed_score = 40.0
    elif latency <= 5.0:
        speed_score = 35.0
    elif latency <= 15.0:
        speed_score = 25.0
    elif latency <= 30.0:
        speed_score = 15.0
    elif latency <= 60.0:
        speed_score = 5.0
    else:
        speed_score = 0.0

    return round(probe_quality + relevance + speed_score, 1)


async def bench_one_provider(provider_key: str, model: str, round_num: int) -> ModelResult:
    """Teste un provider/modele et retourne les metriques."""

    print(f"  [{provider_key}] round {round_num} | model={model} ... ", end="", flush=True)

    # Inject model into PROVIDER_MODELS so llm_service resolves it correctly
    injected = provider_key not in PROVIDER_MODELS
    if injected:
        PROVIDER_MODELS[provider_key] = model

    start = time.perf_counter()
    tokens = 0
    raw_output = ""
    error = ""

    try:
        async for chunk in llm_service.get_streaming_response(
            prompt=BENCH_PROMPT,
            system_message=BENCH_SYSTEM,
            mode="question",
            provider=provider_key,
            json_format=True,
        ):
            raw_output += chunk
            tokens += len(chunk.split())
    except Exception as e:
        error = str(e)
        print(f"ERREUR: {error[:80]}")
        return ModelResult(
            provider=provider_key, model=model, latency_s=time.perf_counter() - start,
            tokens=0, tokens_per_s=0, json_valid=False, probe_count=0,
            relevant_probes=0, quality_score=0, raw_output="", error=error,
        )

    latency = time.perf_counter() - start
    tokens_per_s = tokens / latency if latency > 0 else 0

    # Parse JSON
    json_valid = False
    probe_count = 0
    relevant_probes = 0
    try:
        data = extract_json(raw_output)
        json_valid = True
        probes = data.get("next_probes", [])
        if isinstance(probes, list):
            probes = [p for p in probes if isinstance(p, str) and len(p.strip()) >= 2]
            # Dedup before counting
            unique_probes = list(dict.fromkeys(p.lower().strip() for p in probes))
            probe_count = len(unique_probes)
            relevant_probes = _count_relevant_probes(probes)
    except (ValueError, json.JSONDecodeError):
        pass

    quality = _compute_quality_score(json_valid, probe_count, relevant_probes, latency)

    status = "OK" if json_valid else "JSON_FAIL"
    print(f"{status} | {latency:.1f}s | {probe_count} probes | {relevant_probes} relevant | score={quality}")

    # Cleanup injected entry
    if injected:
        PROVIDER_MODELS.pop(provider_key, None)

    return ModelResult(
        provider=provider_key, model=model, latency_s=round(latency, 2),
        tokens=tokens, tokens_per_s=round(tokens_per_s, 1),
        json_valid=json_valid, probe_count=probe_count,
        relevant_probes=relevant_probes, quality_score=quality,
        raw_output=raw_output[:500], error=error,
    )


def _build_provider_list() -> list[tuple[str, str]]:
    """Construit la liste des providers a tester."""
    providers = [
        ("groq", PROVIDER_MODELS["groq"]),
        ("gemini", PROVIDER_MODELS["gemini"]),
        ("ollama", PROVIDER_MODELS["ollama"]),
        ("ollama-small", PROVIDER_MODELS["ollama-small"]),
        ("ollama-mini", PROVIDER_MODELS["ollama-mini"]),
    ]

    for label, tag in OPTIONAL_OLLAMA_MODELS:
        if _check_ollama_model_available(tag):
            providers.append((label, tag))
        else:
            print(f"  [{label}] {tag} non disponible, skip")

    return providers


def print_results_table(results: list[ModelResult]) -> None:
    """Affiche un tableau comparatif des resultats, separe par type (Cloud/Local)."""
    headers = ["provider", "model", "latency", "tok/s", "json", "probes", "relevant", "score"]

    def _print_group(title: str, group_results: list[ModelResult]) -> None:
        if not group_results:
            return

        print(f"\n=== {title} ===")
        rows = []
        for r in sorted(group_results, key=lambda x: -x.quality_score):
            rows.append([
                r.provider,
                r.model,
                f"{r.latency_s:.1f}s",
                f"{r.tokens_per_s:.0f}",
                "ok" if r.json_valid else "FAIL",
                str(r.probe_count),
                str(r.relevant_probes),
                f"{r.quality_score:.0f}",
            ])

        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))

        def fmt(row: list[str]) -> str:
            return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

        print(fmt(headers))
        print("-+-".join("-" * w for w in widths))
        for row in rows:
            print(fmt(row))

    cloud_results = [r for r in results if r.provider in ("groq", "gemini")]
    local_results = [r for r in results if r.provider not in ("groq", "gemini")]

    _print_group("Modeles Cloud (API)", cloud_results)
    _print_group("Modeles Locaux (Ollama)", local_results)


async def run_benchmark(rounds: int = 1) -> list[ModelResult]:
    """Execute le benchmark complet."""
    providers = _build_provider_list()
    all_results: list[ModelResult] = []

    for round_num in range(1, rounds + 1):
        if rounds > 1:
            print(f"\n=== Round {round_num}/{rounds} ===")

        for provider_key, model in providers:
            result = await bench_one_provider(provider_key, model, round_num)
            all_results.append(result)

    # Aggregation si plusieurs rounds
    if rounds > 1:
        aggregated: dict[str, list[ModelResult]] = {}
        for r in all_results:
            aggregated.setdefault(r.provider, []).append(r)

        avg_results = []
        for provider_key, results_list in aggregated.items():
            valid_results = [r for r in results_list if not r.error]
            if not valid_results:
                avg_results.append(results_list[0])
                continue
            avg_results.append(ModelResult(
                provider=provider_key,
                model=valid_results[0].model,
                latency_s=round(sum(r.latency_s for r in valid_results) / len(valid_results), 2),
                tokens=round(sum(r.tokens for r in valid_results) / len(valid_results)),
                tokens_per_s=round(sum(r.tokens_per_s for r in valid_results) / len(valid_results), 1),
                json_valid=all(r.json_valid for r in valid_results),
                probe_count=round(sum(r.probe_count for r in valid_results) / len(valid_results)),
                relevant_probes=round(sum(r.relevant_probes for r in valid_results) / len(valid_results)),
                quality_score=round(sum(r.quality_score for r in valid_results) / len(valid_results), 1),
                raw_output="(averaged)",
                error="",
            ))
        return avg_results

    return all_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark des modeles LLM pour Pedantix")
    parser.add_argument("--rounds", type=int, default=1, help="Nombre de rounds (moyenne)")
    parser.add_argument("--output", type=str, default="tmp/benchmark_models_results.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("benchmark modeles LLM -- pedantix\n")

    results = asyncio.run(run_benchmark(rounds=args.rounds))

    print_results_table(results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = []
    for r in results:
        d = asdict(r)
        d.pop("raw_output", None)
        serializable.append(d)
    output_path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nresultats ecrits dans : {output_path}")


if __name__ == "__main__":
    main()
