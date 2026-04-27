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
