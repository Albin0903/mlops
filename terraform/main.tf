# Appel du module VPC (Réseau)
module "vpc" {
  source = "./modules/vpc"
}

# Appel du module Cluster (Kubernetes) -> commenté = pas de frais
# module "cluster" {
#   source = "./modules/cluster"
# }