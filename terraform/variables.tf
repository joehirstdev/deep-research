variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  default = "us-central1"
  type    = string
}

variable "image_path" {
  description = "Full path to the Docker image in Artifact Registry"
  type        = string
}

variable "env_vars" {
  description = "Environment variables for the container"
  type        = map(string)
}
