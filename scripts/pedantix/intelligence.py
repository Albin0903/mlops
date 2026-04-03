import json
import re
from collections import Counter
from typing import Any

from app.infrastructure.composition import get_generate_full_response_use_case
from scripts.pedantix.models import GuessResult, extract_words_from_phrase, normalize_text

generate_full_response_use_case = get_generate_full_response_use_case()

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
    # Determinants et pronoms
    "le", "la", "les", "de", "du", "des", "un", "une",
    "et", "ou", "a", "au", "aux", "d", "l",
    "est", "sont", "il", "elle", "ils", "elles",
    "ce", "ces", "cette", "ne", "pas", "plus", "en",
    "etre", "avoir", "bien", "aussi", "meme",
    "que", "qui", "dans", "sur", "pour", "avec",
    "t", "j", "n", "y", "se", "s", "c", "m",
    "son", "sa", "ses", "on", "tout", "tous",
    # Conjonctions, adverbes, prepositions (signaux de frequence, pas de theme)
    "mais", "donc", "ni", "car", "entre", "sous", "vers",
    "jusque", "lors", "tres", "peu", "beaucoup", "trop", "assez",
    "moins", "sans", "avant", "apres", "ici", "ainsi",
    "toujours", "jamais", "souvent", "comme",
    # Verbes tres frequents (sondes initiales, aucun signal thematique)
    "faire", "fait", "font", "pouvoir", "peut", "peuvent", "puisse",
    "devoir", "doit", "doivent", "aller", "va", "vont",
    "voir", "voit", "voient", "savoir", "sait", "savent",
    "falloir", "faut", "vouloir", "veut", "veulent",
    "dire", "dit", "disent", "donner", "donne", "donnent",
    "prendre", "prend", "prennent", "mettre", "met", "mettent",
    # Noms de categories generiques (sondes de triage)
    "siecle", "annee", "temps", "premier", "grand", "partie",
    "histoire", "guerre", "empire", "roi",
}

LLM_NOISE_WORDS = PROBE_STOPWORDS | {"meme", "aussi", "que", "c"}

PLACEHOLDER_PHRASES = {
    "ceci est un test",
    "this is a test",
    "cet article",
    "cette page",
    "unknown",
    "n/a",
}

PROBE_GARBAGE_WORDS = LLM_NOISE_WORDS | {
    "ceci",
    "test",
    "texte",
    "document",
    "truc",
    "chose",
    "element",
    "article",
    "page",
    "wikipedia",
    "pedantix",
}

QUERY_GARBAGE_WORDS = PROBE_GARBAGE_WORDS | {
    "info",
    "definition",
    "explication",
}

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(?P<json>[\s\S]*?)```", re.IGNORECASE)


def _is_placeholder_text(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return True
    if normalized in PLACEHOLDER_PHRASES:
        return True
    return any(phrase in normalized for phrase in PLACEHOLDER_PHRASES)


def _dedup_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        norm = normalize_text(item)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(item.strip())
    return out


def _sanitize_probe_terms(raw_probes: list[Any], known_words: set[str]) -> list[str]:
    known_norm = {normalize_text(w) for w in known_words if normalize_text(w)}
    terms: list[str] = []
    for probe in raw_probes:
        if not isinstance(probe, str):
            continue
        if _is_placeholder_text(probe):
            continue
        for token in extract_words_from_phrase(probe):
            norm = normalize_text(token)
            if len(norm) < 3 or norm in PROBE_GARBAGE_WORDS or norm in known_norm:
                continue
            # Keep only lexical tokens, no pure numbers.
            if re.fullmatch(r"\d+", norm):
                continue
            terms.append(norm)
    return _dedup_keep_order(terms)


def _sanitize_wikipedia_queries(raw_queries: list[Any]) -> list[str]:
    queries: list[str] = []
    for query in raw_queries:
        if not isinstance(query, str):
            continue
        cleaned = re.sub(r"\s+", " ", query).strip()
        if not cleaned or _is_placeholder_text(cleaned):
            continue
        tokens = [normalize_text(t) for t in extract_words_from_phrase(cleaned)]
        tokens = [t for t in tokens if t and t not in QUERY_GARBAGE_WORDS]
        if not tokens:
            continue
        # Keep short keyword queries (best for wiki search)
        if len(tokens) > 6:
            tokens = tokens[:6]
        queries.append(" ".join(tokens))
    return _dedup_keep_order(queries)


def _build_exact_position_map(summary: dict[str, Any], slot_count: int) -> dict[str, str]:
    position_map: dict[str, str] = {}
    for item in summary.get("exact_terms", []):
        if not isinstance(item, dict):
            continue
        term = normalize_text(str(item.get("term", "")))
        if not term:
            continue
        for pos in item.get("positions", []):
            if isinstance(pos, int) and 0 <= pos < slot_count:
                position_map[str(pos)] = term
    return position_map


def _candidate_matches_title_lengths(candidate: str, title_lengths: list[int]) -> bool:
    words = extract_words_from_phrase(candidate)
    if len(words) != len(title_lengths):
        return False
    return all(len(words[i]) == title_lengths[i] for i in range(len(title_lengths)))


def _is_small_provider(provider: str) -> bool:
    p = normalize_text(provider)
    return (
        "ollama-small" in p
        or "ollama-mini" in p
        or "qwen2b" in p
        or "qwen0.8b" in p
        or "gemma4-e2b" in p
        or p.endswith(":2b")
        or p.endswith(":0.8b")
    )


MORPH_SUFFIXES = [
    ("", "age"), ("", "eur"), ("", "euse"), ("", "ment"), ("", "tion"),
    ("", "ure"), ("", "ise"), ("", "iste"), ("", "able"), ("", "ible"),
    ("e", ""), ("er", ""), ("ir", ""), ("re", ""),
    ("ure", "age"), ("ure", "er"), ("ure", "eur"),
    ("age", "ure"), ("age", "er"), ("age", "eur"),
    ("tion", "teur"), ("tion", "ter"),
    ("ment", "er"), ("eur", "age"), ("eur", "ure"),
]


def _derive_morphological_variants(word: str) -> list[str]:
    """Genere des variantes morphologiques francaises d'un mot."""
    word = word.lower().strip()
    if len(word) < 4:
        return []

    variants: list[str] = []

    for suffix_remove, suffix_add in MORPH_SUFFIXES:
        if suffix_remove and word.endswith(suffix_remove):
            stem = word[: -len(suffix_remove)]
            candidate = stem + suffix_add
            if len(candidate) >= 4 and candidate != word:
                variants.append(candidate)
        elif not suffix_remove:
            candidate = word + suffix_add
            if candidate != word:
                variants.append(candidate)

    # Prefixes
    for prefix in ["re", "de", "pre"]:
        if not word.startswith(prefix):
            variants.append(prefix + word)
        elif len(word) > len(prefix) + 2:
            variants.append(word[len(prefix):])

    return list(dict.fromkeys(variants))


def _compress_masked_preview(masked_preview: str, chunk_size: int = 900) -> str:
    if len(masked_preview) <= chunk_size * 3:
        return masked_preview
    middle_start = max(0, len(masked_preview) // 2 - chunk_size // 2)
    middle = masked_preview[middle_start : middle_start + chunk_size]
    tail = masked_preview[-chunk_size:]
    head = masked_preview[:chunk_size]
    return f"{head}\n...[middle omitted]...\n{middle}\n...[tail]...\n{tail}"


def _split_glued_words(text: str) -> str:
    return re.sub(r"([a-zà-ÿ])([A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸ])", r"\1 \2", text)


def _extract_relaxed_json(text: str) -> dict[str, Any]:
    hypothesis_match = re.search(r'"hypothesis"\s*:\s*"(?P<h>[^"\\]*(?:\\.[^"\\]*)*)"', text)
    probes_match = re.search(r'"next_probes"\s*:\s*\[(?P<body>[\s\S]*?)(?:\]|$)', text)
    queries_match = re.search(r'"wikipedia_queries"\s*:\s*\[(?P<body>[\s\S]*?)(?:\]|$)', text)
    candidates_match = re.search(r'"candidates"\s*:\s*\[(?P<body>[\s\S]*?)(?:\]|$)', text)

    payload: dict[str, Any] = {}
    if hypothesis_match:
        payload["hypothesis"] = hypothesis_match.group("h")
    if probes_match:
        payload["next_probes"] = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', probes_match.group("body"))
    if queries_match:
        payload["wikipedia_queries"] = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', queries_match.group("body"))
    if candidates_match:
        payload["candidates"] = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', candidates_match.group("body"))

    if payload:
        return payload
    raise ValueError("Aucun champ JSON exploitable dans la réponse LLM")


def extract_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    block = JSON_BLOCK_RE.search(raw)
    if block:
        raw = block.group("json").strip()

    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        try:
            return _extract_relaxed_json(raw)
        except ValueError:
            raise ValueError(f"Réponse LLM non exploitable: {text[:200]}") from None

    raw_json = raw[start : end + 1]
    raw_json = raw_json.replace("\\", "\\\\")
    raw_json = _split_glued_words(raw_json)

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        try:
            return json.loads(raw_json, strict=False)
        except json.JSONDecodeError:
            try:
                return _extract_relaxed_json(raw)
            except ValueError:
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
    slot_lengths: list[int] | None = None,
) -> dict[str, Any]:
    system = (
        "Tu joues a un benchmark de resolution Pedantix. "
        "Objectif: proposer des actions utiles, pas de texte inutile. "
        "Reponds UNIQUEMENT avec un objet JSON valide. "
        "Interdit: phrases placeholders comme 'ceci est un test', 'cet article', 'cette page'.\n"
        "Format strict:\n"
        "{\n"
        '  "hypothesis": "titre court plausible",\n'
        '  "next_probes": ["mot1", "mot2"],\n'
        '  "wikipedia_queries": ["requete utile 1", "requete utile 2"]\n'
        "}\n"
        "Regles: next_probes doit contenir des mots unitaires (pas de phrase), utiles, dedupes, non generiques.\n"
    )
    if "ollama" in provider:
        system += "Si le modele hesite, privilegie des mots thematiques concrets plutot que du blabla.\n"

    small_provider = _is_small_provider(provider)
    known_cap = 80 if small_provider else 200
    known_list = sorted({normalize_text(w) for w in known_words if normalize_text(w)})[:known_cap]
    llm_summary = sanitize_summary(summary)

    context_slots = slot_lengths if slot_lengths else title_lengths + [0] * 135

    context_payload = {
        "title_lengths": title_lengths,
        "slot_count": len(context_slots),
        "known_exact_terms": llm_summary["exact_terms"][:12 if small_provider else 30],
        "top_proximity": llm_summary["best_probes"][:12 if small_provider else 20],
        "known_words": known_list,
    }

    bp_list = [f" {p['word']} (score={p['best_score']})" for p in llm_summary["best_probes"]]
    best_probes_str = "\n".join(bp_list) if bp_list else "Aucun"

    # Build title constraint hint
    if len(title_lengths) == 1:
        title_hint = (
            f"IMPORTANT: Le titre Wikipedia cible fait exactement {title_lengths[0]} lettres (1 seul mot).\n"
            f"Concentre tes suggestions sur des mots de {title_lengths[0]} lettres.\n"
        )
    else:
        lens_str = " ".join(str(length) for length in title_lengths)
        title_hint = (
            f"IMPORTANT: Le titre Wikipedia cible fait {len(title_lengths)} mots "
            f"avec les longueurs exactes : [{lens_str}].\n"
        )

    prompt = (
        "Contexte complet du puzzle Pedantix (JSON):\n"
        f"{json.dumps(context_payload, ensure_ascii=False)}\n\n"
        f"{title_hint}\n"
        "Objectif:\n"
        "1) Trouver des mots discriminants qui augmentent les indices exacts.\n"
        "2) Donner des requetes wikipedia courtes mais tres informatives.\n"
        "3) Eviter tout mot deja teste et tout mot generique.\n\n"
        "Contraintes de sortie:\n"
        "- hypothesis: phrase courte (2 a 10 mots) et pertinente.\n"
        "- next_probes: 15 a 25 mots, chacun sans espace, dedupe, jamais placeholders.\n"
        "- wikipedia_queries: 3 a 8 requetes, chacune 1 a 6 mots.\n"
        f"Repere proximite actuel:\n{best_probes_str}\n"
    )
    try:
        response = await generate_full_response_use_case.execute(
            prompt=prompt, system_message=system, mode="question", provider=provider, thinking=thinking
        )
        data = extract_json(response)
        probes = _sanitize_probe_terms(data.get("next_probes", []), known_words)
        queries = _sanitize_wikipedia_queries(data.get("wikipedia_queries", []))

        if len(queries) < 3:
            queries.extend(_sanitize_wikipedia_queries(probes[:8]))
            queries = _dedup_keep_order(queries)

        if len(probes) < 12:
            fallback_probes = [
                normalize_text(str(item.get("term", "")))
                for item in llm_summary.get("exact_terms", [])
                if normalize_text(str(item.get("term", ""))) and normalize_text(str(item.get("term", ""))) not in known_words
            ]
            fallback_probes.extend([
                normalize_text(str(item.get("word", "")))
                for item in llm_summary.get("best_probes", [])
                if normalize_text(str(item.get("word", ""))) and normalize_text(str(item.get("word", ""))) not in known_words
            ])
            fallback_probes.extend(build_fallback_probes(summary))
            probes = _dedup_keep_order(probes + _sanitize_probe_terms(fallback_probes, known_words))

        hypothesis_raw = str(data.get("hypothesis", "")).strip()
        hypothesis = "" if _is_placeholder_text(hypothesis_raw) else hypothesis_raw

        # Inject morphological variants from high-scoring proximity words
        morph_probes: list[str] = []
        for probe_item in llm_summary.get("best_probes", []):
            score = probe_item.get("best_score", 0)
            word = normalize_text(str(probe_item.get("word", "")))
            if score >= 70 and word and word not in known_words:
                variants = _derive_morphological_variants(word)
                morph_probes.extend(v for v in variants if v not in known_words)
        if morph_probes:
            probes = _dedup_keep_order(probes + _sanitize_probe_terms(morph_probes, known_words))

        return {
            "hypothesis": hypothesis,
            "next_probes": probes[:30],
            "wikipedia_queries": queries[:8],
        }
    except Exception as e:
        print(f"  [LLM probes] Erreur, fallback local: {e}")
        fb = [
            normalize_text(str(p.get("word", "")))
            for p in summary.get("best_probes", [])
            if normalize_text(str(p.get("word", ""))) and normalize_text(str(p.get("word", ""))) not in known_words
        ]
        fb.extend(build_fallback_probes(summary))
        sanitized_fb = _sanitize_probe_terms(fb, known_words)
        return {
            "hypothesis": "fallback",
            "next_probes": sanitized_fb[:25],
            "wikipedia_queries": _sanitize_wikipedia_queries(sanitized_fb[:8])[:5],
        }


async def ask_llm_candidates(
    title_lengths: list[int],
    masked_preview: str,
    summary: dict[str, Any],
    tested_titles: list[str],
    provider: str,
    thinking: str | bool | None = None,
    known_words: set[str] | None = None,
    slot_lengths: list[int] | None = None,
) -> list[str]:
    system = (
        "Tu joues a Pedantix en mode benchmark. "
        "Reponds UNIQUEMENT avec un objet JSON contenant la cle 'candidates'. "
        "Chaque candidat doit etre un titre Wikipedia plausible, utile, sans blabla.\n"
    )
    if "ollama" in provider:
        system += "Evite toute phrase inutile ou placeholder.\n"

    small_provider = _is_small_provider(provider)
    llm_summary = sanitize_summary(summary)
    tested_str = json.dumps(tested_titles[-50:], ensure_ascii=False) if tested_titles else "Aucun"
    context_slots = slot_lengths if slot_lengths else title_lengths + [0] * 135
    known_cap = 80 if small_provider else 200
    known_list = sorted({normalize_text(w) for w in (known_words or set()) if normalize_text(w)})[:known_cap]

    context_payload = {
        "title_lengths": title_lengths,
        "slot_count": len(context_slots),
        "known_exact_terms": llm_summary["exact_terms"][:12 if small_provider else 30],
        "top_proximity": llm_summary["best_probes"][:12 if small_provider else 20],
        "known_words": known_list,
        "already_tested_titles": tested_titles[-40:],
    }
    bp_list = [f" {p['word']} (score={p['best_score']})" for p in llm_summary["best_probes"]]

    # Build title constraint hint
    if len(title_lengths) == 1:
        title_hint = (
            f"IMPORTANT: Le titre Wikipedia cible fait exactement {title_lengths[0]} lettres (1 seul mot).\n"
            f"Ne propose QUE des titres d'un seul mot de {title_lengths[0]} lettres.\n"
        )
    else:
        lens_str = " ".join(str(length) for length in title_lengths)
        title_hint = (
            f"IMPORTANT: Le titre Wikipedia fait {len(title_lengths)} mots "
            f"avec les longueurs exactes : [{lens_str}].\n"
        )

    prompt = (
        "Contexte complet (JSON):\n"
        f"{json.dumps(context_payload, ensure_ascii=False)}\n\n"
        f"{title_hint}\n"
        "Objectif: proposer 15 a 40 titres wikipedia potentiels, precis et varies, sans repetitions.\n"
        "Prioriser les titres qui matchent strictement la structure des longueurs du titre cible.\n"
        "Sortie JSON stricte, uniquement la cle 'candidates'.\n"
        f"Rappel proximite:\n{chr(10).join(bp_list)}\n"
        f"Deja testes (echec): {tested_str}\n"
    )
    try:
        response = await generate_full_response_use_case.execute(
            prompt=prompt, system_message=system, mode="question", provider=provider, thinking=thinking
        )
        data = extract_json(response)
        raw_candidates = data.get("candidates", [])

        candidates = []
        for candidate in raw_candidates:
            if not isinstance(candidate, str):
                continue
            cleaned = re.sub(r"\s+", " ", candidate).strip()
            if not cleaned or _is_placeholder_text(cleaned):
                continue
            candidates.append(cleaned)

        candidates = _dedup_keep_order(candidates)
        if title_lengths:
            matching = [c for c in candidates if _candidate_matches_title_lengths(c, title_lengths)]
            others = [c for c in candidates if c not in matching]
            candidates = matching + others

        return candidates[:50]
    except Exception as e:
        print(f"  [LLM candidates] Erreur: {e}")
        return []
