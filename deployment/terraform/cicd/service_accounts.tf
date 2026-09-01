# GitHub Actions CI/CD Runner Service Account
resource "google_service_account" "cicd_runner_sa" {
  project      = var.cicd_project
  account_id   = "bugtriage-runner-sa"
  display_name = "GitHub Actions CI/CD Ingress & Deployment Runner"
}

resource "google_project_iam_member" "runner_aiplatform_user" {
  project = var.cicd_project
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cicd_runner_sa.email}"
}

resource "google_project_iam_member" "runner_artifact_admin" {
  project = var.cicd_project
  role    = "roles/artifactregistry.admin"
  member  = "serviceAccount:${google_service_account.cicd_runner_sa.email}"
}
