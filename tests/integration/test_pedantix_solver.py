import os
import sys
import time

import anyio
import pytest
from dotenv import load_dotenv

pytest.importorskip("dagger")

import dagger
from dagger import dag
from loguru import logger

load_dotenv()


async def test_pedantix():
    """
    Script de test dédié pour valider le solveur Pedantix via Dagger.
    """
    python_version = "3.14"

    # Vérification des credentials
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        pytest.skip("GEMINI_API_KEY absent : test d'integration Pedantix ignore")

    logger.info("Démarrage du test du solveur Pedantix...")
    start_time = time.time()

    async with dagger.connection(dagger.Config(log_output=sys.stderr)):
        # Sélection des fichiers nécessaires uniquement
        src = dag.host().directory(".", include=["scripts/pedantix/", "requirements.txt", "app/"])

        # Construction du conteneur de test (plus léger)
        container = (
            dag.container()
            .from_(f"python:{python_version}-slim")
            .with_directory("/src", src)
            .with_workdir("/src")
            .with_exec(["pip", "install", "--upgrade", "pip"])
            # Installation minimale : seulement ce qui est nécessaire pour solve_pedantix.py
            .with_exec(
                ["pip", "install", "httpx", "loguru", "python-dotenv", "google-genai", "pydantic", "pydantic-settings"]
            )
            .with_secret_variable("GEMINI_API_KEY", dag.set_secret("gemini-key", gemini_key))
        )

        logger.info("Exécution du solveur (mode rapide avec 5 candidats)...")

        try:
            # Exécution du script avec un nombre limité de candidats pour le test
            result = await container.with_exec(["python", "scripts/pedantix/cli.py", "--max-candidates", "5"]).stdout()

            # Afficher les logs de sortie
            print(result)

            duration = time.time() - start_time
            logger.success(f"Test Pedantix réussi en {duration:.1f}s")

        except Exception as e:
            logger.error(f"Échec du test Pedantix : {e}")
            pytest.fail(f"Échec du test Pedantix : {e}")


if __name__ == "__main__":
    try:
        anyio.run(test_pedantix)
    except KeyboardInterrupt:
        logger.info("Test interrompu par l'utilisateur")
    except Exception as e:
        logger.critical(f"Erreur fatale : {e}")
        sys.exit(1)
