resource "google_cloud_run_v2_service" "deep_research_app" {
  name     = "deep-research-app"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {

    # Configure max instances of applicatoin
    scaling {
      max_instance_count = 1
      min_instance_count = 0
    }

    containers {
      image = var.image_path

      # FastAPI port
      ports {
        container_port = 8000
      }

      # Provision resources for container
      resources {
        limits = {
          cpu    = "0.5"
          memory = "256Mi"
        }
        cpu_idle = true
      }

      # Load env vars into container
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
