variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "key_pair_name" {
  description = "Name of the AWS key pair for SSH access"
  type        = string
}

variable "project_name" {
  description = "Name tag applied to all resources"
  type        = string
  default     = "it-asset-compliance"
}

variable "github_repo" {
  description = "HTTPS URL of the GitHub repository to clone on the EC2 instance"
  type        = string
}

variable "db_user" {
  description = "PostgreSQL admin username written into the backend .env on first boot"
  type        = string
  default     = "admin"
}

variable "db_password" {
  description = "PostgreSQL admin password written into the backend .env on first boot. Supply via TF_VAR_db_password env var or terraform.tfvars (never commit the value)."
  type        = string
  sensitive   = true
}

variable "allowed_ssh_cidr" {
  description = "CIDR block permitted to reach port 22. Restrict to your own IP (e.g. 203.0.113.5/32) for production; 0.0.0.0/0 is acceptable only for demos."
  type        = string
  default     = "0.0.0.0/0"
}
