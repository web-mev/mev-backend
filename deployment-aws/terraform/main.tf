terraform {
  required_version = ">= 1.2.6, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.24.0"
    }
    cloudinit = {
      source  = "hashicorp/cloudinit"
      version = "~> 2.2.0"
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.2.2"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.3.2"
    }
  }

  backend "s3" {
    bucket               = "webmev-tf"
    key                  = "terraform.state"
    region               = "us-east-2"
    workspace_key_prefix = "workspace"
  }
}

locals {
  stack         = lower(terraform.workspace)
  commit_id     = var.git_commit == "" ? data.external.git.result["branch"] : var.git_commit
  globus_bucket = "${local.stack}-webmev-globus"
  common_tags   = {
    Name      = "${local.stack}-mev"
    Project   = "WebMEV"
    Terraform = "True"
  }
}

provider "aws" {
  region = "us-east-2"
  default_tags {
    tags = local.common_tags
  }
}

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

data "external" "git" {
  program = ["/bin/bash", "-c", "echo '{\"branch\": \"'$(git branch --show-current)'\"}'"]
}

module "globus" {
  count                  = var.globus == null ? 0 : 1
  source                 = "./modules/globus"
  data_bucket            = local.globus_bucket
  name_prefix            = local.common_tags.Name
  secrets_bucket         = "webmev-tf"
  secrets_prefix         = "secrets/${local.stack}"
  subnet_id              = aws_subnet.public.id
  vpc_id                 = aws_vpc.main.id
}
