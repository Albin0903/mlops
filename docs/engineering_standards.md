# Standards d'ingénierie et de style

Ce document définit les règles strictes de développement pour garantir la sobriété et le professionnalisme du projet.

## Règles de rédaction et de communication
- Interdiction d'utiliser des emojis dans le code, les commentaires, les messages de commit, les logs ou la documentation.
- Interdiction d'utiliser des majuscules en milieu de phrase ou pour mettre en avant des mots (sauf noms propres techniques comme Python, Docker, Terraform).
- Interdiction d'adopter un ton trop formel, scolaire ou verbeux typique des ia. L'écriture doit être directe, technique et factuelle.
- Interdiction d'ajouter des phrases de politesse génériques ("voici le code", "je suis ravi de vous aider"). Allez à l'essentiel technique.

## Sécurité et développement
- Interdiction de commiter des secrets, des clés api ou des fichiers de configuration locale (`.env`, `.tfstate`).
- Obligation de valider chaque commit avec les hooks `pre-commit` localement.
- Obligation d'utiliser `pathlib` pour la gestion des chemins afin d'assurer la compatibilité entre windows et linux.
- Les messages de log doivent être structurés (ex: `info: processing started for {filename}`) et sans décoration graphique.

## Infrastructure et code
- Le code python doit suivre les standards `ruff` et être testé via `pytest`.
- La configuration terraform doit être modulaire et utiliser un backend distant pour la gestion de l'état.- Interdiction d'ajouter des espaces pour aligner les opérateurs = (le code doit être compact).
