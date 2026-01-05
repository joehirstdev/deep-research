output "service_url" {
  description = "The URL where your FastAPI app is live"
  value       = google_cloud_run_v2_service.deep_research_app.uri
}
