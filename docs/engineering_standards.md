# Standards du projet

Quelques regles simples pour garder le code propre et coherent.

## Style et redaction

- Pas d'emojis dans le code, les commits, les logs ou la doc.
- Pas de majuscules decoratives en pleine phrase (sauf noms propres : Python, Docker, etc.).
- Ton direct et technique. On evite les tournures scolaires ou les phrases de remplissage.

## Securite

- Jamais de secrets ou de cles API dans Git (`.env`, `.tfstate` restent en local).
- Chaque commit passe par les hooks `pre-commit` avant d'etre pousse.
- Utiliser `pathlib` pour les chemins de fichiers (compatibilite Windows/Linux).

## Code et infra

- Python : le code suit les regles `ruff` et est couvert par `pytest`.
- Terraform : modules independants, backend distant pour l'etat.
- Les logs restent structures et lisibles (`info: processing started for {filename}`), sans decoration.
- Pas d'alignement d'operateurs `=` — on garde le code compact.
