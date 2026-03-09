import time
import random
from locust import HttpUser, task, between, constant_pacing

# --- Notes Quotas (50% Load) ---
# Groq (Llama 8b/70b/GPT-OSS): Max 30 RPM -> Target 15 RPM (1 req every 4s)
# Gemini 3.1 Flash: Max 15 RPM -> Target 7.5 RPM (1 req every 8s)

class MLOpsProjectUser(HttpUser):
    # Entre 2 et 8 secondes pour simuler un mix de charge
    wait_time = between(2, 10)
    
    @task(5)
    def health_check(self):
        """Vérifie la santé de l'API (très rapide)."""
        self.client.get("/health/")

    @task(10)
    def analyze_doc_groq_instant(self):
        """Analyse de code avec Groq Instant (Llama 3.1 8b)."""
        payload = {
            "content": "def hello(): print('world')",
            "language": "python",
            "mode": "doc",
            "provider": "instant"
        }
        self.client.post("/analyze/", json=payload, name="/analyze [Groq Instant]")

    @task(3)
    def analyze_doc_gemini(self):
        """Analyse de code avec Gemini (plus lent, quota plus faible)."""
        payload = {
            "content": "class Database: pass",
            "language": "python",
            "mode": "doc",
            "provider": "gemini"
        }
        self.client.post("/analyze/", json=payload, name="/analyze [Gemini]")

    @task(2)
    def analyze_question_groq_medium(self):
        """Question sur document avec Groq Medium (Llama 120b/70b)."""
        payload = {
            "content": "Le projet utilise Terraform, K8s et Dagger.",
            "language": "text",
            "mode": "question",
            "question": "Quels outils d'IaC sont utilisés ?",
            "provider": "medium"
        }
        self.client.post("/analyze/", json=payload, name="/analyze [Groq Medium]")

    def on_start(self):
        """Exécuté quand un utilisateur commence."""
        pass
