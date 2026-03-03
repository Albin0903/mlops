# 1. le cluster eks
resource "aws_eks_cluster" "main" {
  name = "mlops-cluster"
  role_arn = var.eks_role_arn
  vpc_config {
    subnet_ids = var.public_subnet_ids
  }
}

# 2. le node group (instances t3.medium)
resource "aws_eks_node_group" "main" {
  cluster_name = aws_eks_cluster.main.name
  node_group_name = "mlops-node-group"
  node_role_arn = var.eks_node_role_arn
  subnet_ids = var.public_subnet_ids
  scaling_config {
    desired_size = 1
    max_size = 2
    min_size = 1
  }
  instance_types = ["t3.medium"]
  depends_on = [aws_eks_cluster.main]
}
