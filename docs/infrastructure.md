# Infrastructure et plateforme MLOps

L'infrastructure sert de plateforme de validation MLOps.

## Role de Minikube

Minikube est utilise comme proxy de production local.
- Pourquoi : Tester un pipeline GitOps ou un monitoring sur un contexte Kubernetes reel.
- Fonctionnalites : Isolation via Namespaces, Ingress Controllers NGINX, validation des Healthchecks.

## Modules Terraform

Le dossier `/terraform` contient des modules pour AWS EKS :
- `vpc` : Reseau prive.
- `iam` : Gestion des privileges.
- `cluster` : Provisionnement du cluster.
*Note : Le projet privilegie Minikube par defaut pour eviter les couts.*

## GitOps avec ArgoCD

Le deploiement est gere dans `/gitops`.
- Auto-Sync : Application automatique des modifications de manifests.
- Self-Healing : Le cluster revient a l'etat defini dans Git en cas de derive.

## Commandes Makefile

- `make build-local` : Build et load l'image dans Minikube.
- `make deploy` : Applique les manifests de base.
