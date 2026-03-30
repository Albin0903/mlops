import json
from typing import Any

from app.services.llm_service import llm_service
from scripts.pedantix.intelligence import extract_best_score, summarize_results
from scripts.pedantix.models import extract_words_from_phrase

# Definition des schemas d'outils pour les LLMs (format OpenAI/Groq/Gemini)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "guess_words",
            "description": "Soumet une liste de mots au puzzle Pédantix pour obtenir leur score exact ou de proximité.",
            "parameters": {
                "type": "object",
                "properties": {
                    "words": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Liste de mots à tester (ex: ['science', 'histoire', 'france'])",
                    }
                },
                "required": ["words"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_wikipedia",
            "description": "Recherche des titres de pages Wikipedia correspondant à une requête thématique.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Terme de recherche (ex: 'physicien français du 19ème siècle')"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_wikipedia_page",
            "description": "Analyse une page Wikipedia spécifique pour voir si elle correspond à la structure du texte masqué.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Titre exact de la page Wikipedia à analyser"}
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_game_state",
            "description": "Récupère l'état actuel du jeu : mots trouvés, meilleurs scores de proximité et aperçu du texte.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
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
        thinking: str = "off",
    ):
        self.puzzle_number = puzzle_number
        self.title_lengths = title_lengths
        self.slot_lengths = slot_lengths
        self.masked_preview = masked_preview
        self.context = cli_context
        self.provider = provider
        self.thinking = thinking

        self.system_message = (
            "Tu es un agent expert chargé de résoudre le puzzle Pédantix. "
            "But : Deviner le titre d'une page Wikipedia masquée.\n\n"
            "Outils disponibles :\n"
            "- `get_game_state` : État actuel du jeu.\n"
            "- `guess_words` : Tester une liste de mots.\n"
            "- `search_wikipedia` : Trouver des candidats par thématique.\n"
            "- `analyze_wikipedia_page` : Vérifier la structure d'un titre.\n\n"
            "Règles :\n"
            "1. Ne répète jamais les mêmes mots inutilement.\n"
            "2. Sois concis dans tes réflexions (Thought).\n"
            "3. Utilise `get_game_state` en premier.\n"
            "4. Si tu es bloqué, cherche des thèmes larges."
        )
        self.history = [{"role": "system", "content": self.system_message}]
        self.max_turns = 15

    async def run(self):
        print(f"info: Démarrage de l'agent ReAct ({self.provider})...")

        # Le premier message utilisateur suffit, pas besoin de ré-appuyer à chaque tour.
        self.history.append({"role": "user", "content": "Analyse l'état initial et commence la résolution."})

        for turn in range(1, self.max_turns + 1):
            print(f"\ninfo: --- Tour Agent {turn}/{self.max_turns} ---")

            # Appel au LLM
            response_data = await llm_service.execute_agent_call(
                messages=self.history,
                tools=TOOLS,
                provider=self.provider,
                thinking=self.thinking,
            )

            if response_data["type"] == "text":
                content = response_data["content"] or "..."
                print(f"Agent Thought: {content}")
                self.history.append({"role": "assistant", "content": content})
                continue

            elif response_data["type"] == "tool_calls":
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
                    print(f"info: Appel outil: {name}({args})")
                    observation = await self.execute_tool(name, args)

                    self.history.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": json.dumps(observation, ensure_ascii=False)
                    })

                    if name == "guess_words":
                        if isinstance(observation, list) and any(r.get("solved") for r in observation):
                            print("info: Solution trouvée par l'agent !")
                            return

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
            from scripts.pedantix.client_wikipedia import search_wikipedia_titles
            titles = await search_wikipedia_titles(self.context.client, [query], per_query=5)
            # Dépolluer les titres pour le LLM
            return {"candidates": titles[:10]}

        elif name == "analyze_wikipedia_page":
            title = args.get("title", "")
            from scripts.pedantix.client_wikipedia import resolve_wikipedia_title
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

        return f"Erreur: Outil {name} inconnu."
