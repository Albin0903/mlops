# appel du module vpc (réseau)
module "vpc" {
  source = "./modules/vpc"
}

# appel du module iam (rôles et politiques)
module "iam" {
  source = "./modules/iam"
}

# module cluster (eks) désactivé pour rester en free tier (~70$/mois sinon)
# remplacé par minikube en local pour le développement kubernetes
# module "cluster" {
#   source = "./modules/cluster"
#   eks_role_arn = module.iam.eks_role_arn
#   eks_node_role_arn = module.iam.eks_node_role_arn
#   public_subnet_ids = module.vpc.public_subnet_ids
# }
