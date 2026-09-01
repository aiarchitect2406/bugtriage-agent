terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

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

variable "github_repository" {
  type        = string
  default     = "aiarchitect2406/example-payment-svc"
  description = "Target GitHub repository authorized for Workload Identity Federation"
}

# 1. Vertex AI Agent Runtime Managed Identity Service Account
resource "google_service_account" "bug_triage_agent_sa" {
  account_id   = "bug-triage-agent-sa"
  display_name = "GEAP Managed Bug Triage Agent Service Account"
}

# 2. IAM Role Bindings for Agent Service Account
resource "google_project_iam_member" "agent_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.bug_triage_agent_sa.email}"
}

resource "google_project_iam_member" "agent_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.bug_triage_agent_sa.email}"
}

resource "google_project_iam_member" "agent_dlp_user" {
  project = var.project_id
  role    = "roles/dlp.user"
  member  = "serviceAccount:${google_service_account.bug_triage_agent_sa.email}"
}

# 3. GitHub Actions Ingress Runner Service Account
resource "google_service_account" "bugtriage_runner_sa" {
  account_id   = "bugtriage-runner-sa"
  display_name = "GitHub Actions Bug Triage Ingress Runner"
}

resource "google_project_iam_member" "runner_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.bugtriage_runner_sa.email}"
}

# 4. Workload Identity Federation (WIF) Pool & Provider for GitHub Actions
resource "google_iam_workload_identity_pool" "github_actions_pool" {
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions WIF Pool"
  description               = "Identity pool for GitHub Actions keyless authentication"
}

resource "google_iam_workload_identity_pool_provider" "github_actions_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_actions_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions-provider"
  display_name                       = "GitHub Actions OIDC Provider"
  description                        = "OIDC identity provider for GitHub Actions"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# 5. Authorize GitHub Target Repository to Impersonate the Ingress Runner Service Account
resource "google_service_account_iam_member" "github_actions_wif_binding" {
  service_account_id = google_service_account.bugtriage_runner_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_actions_pool.name}/attribute.repository/${var.github_repository}"
}

# 6. Secret Manager Secret for GitHub Token
resource "google_secret_manager_secret" "github_token" {
  secret_id = "github-api-token"
  replication {
    auto {}
  }
}

