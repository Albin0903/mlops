import json
import re
from collections import Counter
from typing import Any

from app.services.llm_service import llm_service
from scripts.pedantix.models import GuessResult, normalize_text

STOPWORDS = {
    "page",
    "pages",
    "mot",
    "mots",
    "article",
    "articles",
    "pays",
    "ville",
    "etat",
    "etats",
    "art",
    "science",
    "animal",
    "animale",
    "animaux",
    "langue",
    "langues",
}

PROBE_STOPWORDS = STOPWORDS | {
    "le",
    "la",
    "les",
    "de",
    "du",
    "des",
    "un",
    "une",
    "et",
    "ou",
    "a",
    "au",
    "aux",
    "d",
    "l",
    "est",
    "sont",
    "il",
    "elle",
    "ils",
    "elles",
    "ce",
    "ces",
    "cette",
    "ne",
    "pas",
    "plus",
    "en",
    "etre",
    "avoir",
    "bien",
    "aussi",
    "meme",
    "que",
    "qui",
    "dans",
    "sur",
    "pour",
    "avec",
    "t",
    "j",
    "n",
    "y",
}

LLM_NOISE_WORDS = PROBE_STOPWORDS | {"meme", "aussi", "que", "c"}

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(?P<json>[\s\S]*?)```", re.IGNORECASE)


def _split_glued_words(text: str) -> str:
    return re.sub(r"([a-zà-ÿ])([A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸ])", r"\1 \2", text)


def extract_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    block = JSON_BLOCK_RE.search(raw)
    if block:
        raw = block.group("json").strip()

    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Réponse LLM non exploitable: {text[:200]}")

    raw_json = raw[start : end + 1]
    raw_json = raw_json.replace("\\", "\\\\")
    raw_json = _split_glued_words(raw_json)

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        try:
            return json.loads(raw_json, strict=False)
        except json.JSONDecodeError:
            raise ValueError(f"JSON invalide: {e}") from e


def extract_best_score(approx_hits: dict[str, list[int]]) -> float | None:
    best: float | None = None
    for key in approx_hits:
        try:
            score = float(key.removeprefix("#"))
            best = score if best is None else max(best, score)
        except ValueError:
            continue
    return best


def summarize_results(results: list[GuessResult]) -> dict[str, Any]:
    exact_counter: Counter[str] = Counter()
    exact_positions: dict[str, list[int]] = {}
    probe_scores: list[dict[str, Any]] = []

    for r in results:
        for term, positions in r.exact_hits.items():
            exact_counter[term] += len(positions)
            exact_positions.setdefault(term, []).extend(positions)

        best = extract_best_score(r.approx_hits)
        if best is not None:
            probe_scores.append({"word": r.word, "best_score": round(best, 2), "approx_markers": len(r.approx_hits)})

    probe_scores = [
        p
        for p in probe_scores
        if normalize_text(p["word"]) not in PROBE_STOPWORDS and len(normalize_text(p["word"])) >= 3
    ]
    probe_scores.sort(key=lambda p: p["best_score"], reverse=True)

    sorted_exact = [
        {"term": t, "count": exact_counter[t], "positions": sorted(set(exact_positions[t]))[:12]}
        for t in sorted(exact_counter, key=lambda t: (-exact_counter[t], t))
        if normalize_text(t) not in STOPWORDS
    ]

    return {"exact_terms": sorted_exact, "best_probes": probe_scores[:20]}


def sanitize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    clean_exact = [
        item
        for item in summary.get("exact_terms", [])
        if normalize_text(str(item.get("term", ""))) not in LLM_NOISE_WORDS
        and len(normalize_text(str(item.get("term", "")))) > 2
    ]
    clean_probes = [
        item
        for item in summary.get("best_probes", [])
        if normalize_text(str(item.get("word", ""))) not in LLM_NOISE_WORDS
        and len(normalize_text(str(item.get("word", "")))) > 2
    ]
    return {"exact_terms": clean_exact[:25], "best_probes": clean_probes[:25]}


def render_virtual_window(slot_lengths: list[int], summary: dict[str, Any], max_slots: int = 150) -> str:
    resolved: dict[int, str] = {}
    for item in summary.get("exact_terms", []):
        term = str(item.get("term", "")).strip()
        for pos in item.get("positions", []):
            if isinstance(pos, int) and 0 <= pos < len(slot_lengths):
                resolved[pos] = term

    parts = []
    for i, length in enumerate(slot_lengths[:max_slots]):
        parts.append(resolved.get(i, f"_{length}_"))

    suffix = " ..." if len(slot_lengths) > max_slots else ""
    return " ".join(parts) + suffix


def infer_probe_pack_order(summary: dict[str, Any]) -> list[str]:
    words = {normalize_text(item["word"]) for item in summary["best_probes"]}
    exact_terms = {normalize_text(item["term"]) for item in summary["exact_terms"]}
    signals = words | exact_terms

    packs = [
        ("animal", len(signals & {"animal", "espece", "amerique", "faune", "langue"})),
        ("geography", len(signals & {"amerique", "europe", "pays", "ville", "continent", "etat"})),
        ("biography", len(signals & {"guerre", "empire", "politique", "histoire", "homme", "femme"})),
        ("science", len(signals & {"science", "physique", "chimie", "medecine", "maladie"})),
        ("culture", len(signals & {"film", "roman", "musique", "art"})),
    ]
    return list(dict.fromkeys(name for name, _ in sorted(packs, key=lambda x: x[1], reverse=True)))


FALLBACK_PROBE_PACKS = {
    "animal": ["mammifere", "canide", "felin", "canis", "faune", "predateur", "espece"],
    "geography": ["canada", "mexique", "bresil", "suisse", "russie", "italie", "capitale", "population", "continent"],
    "biography": ["homme", "femme", "ne", "mort", "francais", "auteur", "acteur", "politique", "vie"],
    "science": ["biologie", "chimie", "physique", "cellule", "virus", "medecine", "molecule", "energie"],
    "culture": ["film", "roman", "musique", "album", "chanson", "realisateur", "artiste", "theatre"],
}


def build_fallback_probes(summary: dict[str, Any]) -> list[str]:
    probes: list[str] = []
    for pack_name in infer_probe_pack_order(summary):
        probes.extend(FALLBACK_PROBE_PACKS[pack_name])
    return probes


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        s = item.strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


async def ask_llm_probes(
    title_lengths: list[int],
    masked_preview: str,
    summary: dict[str, Any],
    provider: str,
    known_words: set[str],
    thinking: str | bool | None = None,
) -> dict[str, Any]:
    system = (
        "Tu aides à résoudre Pédantix en trouvant une page Wikipedia cachée. "
        "Réponds UNIQUEMENT avec un objet JSON valide. "
        "Règle ABSOLUE : Rédige TOUJOURS en français normal, avec des ESPACES NATURELS entre chaque mot.\n"
    )
    if "ollama" in provider:
        system += "MAUVAIS : 'religiongrande' ou 'CeciEstUnTest'\nBON : 'religion grande' ou 'Ceci est un test'\n"

    known_list = list(known_words)[-150:]
    llm_summary = sanitize_summary(summary)

    virtual_window = render_virtual_window(title_lengths + [0] * 135, summary, max_slots=150)

    bp_list = [f" {p['word']} (score={p['best_score']})" for p in llm_summary["best_probes"]]
    best_probes_str = "\n".join(bp_list) if bp_list else "Aucun"

    prompt = (
        "Contexte du puzzle Pédantix:\n"
        f"- Le TITRE exact a les longueurs de mots : {title_lengths}\n"
        f"- Fenêtre article : {virtual_window}\n"
        f"- Indices exacts découverts : {json.dumps(llm_summary['exact_terms'], ensure_ascii=False)}\n"
        f"MOTS THÉMATIQUES TRÈS PROCHES :\n"
        f"{best_probes_str}\n"
        f"- MOTS DÉJÀ TESTÉS : {json.dumps(known_list, ensure_ascii=False)}\n\n"
        "Contraintes:\n"
        "- 15 à 25 next_probes (mots uniques)\n"
        "- wikipedia_queries : 3 à 8 requêtes par mots-clés simples\n\n"
        "EXEMPLE DE RÉPONSE (JSON UNIQUEMENT) :\n"
        "{\n"
        '  "hypothesis": "Ceci est un grand bâtiment",\n'
        '  "next_probes": ["religion", "grandeur", "bâtiment"],\n'
        '  "wikipedia_queries": ["bâtiment", "grand temple"]\n'
        "}"
    )
    try:
        response = await llm_service.get_full_response(
            prompt=prompt, system_message=system, mode="question", provider=provider, thinking=thinking
        )
        return extract_json(response)
    except Exception as e:
        print(f"  [LLM probes] Erreur, fallback local: {e}")
        fb = [
            normalize_text(str(p.get("word", "")))
            for p in summary.get("best_probes", [])
            if normalize_text(str(p.get("word", ""))) not in known_words
        ]
        fb.extend(["biologie", "organisme", "evolution", "cellule", "temps"])
        return {"hypothesis": "Fallback local", "next_probes": _dedup(fb)[:25], "wikipedia_queries": fb[:5]}


async def ask_llm_candidates(
    title_lengths: list[int],
    masked_preview: str,
    summary: dict[str, Any],
    tested_titles: list[str],
    provider: str,
    thinking: str | bool | None = None,
) -> list[str]:
    system = (
        "Tu es un expert du jeu Pédantix. "
        "Réponds UNIQUEMENT avec un objet JSON contenant une liste de titres Wikipedia exacts. "
        "Règle ABSOLUE : Rédige TOUJOURS en français normal.\n"
    )
    if "ollama" in provider:
        system += "MAUVAIS : 'LeTitreEstCaché' ou 'UnTitre'\nBON : 'Le titre est caché' ou 'Un titre'\n"
    llm_summary = sanitize_summary(summary)
    tested_str = json.dumps(tested_titles[-50:], ensure_ascii=False) if tested_titles else "Aucun"
    virtual_window = render_virtual_window(title_lengths + [0] * 135, summary, max_slots=150)
    bp_list = [f" {p['word']} (score={p['best_score']})" for p in llm_summary["best_probes"]]

    prompt = (
        f"Contexte:\nLongueurs attendues : {title_lengths}\n"
        f"Fenêtre : {virtual_window}\n"
        f"Indices: {json.dumps(llm_summary['exact_terms'], ensure_ascii=False)}\n"
        f"Proches:\n{chr(10).join(bp_list)}\n"
        f"Déjà testés (échec): {tested_str}\n\n"
        "Propose 10 à 30 candidats (titres existants wikipedia) dans un JSON avec la clé 'candidates'."
    )
    try:
        response = await llm_service.get_full_response(
            prompt=prompt, system_message=system, mode="question", provider=provider, thinking=thinking
        )
        data = extract_json(response)
        candidates = data.get("candidates", [])
        return _dedup([c for c in candidates if isinstance(c, str) and c.strip()])
    except Exception as e:
        print(f"  [LLM candidates] Erreur: {e}")
        return []
