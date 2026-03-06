# Compatibilite multi-OS

Le projet tourne sur Windows et Linux. Quelques conventions pour eviter les problemes.

## Python

- Toujours utiliser un `venv` pour isoler les dependances.
- Utiliser `pathlib` pour manipuler les chemins (evite les bugs `/` vs `\`).

## Scripts

- Les scripts d'automatisation sont en Python (`scripts/manage_infra.py`) pour tourner partout sans adaptation.
- Pour les commandes simples, on documente les equivalents PowerShell et Bash.

## Docker

- Les fichiers a l'interieur des conteneurs utilisent des fins de ligne `LF` (Linux).
- Le `.gitattributes` force le format `LF` sur les scripts shell pour eviter les surprises au build.
