# Demonstrations et validation

Les solveurs de jeux valident l'efficacite de l'API sur des workflows iteratifs.

## Solveur Pedantix (`scripts/solve_pedantix.py`)

Client de validation des capacites de raisonnement.
- Fonctionnement : Devine un article Wikipedia via l'API locale.
- Validation : Utilise les metriques de proximite pour converger.

## Module Tusmo (`tusmo/solve.py`)

Agent automatise pour resoudre le jeu de mots Tusmo.
- Entropie : Reduit l'incertitude pour choisir le mot suivant.
- Intelligence : Utilise l'API LLM pour selectionner les mots via Wikipedia.

## Utile pour le test systeme

- Test de charge : Simule des successions rapides de requetes.
- Validation end-to-end : Verifie la coherence des reponses et la connectivite.
- Showcase : Support pour des agents autonomes.
