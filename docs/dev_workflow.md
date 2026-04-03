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
make prepush
python scripts/dagger_ci.py
```

Notes:

- `pre-commit` couvre lint, format, secrets, manifests K8s et checks Terraform.
- `scripts/dagger_ci.py` reproduit un pipeline local proche de la CI distante.

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
