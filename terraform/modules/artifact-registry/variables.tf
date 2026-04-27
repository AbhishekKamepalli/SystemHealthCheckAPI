variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for the Artifact Registry repository."
  type        = string
}

variable "repository_id" {
  description = "Artifact Registry repository ID."
  type        = string
}

variable "description" {
  description = "Description for the Artifact Registry repository."
  type        = string
  default     = "Docker repository for dag-health-api container images."
}

variable "labels" {
  description = "Labels applied to the repository."
  type        = map(string)
  default     = {}
}
