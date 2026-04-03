terraform {
  backend "s3" {
    bucket         = "mlops-albin"
    key            = "global/s3/terraform.tfstate"
    region         = "eu-north-1"
    encrypt        = true
  }
}
