variable "project_id" {
  description = "Google Cloud project ID where resources will be created."
  type        = string
}

variable "region" {
  description = "GCP region for Artifact Registry and Cloud Run."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "service_name" {
  description = "Base service name for the application."
  type        = string
  default     = "dag-health-api"
}

variable "image_tag" {
  description = "Docker image tag to deploy when container_image is not set directly."
  type        = string
  default     = "latest"
}

variable "container_image" {
  description = "Optional full container image reference. If null, Terraform derives it from Artifact Registry outputs plus image_tag."
  type        = string
  default     = null
}

variable "container_port" {
  description = "Container port exposed by the FastAPI container in Cloud Run."
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
  description = "Cloud Run request timeout."
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
  description = "Whether the Cloud Run service allows unauthenticated invocation."
  type        = bool
  default     = true
}

variable "env_vars" {
  description = "Extra environment variables passed to the FastAPI container."
  type        = map(string)
  default = {
    APP_ENV          = "dev"
    APP_LOG_LEVEL    = "INFO"
    APP_SERVICE_NAME = "dag-health-api"
  }
}

variable "notification_channel_ids" {
  description = "Optional Cloud Monitoring notification channel IDs."
  type        = list(string)
  default     = []
}

variable "enable_5xx_alert" {
  description = "Whether to create the Cloud Monitoring 5xx alert policy."
  type        = bool
  default     = true
}

variable "five_xx_error_rate_threshold" {
  description = "Threshold for Cloud Run 5xx requests per second."
  type        = number
  default     = 0
}

variable "five_xx_alignment_period" {
  description = "Alignment period used for the 5xx alert."
  type        = string
  default     = "300s"
}

variable "five_xx_duration" {
  description = "Duration the 5xx threshold must persist before alerting."
  type        = string
  default     = "300s"
}

variable "enable_latency_alert" {
  description = "Whether to create the Cloud Monitoring latency alert policy."
  type        = bool
  default     = true
}

variable "latency_threshold_ms" {
  description = "Latency threshold in milliseconds. Default 2000 ms means 2 seconds."
  type        = number
  default     = 2000
}

variable "latency_alignment_period" {
  description = "Alignment period used for the latency alert."
  type        = string
  default     = "300s"
}

variable "latency_duration" {
  description = "Duration the latency threshold must persist before alerting."
  type        = string
  default     = "300s"
}

variable "latency_per_series_aligner" {
  description = "Cloud Monitoring aligner used for the request latency metric."
  type        = string
  default     = "ALIGN_MEAN"
}
