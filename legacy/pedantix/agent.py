import json
import re
from typing import Any

from app.infrastructure.composition import get_execute_agent_call_use_case
from legacy.pedantix.client_wikipedia import search_wikipedia_titles
from legacy.pedantix.intelligence import (
    ask_llm_candidates,
    ask_llm_probes,
    build_fallback_probes,
    extract_best_score,
    summarize_results,
)
from legacy.pedantix.models import extract_words_from_phrase, normalize_text

execute_agent_call_use_case = get_execute_agent_call_use_case()

NOISE_TERMS = {
    "page",
    "article",
    "wikipedia",
    "pedantix",
    "grand",
    "grande",
    "grands",
    "grandes",
    "temps",
    "histoire",
    "ville",
    "pays",
    "etat",
    "qui",
    "que",
    "dont",
    "pour",
    "avec",
    "sans",
}

# Definition des schemas d'outils pour les LLMs (format OpenAI/Groq/Gemini)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_game_state",
            "description": "Récupère l'état actuel du jeu : mots trouvés, meilleurs scores de proximité et aperçu du texte.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "brainstorm_and_test_probes",
            "description": "Délègue à un sous-agent expert l'analyse de l'état du jeu pour générer et tester automatiquement un lot de 20 nouveaux mots pertinents (sondes heuristiques). À utiliser quand tu as besoin de plus d'indices.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "brainstorm_and_test_wiki_titles",
            "description": "Délègue à un sous-agent expert la recherche et le test immédiat de titres de pages Wikipédia correspondants aux indices actuels. À utiliser quand tu as de bons mots trouvés de proximité ou exacts.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    }
]


class PedantixAgent:
    def __init__(
        self,
        puzzle_number: int,
        title_lengths: list[int],
        slot_lengths: list[int],
        masked_preview: str,
        cli_context: Any,
        provider: str = "gemini",
        sub_provider: str = "ollama-small",
        thinking: str = "off",
        max_turns: int = 15,
    ):
        self.puzzle_number = puzzle_number
        self.title_lengths = title_lengths
        self.slot_lengths = slot_lengths
        self.masked_preview = masked_preview
        self.context = cli_context
        self.provider = provider
        self.sub_provider = sub_provider
        self.thinking = thinking

        self.system_message = (
            "Tu es un Agent Manageur chargé de diriger la résolution du puzzle Pédantix. "
            "But : Deviner le titre crypté d'une page Wikipedia.\n\n"
            "Outils de Délégation à ta disposition :\n"
            "- `get_game_state` : Constater les mots déjà trouvés.\n"
            "- `brainstorm_and_test_probes` : Assigne à un sous-agent la tâche d'analyser le contexte et tester un lot de 20 nouveaux mots intelligents.\n"
            "- `brainstorm_and_test_wiki_titles` : Assigne à un sous-agent la tâche de chercher sur Wikipédia des titres candidats et les tester en bloc (utile s'il y a des mots pertinents trouvés).\n"
            "Le sous-agent tourne sur un modèle secondaire rapide/local.\n\n"
            "Règles :\n"
            "1. Privilégie LOURDEMENT L'UTILISATION DES SOUS-AGENTS (`brainstorm_...`) plutôt que de tester les mots toi-même.\n"
            "2. Observe les réponses, tu dois jouer le rôle de chef d'orchestre.\n"
            "3. Utilise d'abord `get_game_state` pour constater l'état des sondes par défaut (c'est fait avant toi).\n"
            "4. Enchaîne avec `brainstorm_and_test_probes` si tu manques d'indices ou `brainstorm_and_test_wiki_titles` si l'espoir est proche.\n"
            "5. Tu ne dois pas rester bloqué en texte libre : si tu hésites, appelle un des deux outils de sous-agent."
        )
        self.history = [{"role": "system", "content": self.system_message}]
        self.max_turns = max_turns
        self.tested_wiki_titles: set[str] = set()
        self.tested_wiki_queries: set[str] = set()
        self.no_progress_streak = 0
        self.force_macro_tool: str | None = None

    def _extract_hypothesis_candidates(self, text: str) -> list[str]:
        raw_candidates: list[str] = []
        for pattern in [r'"([^"\n]{4,120})"', r"«([^»\n]{4,120})»", r"'([^'\n]{4,120})'"]:
            raw_candidates.extend(re.findall(pattern, text))

        probable = re.search(r"probablement\s+([a-zà-ÿ0-9\-\(\)' ]{4,120})", text, flags=re.IGNORECASE)
        if probable:
            raw_candidates.append(probable.group(1))

        cleaned: list[str] = []
        seen: set[str] = set()
        for candidate in raw_candidates:
            c = candidate.strip(" .,:;!?-\n\t\"'")
            if len(c.split()) < 2:
                continue
            c_norm = normalize_text(c)
            if c_norm in seen:
                continue
            seen.add(c_norm)
            cleaned.append(c)
        return cleaned[:3]

    def _title_shape_matches(self, title: str) -> bool:
        words = extract_words_from_phrase(title)
        if len(words) != len(self.title_lengths):
            return False
        return all(len(words[i]) == self.title_lengths[i] for i in range(len(self.title_lengths)))

    def _select_recovery_tool(self) -> str:
        summary = summarize_results(self.context.all_results)
        strong_exact_terms = len(summary.get("exact_terms", []))
        strong_probes = len(summary.get("best_probes", []))
        if strong_exact_terms >= 2 or strong_probes >= 5:
            return "brainstorm_and_test_wiki_titles"
        return "brainstorm_and_test_probes"

    def _progress_signal(self) -> tuple[int, int]:
        summary = summarize_results(self.context.all_results)
        exact_terms = summary.get("exact_terms", [])
        covered_positions: set[int] = set()
        for item in exact_terms:
            if not isinstance(item, dict):
                continue
            for pos in item.get("positions", []):
                if isinstance(pos, int) and 0 <= pos < len(self.title_lengths):
                    covered_positions.add(pos)
        return len(exact_terms), len(covered_positions)

    def _is_noise_term(self, value: str) -> bool:
        norm = normalize_text(value)
        return len(norm) < 3 or norm in NOISE_TERMS

    def _extract_probe_terms(self, probe_plan: dict[str, Any]) -> list[str]:
        raw_probes = probe_plan.get("next_probes", [])
        terms: list[str] = []
        seen: set[str] = set()
        for probe in raw_probes:
            if not isinstance(probe, str):
                continue
            for token in extract_words_from_phrase(probe):
                norm = normalize_text(token)
                if self._is_noise_term(norm) or norm in seen or norm in self.context.known_words:
                    continue
                seen.add(norm)
                terms.append(norm)
        return terms

    def _build_thematic_probes(self, summary: dict[str, Any]) -> list[str]:
        signal_terms = {
            normalize_text(str(item.get("term", "")))
            for item in summary.get("exact_terms", [])
            if normalize_text(str(item.get("term", "")))
        }
        signal_terms |= {
            normalize_text(str(item.get("word", "")))
            for item in summary.get("best_probes", [])
            if normalize_text(str(item.get("word", "")))
        }

        thematic: list[str] = []
        if signal_terms & {"empire", "religion", "romain", "rome", "antique", "culte"}:
            thematic.extend(
                [
                    "romain",
                    "rome",
                    "antique",
                    "mythologie",
                    "dieux",
                    "culte",
                    "rituel",
                    "temple",
                    "paien",
                    "paganisme",
                    "senat",
                    "imperial",
                    "republique",
                    "citoyen",
                    "civilisation",
                ]
            )
        if signal_terms & {"guerre", "roi", "dynastie", "histoire"}:
            thematic.extend(["dynastie", "monarchie", "couronne", "empereur", "conquete", "province"])

        thematic.extend(["philosophie", "theologie", "doctrine", "offrande", "sacrifice"])

        deduped: list[str] = []
        seen: set[str] = set()
        for term in thematic:
            norm = normalize_text(term)
            if self._is_noise_term(norm) or norm in seen or norm in self.context.known_words:
                continue
            seen.add(norm)
            deduped.append(norm)
        return deduped[:25]

    def _signal_terms(self, summary: dict[str, Any]) -> set[str]:
        signals: set[str] = {
            normalize_text(str(item.get("term", "")))
            for item in summary.get("exact_terms", [])
            if normalize_text(str(item.get("term", "")))
        }
        signals |= {
            normalize_text(str(item.get("word", "")))
            for item in summary.get("best_probes", [])
            if normalize_text(str(item.get("word", "")))
        }
        return {s for s in signals if not self._is_noise_term(s)}

    def _probe_relevance_count(self, probes: list[str], summary: dict[str, Any]) -> int:
        signals = self._signal_terms(summary)
        thematic = set(self._build_thematic_probes(summary))
        score = 0
        for probe in probes:
            p = normalize_text(probe)
            if p in signals or p in thematic:
                score += 1
                continue
            if any(len(s) >= 5 and (p.startswith(s[:5]) or s.startswith(p[:5])) for s in signals):
                score += 1
        return score

    def _query_relevance_count(self, queries: list[str], summary: dict[str, Any]) -> int:
        signals = self._signal_terms(summary)
        thematic = set(self._build_thematic_probes(summary))
        score = 0
        for query in queries:
            tokens = [normalize_text(t) for t in extract_words_from_phrase(query)]
            if any(t in signals or t in thematic for t in tokens):
                score += 1
        return score

    def _candidate_relevance_score(self, title: str, summary: dict[str, Any]) -> int:
        signals = self._signal_terms(summary)
        thematic = set(self._build_thematic_probes(summary))
        words = [normalize_text(w) for w in extract_words_from_phrase(title)]
        if not words:
            return 0
        score = 0
        for word in words:
            if word in signals:
                score += 3
            elif word in thematic:
                score += 2
        if self._title_shape_matches(title):
            score += 3
        return score

    def _build_fallback_queries(self, summary: dict[str, Any]) -> list[str]:
        exact_terms = [
            normalize_text(str(item.get("term", "")))
            for item in summary.get("exact_terms", [])
            if normalize_text(str(item.get("term", ""))) and not self._is_noise_term(str(item.get("term", "")))
        ]
        probe_terms = [
            normalize_text(str(item.get("word", "")))
            for item in summary.get("best_probes", [])
            if normalize_text(str(item.get("word", ""))) and not self._is_noise_term(str(item.get("word", "")))
        ]

        candidates = exact_terms[:6] + probe_terms[:8]
        queries: list[str] = []
        seen: set[str] = set()
        for term in candidates:
            if term in seen:
                continue
            seen.add(term)
            queries.append(term)

        # Build a few bi-gram queries for better wikipedia precision.
        for i in range(min(len(candidates) - 1, 5)):
            q = f"{candidates[i]} {candidates[i + 1]}".strip()
            qn = normalize_text(q)
            if qn and qn not in seen:
                seen.add(qn)
                queries.append(q)

        return queries[:10]

    def _reconstruct_title_if_covered(self) -> str | None:
        summary = summarize_results(self.context.all_results)
        exacts = summary.get("exact_terms") or []
        covered_positions: dict[int, str] = {}

        for item in exacts:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term", "")).strip()
            positions = item.get("positions") or []
            if not term:
                continue
            for p in positions:
                if isinstance(p, int) and 0 <= p < len(self.title_lengths):
                    covered_positions[p] = term

        if len(covered_positions) != len(self.title_lengths):
            return None

        reconstructed = " ".join(covered_positions[i] for i in range(len(self.title_lengths))).strip()
        if self._title_shape_matches(reconstructed):
            return reconstructed
        return None

    async def _try_auto_validate_hypothesis(self, text: str) -> str | None:
        if not text:
            return None
        candidates = self._extract_hypothesis_candidates(text)
        if not candidates:
            return None

        from legacy.pedantix.client_wikipedia import resolve_wikipedia_title

        for candidate in candidates:
            resolved = await resolve_wikipedia_title(self.context.client, candidate)
            if not resolved:
                continue
            if not self._title_shape_matches(resolved):
                continue

            print(f"info: Validation auto d'hypothèse agent: {resolved}")
            words = extract_words_from_phrase(resolved)
            _, solution = await self.context.score_batch(words, tag="agent-hypothesis")
            if solution and solution.solution:
                return solution.solution
        return None

    async def run(self):
        print(f"info: Démarrage de l'agent ReAct ({self.provider})...")

        # Le premier message utilisateur suffit, pas besoin de ré-appuyer à chaque tour.
        self.history.append({"role": "user", "content": "Analyse l'état initial et commence la résolution."})
        text_only_turns = 0

        for turn in range(1, self.max_turns + 1):
            print(f"\ninfo: --- Tour Agent {turn}/{self.max_turns} ---")

            # Appel au LLM
            response_data = await execute_agent_call_use_case.execute(
                messages=self.history,
                tools=TOOLS,
                provider=self.provider,
                thinking=self.thinking,
            )

            if response_data["type"] == "text":
                content = (response_data["content"] or "...").strip() or "..."
                print(f"Agent Thought: {content}")
                self.history.append({"role": "assistant", "content": content})

                auto_solution = await self._try_auto_validate_hypothesis(content)
                if auto_solution:
                    print(f"info: SOLUTION TROUVÉE par validation auto: {auto_solution}")
                    print(f"Lien : https://fr.wikipedia.org/wiki/{auto_solution.replace(' ', '_')}")
                    return

                text_only_turns += 1
                if text_only_turns >= 1:
                    recovery_tool = self._select_recovery_tool()
                    print(f"info: Tour texte sans action, rattrapage auto via {recovery_tool}...")
                    observation = await self.execute_tool(recovery_tool, {})
                    self.history.append(
                        {
                            "role": "user",
                            "content": (
                                "Tu dois agir via outil. Résultat du rattrapage automatique : "
                                f"{json.dumps(observation, ensure_ascii=False)}. "
                                "Au prochain tour, appelle un outil et évite les pensées longues."
                            ),
                        }
                    )
                    if isinstance(observation, dict) and observation.get("solved"):
                        print(f"info: SOLUTION TROUVÉE par rattrapage auto ({recovery_tool}) : {observation.get('solution')}")
                        if observation.get("solution"):
                            print(f"Lien : https://fr.wikipedia.org/wiki/{observation.get('solution').replace(' ', '_')}")
                        return

                    reconstructed = self._reconstruct_title_if_covered()
                    if reconstructed:
                        print(f"info: Titre reconstruit à partir des positions exactes : {reconstructed}")
                        print(f"Lien : https://fr.wikipedia.org/wiki/{reconstructed.replace(' ', '_')}")
                        return

                    text_only_turns = 0
                continue

            elif response_data["type"] == "tool_calls":
                text_only_turns = 0
                # 1. Message Assistant obligatoire avec les tool_calls
                assistant_msg = {
                    "role": "assistant",
                    "content": response_data.get("content") or "Action en cours...",
                    "tool_calls": []
                }

                tool_requests = []
                for call in response_data["calls"]:
                    name = call["name"]
                    args = call["args"] or {}
                    call_id = f"call_{turn}_{name}" # Génère un ID stable

                    assistant_msg["tool_calls"].append({
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)}
                    })
                    tool_requests.append((name, args, call_id))

                self.history.append(assistant_msg)

                # 2. Exécution des outils et ajout des résultats
                for name, args, call_id in tool_requests:
                    if self.force_macro_tool and name in {
                        "brainstorm_and_test_probes",
                        "brainstorm_and_test_wiki_titles",
                    }:
                        if name != self.force_macro_tool:
                            print(f"info: Override anti-stagnation: {name} -> {self.force_macro_tool}")
                            name = self.force_macro_tool
                            args = {}
                        self.force_macro_tool = None

                    if name in {"brainstorm_and_test_probes", "brainstorm_and_test_wiki_titles", "get_game_state"}:
                        args = {}

                    print(f"info: Appel outil: {name}({args})")
                    before_signal = self._progress_signal() if name in {
                        "brainstorm_and_test_probes",
                        "brainstorm_and_test_wiki_titles",
                    } else None
                    observation = await self.execute_tool(name, args)
                    after_signal = self._progress_signal() if before_signal else None

                    self.history.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": json.dumps(observation, ensure_ascii=False)
                    })

                    if name == "guess_words" and isinstance(observation, list) and any(r.get("solved") for r in observation):
                        print("info: Solution trouvée par l'agent unitaire !")
                        return

                    if name in ["brainstorm_and_test_probes", "brainstorm_and_test_wiki_titles"]:
                        if before_signal and after_signal and after_signal <= before_signal:
                            self.no_progress_streak += 1
                        else:
                            self.no_progress_streak = 0

                        if self.no_progress_streak >= 2:
                            self.force_macro_tool = (
                                "brainstorm_and_test_wiki_titles"
                                if name == "brainstorm_and_test_probes"
                                else "brainstorm_and_test_probes"
                            )
                            self.no_progress_streak = 0

                        if isinstance(observation, dict) and observation.get("solved"):
                            print(f"info: SOLUTION TROUVÉE par l'agent ! (sous-agent {name}) : {observation.get('solution')}")
                            if observation.get("solution"):
                                url_sol = observation.get("solution").replace(' ', '_')
                                print(f"Lien : https://fr.wikipedia.org/wiki/{url_sol}")
                            return

                        reconstructed = self._reconstruct_title_if_covered()
                        if reconstructed:
                            print(f"info: Titre reconstruit à partir des positions exactes : {reconstructed}")
                            print(f"Lien : https://fr.wikipedia.org/wiki/{reconstructed.replace(' ', '_')}")
                            return

        print("info: Fin des tours agent sans solution.")

    async def execute_tool(self, name: str, args: dict[str, Any] | None) -> Any:
        args = args or {}
        if name == "get_game_state":
            summary = summarize_results(self.context.all_results)
            return {
                "puzzle_number": self.puzzle_number,
                "title_lengths": self.title_lengths,
                "discovered_terms": summary.get("exact_terms", [])[:15],
                "proximity_scores": summary.get("best_probes", [])[:10],
                "masked_preview": self.masked_preview[:200]
            }

        elif name == "guess_words":
            words = args.get("words", [])
            results, solution = await self.context.score_batch(words, tag="agent")
            return [
                {
                    "word": r.word,
                    "solved": r.solved,
                    "exact_hits": len(r.exact_hits),
                    "best_approx": extract_best_score(r.approx_hits)
                }
                for r in results
            ]

        elif name == "search_wikipedia":
            query = args.get("query", "")
            titles = await search_wikipedia_titles(self.context.client, [query], per_query=5)
            # Dépolluer les titres pour le LLM
            return {"candidates": titles[:10]}

        elif name == "analyze_wikipedia_page":
            title = args.get("title", "")
            from legacy.pedantix.client_wikipedia import resolve_wikipedia_title
            resolved = await resolve_wikipedia_title(self.context.client, title)
            if not resolved:
                return "Page introuvable."

            words = extract_words_from_phrase(resolved)
            return {
                "resolved_title": resolved,
                "title_word_count": len(words),
                "expected_word_count": len(self.title_lengths),
                "potential_match": len(words) == len(self.title_lengths)
            }

        elif name == "brainstorm_and_test_probes":
            print("info: -> Orchestration du sous-agent pour les sondes...")
            summary = summarize_results(self.context.all_results)
            probe_plan = await ask_llm_probes(
                self.title_lengths,
                self.masked_preview,
                summary,
                self.sub_provider,
                self.context.known_words,
                thinking="off",
                slot_lengths=self.slot_lengths,
            )
            llm_probes = self._extract_probe_terms(probe_plan)

            relevance = self._probe_relevance_count(llm_probes, summary)
            if (len(llm_probes) < 10 or relevance < max(4, len(llm_probes) // 3)) and self.provider != self.sub_provider:
                print(f"info: -> Escalade qualité des sondes via provider principal ({self.provider})...")
                strong_plan = await ask_llm_probes(
                    self.title_lengths,
                    self.masked_preview,
                    summary,
                    self.provider,
                    self.context.known_words,
                    thinking="off",
                    slot_lengths=self.slot_lengths,
                )
                for term in self._extract_probe_terms(strong_plan):
                    if term not in llm_probes:
                        llm_probes.append(term)

            if len(llm_probes) < 8:
                for term in self._build_thematic_probes(summary):
                    if term not in llm_probes:
                        llm_probes.append(term)
                    if len(llm_probes) >= 20:
                        break

            if len(llm_probes) < 8:
                seen = set(llm_probes)
                for fallback in build_fallback_probes(summary):
                    norm = normalize_text(fallback)
                    if self._is_noise_term(norm) or norm in seen or norm in self.context.known_words:
                        continue
                    seen.add(norm)
                    llm_probes.append(norm)
                    if len(llm_probes) >= 20:
                        break

            llm_probes = llm_probes[:20]

            print(f"info: -> Sous-agent propose {len(llm_probes)} mots. Test en cours...")
            _, solution = await self.context.score_batch(llm_probes, tag="agent-macro")
            return {
                "action": "tested_probes",
                "words_tested": len(llm_probes),
                "solved": solution is not None,
                "solution": solution.solution if solution else None
            }

        elif name == "brainstorm_and_test_wiki_titles":
            print("info: -> Orchestration du sous-agent pour requêtes Wikipédia...")
            summary = summarize_results(self.context.all_results)
            tested_titles: list[str] = []

            # 1. Ask for titles
            probe_plan = await ask_llm_probes(
                self.title_lengths,
                self.masked_preview,
                summary,
                self.sub_provider,
                self.context.known_words,
                thinking="off",
                slot_lengths=self.slot_lengths,
            )
            llm_queries: list[str] = []
            seen_queries: set[str] = set()
            for q in probe_plan.get("wikipedia_queries", []):
                if not isinstance(q, str):
                    continue
                cleaned = q.strip()
                if len(cleaned) < 3:
                    continue
                q_norm = normalize_text(cleaned)
                if q_norm in seen_queries or self._is_noise_term(q_norm):
                    continue
                seen_queries.add(q_norm)
                llm_queries.append(cleaned)

            relevance = self._query_relevance_count(llm_queries, summary)
            if (len(llm_queries) < 3 or relevance < 2) and self.provider != self.sub_provider:
                print(f"info: -> Escalade qualité des requêtes via provider principal ({self.provider})...")
                strong_plan = await ask_llm_probes(
                    self.title_lengths,
                    self.masked_preview,
                    summary,
                    self.provider,
                    self.context.known_words,
                    thinking="off",
                    slot_lengths=self.slot_lengths,
                )
                for q in strong_plan.get("wikipedia_queries", []):
                    if not isinstance(q, str):
                        continue
                    cleaned = q.strip()
                    q_norm = normalize_text(cleaned)
                    if len(cleaned) < 3 or q_norm in seen_queries or self._is_noise_term(q_norm):
                        continue
                    seen_queries.add(q_norm)
                    llm_queries.append(cleaned)

            if len(llm_queries) < 3:
                for query in self._build_fallback_queries(summary):
                    q_norm = normalize_text(query)
                    if q_norm in seen_queries or self._is_noise_term(q_norm):
                        continue
                    seen_queries.add(q_norm)
                    llm_queries.append(query)
                    if len(llm_queries) >= 8:
                        break

            if not llm_queries:
                return {"action": "wiki_search", "result": "Aucune requête générée par le sous-agent."}

            llm_candidates = await ask_llm_candidates(
                self.title_lengths,
                self.masked_preview,
                summary,
                list(self.tested_wiki_titles)[-100:],
                self.provider,
                thinking="off",
                known_words=self.context.known_words,
                slot_lengths=self.slot_lengths,
            )
            for candidate in llm_candidates[:30]:
                if not isinstance(candidate, str):
                    continue
                c_norm = normalize_text(candidate)
                if c_norm in self.tested_wiki_titles:
                    continue
                tested_titles.append(candidate)

            # 2. Search wiki
            new_queries = []
            for query in llm_queries:
                q_norm = normalize_text(query)
                if q_norm in self.tested_wiki_queries:
                    continue
                self.tested_wiki_queries.add(q_norm)
                new_queries.append(query)

            wiki_titles = await search_wikipedia_titles(self.context.client, new_queries[:6], per_query=6) if new_queries else []
            if not wiki_titles and not tested_titles:
                return {"action": "wiki_search", "result": "Aucun titre trouvé sur Wikipédia."}

            shape_matching = [t for t in wiki_titles if self._title_shape_matches(t)]
            others = [t for t in wiki_titles if t not in shape_matching]
            merged_candidates = tested_titles + shape_matching + others

            merged_candidates.sort(key=lambda title: self._candidate_relevance_score(title, summary), reverse=True)

            unique_titles: list[str] = []
            seen_titles: set[str] = set()
            for title in merged_candidates:
                t_norm = normalize_text(title)
                if not t_norm or t_norm in seen_titles or t_norm in self.tested_wiki_titles:
                    continue
                if self._candidate_relevance_score(title, summary) <= 0:
                    continue
                seen_titles.add(t_norm)
                unique_titles.append(title)
                if len(unique_titles) >= 20:
                    break

            tested_titles = unique_titles
            if not tested_titles:
                return {"action": "wiki_search", "result": "Aucun nouveau titre à tester."}

            for title in tested_titles:
                self.tested_wiki_titles.add(normalize_text(title))

            # 3. Test titles
            words: list[str] = []
            seen_words: set[str] = set()
            for c in tested_titles:
                for word in extract_words_from_phrase(c):
                    w_norm = normalize_text(word)
                    if self._is_noise_term(w_norm) or w_norm in seen_words or w_norm in self.context.known_words:
                        continue
                    seen_words.add(w_norm)
                    words.append(w_norm)

            print(f"info: -> Sous-agent teste {len(tested_titles)} titres Wikipedia probables...")
            _, solution = await self.context.score_batch(words, tag="agent-wiki")

            return {
                "action": "tested_wiki_titles",
                "queries_used": new_queries[:5],
                "titles_found": tested_titles[:5],
                "solved": solution is not None,
                "solution": solution.solution if solution else None
            }

        return f"Erreur: Outil {name} inconnu."
