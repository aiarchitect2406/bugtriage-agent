# Core Google Cloud APIs enabled for Autonomous Bug Triage Agent
locals {
  services = [
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com",
    "dlp.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}

resource "google_project_service" "services" {
  for_each                   = toset(local.services)
  project                    = var.project_id
  service                    = each.key
  disable_on_destroy         = false
  disable_dependent_services = false
}

# Secret Manager Secrets for runtime credential injection
resource "google_secret_manager_secret" "github_token" {
  project   = var.project_id
  secret_id = "github-api-token"
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret" "slack_hmac_key" {
  project   = var.project_id
  secret_id = "slack-hmac-signing-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}
