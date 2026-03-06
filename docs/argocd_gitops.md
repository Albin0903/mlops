# ArgoCD et GitOps

Comment le deploiement continu fonctionne sur ce projet.

## Principe

La CI (GitHub Actions) construit l'image Docker et la pousse sur GHCR.
ArgoCD surveille le dossier `gitops/overlays/minikube` sur la branche `main` et synchronise automatiquement le cluster avec ce qui est declare dans Git. Si quelqu'un modifie le cluster a la main, ArgoCD corrige tout seul (self-heal).

## Organisation des fichiers

```text
gitops/
  base/                   # deployment, service, ingress de l'API
  overlays/minikube/      # configuration specifique a minikube
argocd/
  applications/mlops.yaml # declaration de l'app ArgoCD
```

## Comment ca se passe concretement

1. Un push sur `main` declenche la CI.
2. La CI publie l'image sur `ghcr.io/albin0903/mlops:latest`.
3. ArgoCD detecte les changements dans le repo Git.
4. Il applique (ou corrige) les ressources Kubernetes automatiquement.

## Ce qu'il faut avoir en place

- ArgoCD installe dans le namespace `argocd` du cluster.
- L'addon Ingress active sur minikube (`minikube addons enable ingress`).
- L'image `ghcr.io/albin0903/mlops:latest` accessible depuis le cluster.
- L'Ingress utilise le hostname `mlops-gitops.local` pour ne pas entrer en conflit avec le manifest de demo `k8s/hello-world.yaml`.

## Commandes utiles

Valider les manifests localement avant de pousser :

```powershell
kubectl apply --dry-run=client -k gitops/overlays/minikube
```

Creer l'application ArgoCD (une seule fois, apres le premier push sur `main`) :

```powershell
kubectl apply -f argocd/applications/mlops.yaml
```

Verifier que tout roule :

```powershell
kubectl get applications -n argocd
kubectl describe application mlops -n argocd
```

Acceder a l'interface web ArgoCD :

```powershell
kubectl port-forward svc/argocd-server -n argocd 8080:443
# ouvrir https://localhost:8080
# login : admin / mot de passe recupere avec :
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

## Gestion des secrets

Les cles API (Groq, Gemini, Langfuse) ne doivent jamais etre commitees.
Le deployment reference un secret Kubernetes optionnel `mlops-api-secrets`.

Pour le creer en local :

```powershell
kubectl create secret generic mlops-api-secrets -n mlops `
  --from-literal=groq_api_key=... `
  --from-literal=gemini_api_key=... `
  --from-literal=langfuse_public_key=... `
  --from-literal=langfuse_secret_key=...
```