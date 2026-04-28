variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region where the Cloud Run service is deployed."
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name to monitor."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
}

variable "notification_channel_ids" {
  description = "Optional Cloud Monitoring notification channel IDs."
  type        = list(string)
  default     = []
}

variable "labels" {
  description = "User labels applied to alert policies."
  type        = map(string)
  default     = {}
}

variable "enable_5xx_alert" {
  description = "Whether to create a Cloud Run 5xx alert policy."
  type        = bool
  default     = true
}

variable "five_xx_error_rate_threshold" {
  description = "Alert threshold for 5xx request rate per second across the service."
  type        = number
  default     = 0
}

variable "five_xx_alignment_period" {
  description = "Alignment period used to evaluate Cloud Run 5xx request metrics."
  type        = string
  default     = "300s"
}

variable "five_xx_duration" {
  description = "Duration the threshold must hold before an incident opens."
  type        = string
  default     = "300s"
}

variable "enable_latency_alert" {
  description = "Whether to create a Cloud Run latency alert policy."
  type        = bool
  default     = true
}

variable "latency_threshold_ms" {
  description = "Latency threshold in milliseconds. Default 2000 ms means 2 seconds."
  type        = number
  default     = 2000
}

variable "latency_alignment_period" {
  description = "Alignment period used to evaluate Cloud Run latency metrics."
  type        = string
  default     = "300s"
}

variable "latency_duration" {
  description = "Duration the latency threshold must hold before alerting."
  type        = string
  default     = "300s"
}

variable "latency_per_series_aligner" {
  description = "Cloud Monitoring aligner used for the Cloud Run latency metric."
  type        = string
  default     = "ALIGN_MEAN"
}
