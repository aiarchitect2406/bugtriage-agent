variable "project_id" {
  type        = string
  default     = "nithin-usbaws-aiml-solns-demos"
  description = "Google Cloud Project ID"
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
  default     = "aiarchitect2406/example-payment-svc"
  description = "Target GitHub repository authorized for Workload Identity Federation"
}

variable "container_image" {
  type        = string
  default     = "gcr.io/nithin-usbaws-aiml-solns-demos/bug-triage-agent:latest"
  description = "Container image URI for the agent service"
}
