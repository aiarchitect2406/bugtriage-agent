output "project_id" {
  description = "Google Cloud Project ID"
  value       = var.project_id
}

output "region" {
  description = "Target deployment region"
  value       = var.region
}

output "agent_service_account_email" {
  description = "Email of the GEAP Agent Identity Service Account"
  value       = google_service_account.bug_triage_agent_sa.email
}

output "runner_service_account_email" {
  description = "Email of the GitHub Actions Ingress Runner Service Account"
  value       = google_service_account.bugtriage_runner_sa.email
}

output "wif_provider_name" {
  description = "Workload Identity Federation Provider Name"
  value       = google_iam_workload_identity_pool_provider.github_actions_provider.name
}

output "cloud_run_service_uri" {
  description = "URI of the deployed Cloud Run agent service"
  value       = google_cloud_run_v2_service.bug_triage_agent.uri
}

output "artifacts_bucket_name" {
  description = "Name of the GCS bucket for agent artifacts and session memory"
  value       = google_storage_bucket.agent_artifacts.name
}

output "github_token_secret_id" {
  description = "Secret Manager secret ID for GitHub API token"
  value       = google_secret_manager_secret.github_token.secret_id
}

output "slack_hmac_key_secret_id" {
  description = "Secret Manager secret ID for Slack HMAC signing key"
  value       = google_secret_manager_secret.slack_hmac_key.secret_id
}
