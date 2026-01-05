resource "google_cloud_run_v2_service" "deep_research_app" {
  name     = "deep-research-app"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {

    # Configure max instances of application
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

      # Regular environment variables
      dynamic "env" {
        for_each = local.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      # Secret environment variables from Secret Manager
      dynamic "env" {
        for_each = local.secret_vars
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }
  }
}

locals {
  # Environment variables
  env_vars = {
    LLM_MODEL    = "gemini-3-flash-preview"
    LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
  }

  # Secret environment variables (references to Secret Manager secret names)
  secret_vars = {
    LLM_API_KEY         = "deep-research-llm-api-key"
    TAVILY_API_KEY      = "deep-research-tavily-api-key"
    BASIC_AUTH_USERNAME = "deep-research-basic-auth-username"
    BASIC_AUTH_PASSWORD = "deep-research-basic-auth-password"
  }
}
