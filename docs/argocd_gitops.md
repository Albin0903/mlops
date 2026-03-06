# ArgoCD et GitOps

Ce document decrit l'integration GitOps mise en place pour le projet.

## Principe

La CI GitHub Actions construit et publie l'image Docker sur GHCR.
ArgoCD surveille ensuite le dossier `gitops/overlays/minikube` du depot Git et
reconcilie automatiquement l'etat du cluster Kubernetes avec l'etat declare dans
Git.

## Structure

- `gitops/base/` : deployment, service et ingress de l'API.
- `gitops/overlays/minikube/` : overlay cible pour l'environnement local minikube.
- `argocd/applications/mlops.yaml` : ressource ArgoCD `Application` qui pointe vers le repo GitHub.

## Flux de deploiement

1. Un commit sur `main` declenche la CI.
2. L'image est publiee sur GHCR avec le tag `latest`.
3. ArgoCD detecte l'etat desire depuis Git.
4. ArgoCD applique ou corrige les ressources sur le cluster.

## Pre-requis

- ArgoCD installe dans le namespace `argocd`.
- Le cluster minikube doit avoir l'addon Ingress active.
- L'image `ghcr.io/albin0903/mlops:latest` doit etre accessible.
- L'hostname d'Ingress utilise par cet overlay est `mlops-gitops.local` pour ne pas entrer en conflit avec le manifest de demo `k8s/hello-world.yaml`.

## Commandes utiles

Appliquer localement les manifests pour validation :

```powershell
kubectl apply --dry-run=client -k gitops/overlays/minikube
```

Creer l'application ArgoCD une fois les fichiers pousses sur `main` :

```powershell
kubectl apply -f argocd/applications/mlops.yaml
```

Verifier le statut :

```powershell
kubectl get applications -n argocd
kubectl describe application mlops -n argocd
```

## Secrets

Les cles LLM et Langfuse ne doivent pas etre committees dans Git.
Le deployment reference un secret Kubernetes optionnel nomme `mlops-api-secrets`.

Exemple de creation locale :

```powershell
kubectl create secret generic mlops-api-secrets -n mlops \
  --from-literal=groq_api_key=... \
  --from-literal=gemini_api_key=... \
  --from-literal=langfuse_public_key=... \
  --from-literal=langfuse_secret_key=...
```