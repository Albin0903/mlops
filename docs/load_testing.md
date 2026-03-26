# Importance des tests de charge en MLOps

Ce document explique pourquoi les tests de charge (comme ceux effectues avec Locust dans ce projet) sont essentiels pour une infrastructure d'IA.

## 1. Identification des goulots d'étranglement

Dans une application s'appuyant sur des LLM, la latence est souvent dominee par l'appel API externe (Groq, Gemini) ou local (Ollama).
- **Benchmarking** : Comparer la latence entre un modele local (Ollama) et un modele Cloud.
- **Saturation API** : Determiner a partir de combien d'utilisateurs simultanes l'API FastAPI commence a rejeter des requetes (Backpressure).

## 2. Configuration du scaling Kubernetes (HPA)

En MLOps, on utilise le **Horizontal Pod Autoscaler (HPA)** pour augmenter le nombre de pods en cas de charge.
- Les tests permettent de definir les seuils de CPU/Memoire ou de latence personnalisee pour declencher le scaling.
- Ils verifient que le cluster Kubernetes peut absorber un pic de trafic sans interruption de service.

## 3. Optimisation des couts

En connaissant exactement la capacite de traitement d'un pod (ex: 5 requetes stream simultanees), on peut eviter de sur-provisionner les ressources Cloud (instances EC2/EKS) et ainsi reduire la facture.

## 4. Resilience et Timeouts

Les tests de charge valident que les mecanismes de **Retry** (Tenacity) et les **Timeouts** HTTP sont correctement identifies pour ne pas bloquer les ressources système indefinement en cas de ralentissement des fournisseurs de modèles.

---
*Note : Utilise `make benchmark` pour lancer une simulation locale.*
