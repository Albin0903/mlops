# Environnement de Développement Multi-OS

## Python
- Utiliser des environnements virtuels (`venv`).
- Utiliser `pathlib` dans le code Python au lieu de manipulations de chaînes de caractères pour les chemins de fichiers (compatibilité `/` vs `\`).

## Scripts Shell vs PowerShell
- Les scripts d'automatisation majeurs doivent être écrits en **Python** (ex: `scripts/manage_infra.py`) pour garantir une exécution identique sur Windows et Linux.
- Pour les commandes simples, privilégier des outils universels comme `make` (via Makefile) ou documenter les équivalents PowerShell/Bash.

## Docker
- Utiliser des fins de ligne `LF` (Linux) pour les fichiers à l'intérieur des conteneurs.
- Configuration `.gitattributes` recommandée pour forcer le format `LF` sur les scripts shell.
