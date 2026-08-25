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

# 1. GEAP Managed Agent Identity Service Account
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

# 3. Secret Manager Secret for GitHub Token
resource "google_secret_manager_secret" "github_token" {
  secret_id = "github-api-token"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

# 4. Secret Manager Secret for Slack HMAC Signing Key
resource "google_secret_manager_secret" "slack_hmac_key" {
  secret_id = "slack-hmac-signing-key"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

# 5. Cloud Run Service for ADK 2.0 Agent Runtime Deployment
resource "google_cloud_run_v2_service" "bug_triage_agent" {
  name     = "bug-triage-agent-service"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.bug_triage_agent_sa.email

    containers {
      image = "gcr.io/${var.project_id}/bug-triage-agent:latest"

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }

      env {
        name = "GITHUB_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.github_token.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "HITL_HMAC_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.slack_hmac_key.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
      }
    }
  }

  depends_on = [
    google_project_iam_member.agent_aiplatform_user,
    google_project_iam_member.agent_secret_accessor,
    google_project_iam_member.agent_dlp_user
  ]
}
