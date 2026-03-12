"""
script de test asynchrone pour valider le streaming de l'api.
utilise httpx au lieu de invoke-restmethod (powershell) qui attend le buffer complet.

usage : python scripts/test_streaming.py
resultat attendu : le texte s'affiche mot par mot (chunks) dans le terminal.
"""

import asyncio
import time

import httpx

API_URL = "http://localhost:8000/analyze/"

# cas de test : generation de documentation
TEST_DOC = {
    "content": "def fibonacci(n: int) -> int:\n    if n <= 1:\n        return n\n    return fibonacci(n - 1) + fibonacci(n - 2)",
    "language": "python",
    "mode": "doc",
}

# cas de test : question sur un document
TEST_QUESTION = {
    "content": "le projet utilise terraform pour l'iac, minikube pour kubernetes local, et groq pour les appels llm.",
    "language": "text",
    "mode": "question",
    "question": "quels outils sont utilises pour l'infrastructure ?",
}


async def test_streaming(payload: dict, label: str):
    """envoie une requete et affiche les chunks au fur et a mesure"""
    print(f"\n{'=' * 60}")
    print(f"test : {label}")
    print(f"{'=' * 60}\n")

    chunk_count = 0
    start = time.perf_counter()

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", API_URL, json=payload) as response:
            if response.status_code != 200:
                print(f"erreur http {response.status_code}")
                return

            async for chunk in response.aiter_text():
                chunk_count += 1
                print(chunk, end="", flush=True)

    elapsed = time.perf_counter() - start
    print("\n\n--- resultats ---")
    print(f"chunks recus     : {chunk_count}")
    print(f"duree totale     : {elapsed:.2f}s")
    print(f"streaming valide : {'oui' if chunk_count > 1 else 'non (reponse en bloc)'}")


async def main():
    """lance les deux scenarios de test"""
    await test_streaming(TEST_DOC, "generation de documentation (mode doc)")
    await test_streaming(TEST_QUESTION, "reponse a une question (mode question)")


if __name__ == "__main__":
    asyncio.run(main())
