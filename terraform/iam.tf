# Get project number for default service account
data "google_project" "project" {}

# Make the Cloud Run service publicly accessible
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.deep_research_app.location
  name     = google_cloud_run_v2_service.deep_research_app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Grant Cloud Run service account access to Secret Manager secrets
resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each  = local.secret_vars
  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}
