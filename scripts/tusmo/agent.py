import json
from typing import Any

from app.services.llm_service import llm_service
from scripts.tusmo.entropy import TusmoSolver

# Définition des schémas d'outils pour Tusmo
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_suggestions",
            "description": "Obtenir les 10 meilleurs mots suggérés par l'entropie statistique.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Nombre de mots à retourner (défaut 10)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_guess",
            "description": "Soumettre un mot et obtenir le motif de réponse (pattern).",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "Le mot à tester (doit avoir la bonne longueur)"}
                },
                "required": ["word"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_game_overview",
            "description": "Obtenir un résumé des contraintes actuelles (lettres fixées, absentes, etc.).",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

class TusmoAgent:
    def __init__(self, solver: TusmoSolver, provider: str = "groq", thinking: str = "off"):
        self.solver = solver
        self.provider = provider
        self.thinking = thinking
        self.max_turns = 8
        self.history = []
        self._init_system_message()

    def _init_system_message(self):
        msg = (
            "Tu es un agent expert pour résoudre le jeu Tusmo (variante de Wordle/Motus).\n"
            f"Règles du jeu :\n"
            f"- Longueur du mot : {self.solver.longueur}\n"
            f"- Première lettre fixée : {self.solver.lettre_depart.upper()}\n"
            "- Motif de réponse (Pattern) :\n"
            "  * MAJUSCULE (ex: 'A') : Lettre BIEN placée (correcte).\n"
            "  * minuscule (ex: 'a') : Lettre MAL placée (présente ailleurs).\n"
            "  * Underscore (ex: '_') : Lettre ABSENTE du mot.\n\n"
            "Stratégie :\n"
            "1. Utilise `get_suggestions` pour voir les mots statistiquement optimaux.\n"
            "2. Analyse les patterns reçus pour éliminer des possibilités.\n"
            "3. Propose des mots qui maximisent l'information si tu as plusieurs candidats.\n\n"
            "Consigne : Sois concis. Réfléchis (Thought) puis appelle un outil."
        )
        self.history = [{"role": "system", "content": msg}]

    async def run(self):
        print(f"info: Démarrage de l'agent Tusmo ({self.provider})...")
        self.history.append({"role": "user", "content": "Commence par analyser les suggestions initiales."})

        for turn in range(1, self.max_turns + 1):
            print(f"\ninfo: --- Tour Agent {turn}/{self.max_turns} ---")

            response_data = await llm_service.execute_agent_call(
                messages=self.history,
                tools=TOOLS,
                provider=self.provider,
                thinking=self.thinking
            )

            if response_data["type"] == "text":
                content = response_data["content"] or "..."
                print(f"Agent Thought: {content}")
                self.history.append({"role": "assistant", "content": content})
                continue

            elif response_data["type"] == "tool_calls":
                assistant_msg = {
                    "role": "assistant",
                    "content": response_data.get("content") or "Analyse en cours...",
                    "tool_calls": []
                }

                tool_requests = []
                for call in response_data["calls"]:
                    name = call["name"]
                    args = call["args"] or {}
                    call_id = f"call_{turn}_{name}"

                    assistant_msg["tool_calls"].append({
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)}
                    })
                    tool_requests.append((name, args, call_id))

                self.history.append(assistant_msg)

                for name, args, call_id in tool_requests:
                    print(f"info: Appel outil: {name}({args})")
                    observation = await self.execute_tool(name, args)

                    self.history.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": json.dumps(observation, ensure_ascii=False)
                    })

                    if name == "submit_guess" and observation.get("solved"):
                        print(f"info: Agent Victoire ! Le mot était : {args.get('word').upper()}")
                        return

    async def execute_tool(self, name: str, args: dict) -> Any:
        if name == "get_suggestions":
            # Pour l'instant on retourne juste les top candidats
            self.solver.filtrer_candidats()
            top = self.solver.candidats[:15]
            return {"suggestions": top, "count": len(self.solver.candidats)}

        elif name == "submit_guess":
            word = args.get("word", "").lower()
            if len(word) != self.solver.longueur:
                return {"error": f"Longueur invalide (attendu {self.solver.longueur})"}

            print(f"PROMPT : Entrez le pattern pour '{word.upper()}' (ex: A_b_C) : ", end="")
            pattern = input().strip()

            self.solver.mettre_a_jour_contraintes(word, pattern)
            self.solver.filtrer_candidats()

            solved = pattern.isupper() and "_" not in pattern
            return {
                "pattern": pattern,
                "solved": solved,
                "remaining_candidats": len(self.solver.candidats)
            }

        elif name == "get_game_overview":
            bien_placees = "".join([l if l else "." for l in self.solver.lettres_bien_placees])
            return {
                "longueur": self.solver.longueur,
                "bien_placees": bien_placees,
                "absentes": sorted(list(self.solver.lettres_absentes)),
                "candidats_count": len(self.solver.candidats)
            }

        return {"error": "Outil inconnu"}
