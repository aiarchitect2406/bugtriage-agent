# Vertex AI Agent Runtime Managed Identity Service Account
resource "google_service_account" "bug_triage_agent_sa" {
  project      = var.project_id
  account_id   = "bug-triage-agent-sa"
  display_name = "GEAP Managed Bug Triage Agent Service Account"
  depends_on   = [google_project_service.services]
}

# Least-Privilege IAM Role Bindings for Agent Service Account
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

# GitHub Actions Ingress Runner Service Account
resource "google_service_account" "bugtriage_runner_sa" {
  project      = var.project_id
  account_id   = "bugtriage-runner-sa"
  display_name = "GitHub Actions Bug Triage Ingress Runner"
  depends_on   = [google_project_service.services]
}

resource "google_project_iam_member" "runner_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.bugtriage_runner_sa.email}"
}
