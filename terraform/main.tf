# 1. GEAP Agent Identity Managed Service Account
resource "google_service_account" "bug_triage_agent_sa" {
  project      = var.project_id
  account_id   = "bug-triage-agent-sa"
  display_name = "GEAP Managed Bug Triage Agent Service Account"
}

# 2. Least-Privilege IAM Role Bindings
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
  project      = var.project_id
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
  project                   = var.project_id
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions WIF Pool"
  description               = "Identity pool for GitHub Actions keyless authentication"
}

resource "google_iam_workload_identity_pool_provider" "github_actions_provider" {
  project                            = var.project_id
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

# 6. Secret Manager Secrets for Runtime Injection
resource "google_secret_manager_secret" "github_token" {
  project   = var.project_id
  secret_id = "github-api-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "slack_hmac_key" {
  project   = var.project_id
  secret_id = "slack-hmac-signing-key"
  replication {
    auto {}
  }
}

# 7. Cloud Storage Bucket for Agent Artifacts & Sessions
resource "google_storage_bucket" "agent_artifacts" {
  project                     = var.project_id
  name                        = "${var.project_id}-${var.project_name}-artifacts"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
}

resource "google_storage_bucket_iam_member" "agent_storage_admin" {
  bucket = google_storage_bucket.agent_artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.bug_triage_agent_sa.email}"
}

# 8. Cloud Run Service for ADK 2.0 Agent Deployment
resource "google_cloud_run_v2_service" "bug_triage_agent" {
  project  = var.project_id
  name     = "${var.project_name}-service"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.bug_triage_agent_sa.email

    containers {
      image = var.container_image

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
    google_project_iam_member.agent_dlp_user,
  ]
}
