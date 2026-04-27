variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for the Cloud Run service."
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
}

variable "container_image" {
  description = "Full container image reference to deploy to Cloud Run."
  type        = string
}

variable "container_port" {
  description = "Container port exposed by the application."
  type        = number
  default     = 8080
}

variable "cpu" {
  description = "CPU limit for the Cloud Run container."
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory limit for the Cloud Run container."
  type        = string
  default     = "512Mi"
}

variable "timeout" {
  description = "Request timeout for the Cloud Run service."
  type        = string
  default     = "30s"
}

variable "min_instance_count" {
  description = "Minimum number of Cloud Run instances."
  type        = number
  default     = 0
}

variable "max_instance_count" {
  description = "Maximum number of Cloud Run instances."
  type        = number
  default     = 3
}

variable "allow_unauthenticated" {
  description = "Whether to allow unauthenticated invocations. Keep false in production unless intentionally public."
  type        = bool
  default     = true
}

variable "env_vars" {
  description = "Environment variables injected into the Cloud Run container."
  type        = map(string)
  default     = {}
}

variable "labels" {
  description = "Labels applied to the Cloud Run service and service account."
  type        = map(string)
  default     = {}
}
