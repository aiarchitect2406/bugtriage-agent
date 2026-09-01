# Cloud Storage Bucket for Agent Artifacts, Sessions & Checkpoints
resource "google_storage_bucket" "agent_artifacts" {
  project                     = var.project_id
  name                        = "${var.project_id}-${var.project_name}-artifacts"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_storage_bucket_iam_member" "agent_storage_admin" {
  bucket = google_storage_bucket.agent_artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.bug_triage_agent_sa.email}"
}
