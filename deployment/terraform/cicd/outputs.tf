output "wif_pool_name" {
  description = "Resource name of the Workload Identity Pool"
  value       = google_iam_workload_identity_pool.github_actions_pool.name
}

output "wif_provider_name" {
  description = "Resource name of the Workload Identity Provider"
  value       = google_iam_workload_identity_pool_provider.github_actions_provider.name
}

output "runner_service_account_email" {
  description = "Email of the GitHub Actions CI/CD Runner Service Account"
  value       = google_service_account.cicd_runner_sa.email
}
