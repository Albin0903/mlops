import argparse

from scripts.tusmo.agent import TusmoAgent
from scripts.tusmo.bot import TusmoBot
from scripts.tusmo.dictionary import TusmoDictionary
from scripts.tusmo.entropy import TusmoSolver


class ANSI:
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"


def render_colored_reply(word: str, pattern: str) -> None:
    res = ""
    for w, p in zip(word, pattern, strict=False):
        if p.isupper():
            res += f"{ANSI.RED}[{w.upper()}]{ANSI.RESET} "
        elif p.islower():
            res += f"{ANSI.YELLOW}({w.upper()}){ANSI.RESET} "
        else:
            res += f" {w.upper()}  "
    print("info: " + res.strip())


def interactive_solve(longueur: int, lettre_depart: str) -> None:
    db = TusmoDictionary()
    solver = TusmoSolver(longueur, lettre_depart, db)
    print(f"info: Démarrage Tusmo interactif. {len(solver.candidats)} mots possibles.")

    tour = 0
    while True:
        tour += 1
        print(f"\ninfo: --- Tour {tour} ---")

        mot_suggere = solver.obtenir_meilleur_mot()
        if not mot_suggere:
            print("info: Plus aucun mot ne correspond.")
            break

        print(f"info: Proposition de l'Agent : {ANSI.CYAN}{mot_suggere.upper()}{ANSI.RESET}")

        reponse = input("Entrez la réponse de Tusmo (A/a/_), ou 0 pour rejeter : ").strip()
        if reponse == "0":
            if mot_suggere in solver.vocabulaire_test:
                solver.vocabulaire_test.remove(mot_suggere)
            if mot_suggere in solver.candidats:
                solver.candidats.remove(mot_suggere)
            tour -= 1
            print("info: Mot rejeté. Recalcul...")
            continue

        if len(reponse) != longueur:
            print(f"info: Erreur : la réponse doit faire {longueur} caractères.")
            tour -= 1
            continue

        render_colored_reply(mot_suggere, reponse)

        if reponse.isupper() and "_" not in reponse and " " not in reponse:
            print(f"{ANSI.GREEN}info: Victoire confirmée ! Le mot était : {mot_suggere.upper()}{ANSI.RESET}")
            break

        solver.mettre_a_jour_contraintes(mot_suggere, reponse)
        restants = solver.filtrer_candidats()
        print(f"info: Mots restants : {restants}")

        if restants == 1:
            sol = solver.candidats[0]
            print(f"\n{ANSI.GREEN}info: SOLUTION TROUVÉE : {sol.upper()}{ANSI.RESET}")
            break


def bot_solve(room_url: str) -> None:
    bot = TusmoBot()
    try:
        lettre_depart, longueur = bot.connect(room_url)
        print(f"info: Bot connecté. Lettre: {lettre_depart}, Longueur: {longueur}")

        db = TusmoDictionary()
        solver = TusmoSolver(longueur, lettre_depart, db)

        for essai in range(6):
            mot_suggere = solver.obtenir_meilleur_mot()
            if not mot_suggere:
                print("info: Impossible de trouver un mot.")
                break

            print(f"info: Essai {essai + 1}: Joue {mot_suggere.upper()}")
            print("info: Attention: Tapez le mot manuellement sur le navigateur, le bot lira la réponse.")
            input("info: Appuyez sur Entrée quand le mot a été validé sur la page...")

            reponse = bot.lire_reponse(longueur, essai)
            render_colored_reply(mot_suggere, reponse)

            if reponse.isupper() and "_" not in reponse:
                print(f"{ANSI.GREEN}info: GAGNÉ !{ANSI.RESET}")
                break

            solver.mettre_a_jour_contraintes(mot_suggere, reponse)
            solver.filtrer_candidats()

    finally:
        bot.close()


async def agent_solve(longueur: int, lettre_depart: str, provider: str, thinking: str, max_turns: int = 8) -> None:
    db = TusmoDictionary()
    solver = TusmoSolver(longueur, lettre_depart, db)
    agent = TusmoAgent(solver, provider=provider, thinking=thinking)
    agent.max_turns = max_turns

    print(f"info: Démarrage Tusmo Agent ({provider}).")
    await agent.run()


def main() -> None:
    parser = argparse.ArgumentParser("Solveur Tusmo")
    parser.add_argument("--mode", choices=["interactive", "bot", "agent"], default="interactive")
    parser.add_argument("--longueur", type=int, default=6)
    parser.add_argument("--lettre", type=str, default="a")
    parser.add_argument("--room", type=str, default="")
    parser.add_argument("--provider", type=str, default="groq")
    parser.add_argument("--thinking", choices=["off", "low", "medium", "high"], default="off")
    parser.add_argument("--max-turns", type=int, default=8)
    args = parser.parse_args()

    if args.mode == "interactive":
        interactive_solve(args.longueur, args.lettre)
    elif args.mode == "bot":
        bot_solve(args.room)
    elif args.mode == "agent":
        import asyncio
        asyncio.run(agent_solve(args.longueur, args.lettre, args.provider, args.thinking, args.max_turns))


if __name__ == "__main__":
    main()
