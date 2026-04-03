# Instructions Copilot - mlops API-only

## Portee produit

- Le coeur produit est API-first sous `app/`.
- Les modules `legacy/pedantix` et `legacy/tusmo` sont hors coeur API et doivent rester optionnels.
- Ne pas introduire de dependance runtime du coeur API vers `legacy/` ou `scripts/`.

## Regles d'architecture

- Respecter les couches: `api -> application -> domain`.
- Les implementations techniques sont dans `infrastructure` et `services`.
- La composition des dependances doit passer par `app/infrastructure/composition.py`.

## Qualite et validation

- Avant proposition de merge, executer au minimum:
  - `make test-pyramid`
  - `make ci-local`
- Le hook Terraform est optimise en local (scope `changed`) et force en complet en CI (scope `all`).

## Dependances

- Installer par defaut via `make install` (socle core).
- Installer les outils lourds seulement si necessaire via `make install-optional`.
