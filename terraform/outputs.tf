output "agent_service_account_email" {
  description = "GEAP Agent Identity Service Account"
  value       = google_service_account.bug_triage_agent_sa.email
}

output "runner_service_account_email" {
  description = "GitHub Actions Ingress Runner Service Account"
  value       = google_service_account.bugtriage_runner_sa.email
}

output "wif_provider_name" {
  description = "Workload Identity Federation Provider Name"
  value       = google_iam_workload_identity_pool_provider.github_actions_provider.name
}

output "cloud_run_service_uri" {
  description = "Cloud Run Service URI"
  value       = google_cloud_run_v2_service.bug_triage_agent.uri
}

output "artifacts_bucket_name" {
  description = "GCS Artifacts Bucket"
  value       = google_storage_bucket.agent_artifacts.name
}
