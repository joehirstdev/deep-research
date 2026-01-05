variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  default = "europe-west1"
  type    = string
}

variable "image_path" {
  description = "Full path to the Docker image in Artifact Registry"
  type        = string
}
