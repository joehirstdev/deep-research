resource "google_cloud_run_v2_service" "deep_research_app" {
  name     = "deep-research-app"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.image_path

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "0.5"
          memory = "256Mi"
        }
        cpu_idle = true
      }

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }
}

# 2. Make the service public
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.deep_research_app.location
  name     = google_cloud_run_v2_service.deep_research_app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# 3. Outputs
output "service_url" {
  description = "The URL where your FastAPI app is live"
  value       = google_cloud_run_v2_service.deep_research_app.uri
}
