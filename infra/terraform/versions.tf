terraform {
  required_version = ">= 1.17.2"

  backend "s3" {
    bucket       = "kalavigyan-tfstate-626159998512"
    key          = "kalavigyan/infra.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.73"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.9"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project = var.project
      Repo    = var.github_repo
    }
  }
}
