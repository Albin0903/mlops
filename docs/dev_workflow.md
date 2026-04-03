# Workflow de developpement (branches + validations)

Ce workflow reduit les echecs en CI en imposant des validations locales avant push.

## 1) Creer une branche de travail

Toujours partir de `develop` a jour:

```bash
git switch develop
git pull --ff-only origin develop
```

Puis creer une branche:

- correction: `bugfix/<sujet-court>`
- evolution: `feature/<sujet-court>`

```bash
git switch -c bugfix/pre-push-hook-stability
```

## 2) Commits atomiques

- Commits petits et explicites (`fix:`, `feat:`, `docs:`, `ci:`).
- Un commit = un objectif technique clair.

## 3) Validation locale obligatoire

Installer les hooks une fois:

```bash
make install
```

Avant push, executer dans cet ordre:

```bash
make ci-local
python scripts/dagger_ci.py
```

Notes:

- `pre-commit` couvre lint, format, secrets, manifests K8s et checks Terraform.
- Le hook Terraform est optimise en local: validation uniquement des dossiers Terraform modifies (mode `changed`).
- La CI distante force la validation Terraform complete (`TERRAFORM_VALIDATE_SCOPE=all`).
- Le gate pre-push execute aussi un check hard de frontiere API (`scripts/check_api_core_boundaries.py`) pour bloquer tout import `app/` vers `scripts/` ou `tests/`.
- `scripts/dagger_ci.py` reproduit un pipeline local proche de la CI distante.
- Les sorties debug/benchmark locales doivent aller dans `tmp/` pour eviter le bruit dans les changements Git.

## Legacy hors coeur API

Les scripts legacy ne font pas partie du coeur API-first et doivent etre appeles explicitement:

```bash
make legacy-pedantix
make legacy-tusmo
```

## 4) Integration vers develop

Quand la branche est verte localement:

```bash
git push -u origin bugfix/pre-push-hook-stability
```

Ensuite integrer vers `develop` (PR recommandee), attendre la CI GitHub en succes, puis synchroniser:

```bash
git switch develop
git pull --ff-only origin develop
```

## 5) Regle operationnelle

- Ne pas pousser de nouveaux changements tant que la CI du push precedent n'est pas terminee en succes.
- En cas d'echec CI: corriger sur branche de travail, revalider localement, puis repousser.
