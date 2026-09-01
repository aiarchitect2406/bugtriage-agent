variable "cicd_project" {
  type        = string
  default     = "nithin-usbaws-aiml-solns-demos"
  description = "Google Cloud Project ID hosting CI/CD infrastructure"
}

variable "dev_project" {
  type        = string
  default     = "nithin-usbaws-aiml-solns-demos"
  description = "Google Cloud Project ID for development environment"
}

variable "prod_project" {
  type        = string
  default     = "nithin-usbaws-aiml-solns-demos"
  description = "Google Cloud Project ID for production environment"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "Target deployment region"
}

variable "project_name" {
  type        = string
  default     = "adk-bugtriage"
  description = "Project and agent resource name"
}

variable "github_repository" {
  type        = string
  default     = "aiarchitect2406/bugtriage-agent"
  description = "Target GitHub repository for CI/CD actions"
}
