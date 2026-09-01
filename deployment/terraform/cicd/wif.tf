# Workload Identity Federation (WIF) Pool & Provider for GitHub Actions Keyless Auth
resource "google_iam_workload_identity_pool" "github_actions_pool" {
  project                   = var.cicd_project
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions WIF Pool"
  description               = "Identity pool for GitHub Actions keyless authentication"
}

resource "google_iam_workload_identity_pool_provider" "github_actions_provider" {
  project                            = var.cicd_project
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

# Authorize GitHub Repository to Impersonate the CI/CD Runner Service Account
resource "google_service_account_iam_member" "github_actions_wif_binding" {
  service_account_id = google_service_account.cicd_runner_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_actions_pool.name}/attribute.repository/${var.github_repository}"
}
