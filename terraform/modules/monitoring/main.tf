locals {
  monitored_service_name = "${var.service_name}-${var.environment}"
}

# Cloud Logging is enabled automatically for Cloud Run. Application stdout/stderr
# and request logs flow into Cloud Logging without extra Terraform resources.
#
# Cloud Monitoring also receives Cloud Run metrics automatically, including request
# count, latency, container CPU, memory, and instance count. This alert policy
# uses those built-in metrics to signal 5xx failures for the service.
resource "google_monitoring_alert_policy" "cloud_run_5xx" {
  count        = var.enable_5xx_alert ? 1 : 0
  project      = var.project_id
  display_name = "${local.monitored_service_name}-5xx-errors"
  combiner     = "OR"
  enabled      = true

  documentation {
    mime_type = "text/markdown"
    content   = <<-EOT
    Cloud Run is serving 5xx responses for `${local.monitored_service_name}` in `${var.region}`.

    Check recent request logs in Cloud Logging and review service revisions, rollout changes, and upstream dependency behavior.
    EOT
  }

  conditions {
    display_name = "Cloud Run 5xx request rate"

    condition_threshold {
      comparison      = "COMPARISON_GT"
      threshold_value = var.five_xx_error_rate_threshold
      duration        = var.five_xx_duration
      filter          = <<-EOT
      resource.type="cloud_run_revision"
      resource.label."service_name"="${local.monitored_service_name}"
      resource.label."location"="${var.region}"
      metric.type="run.googleapis.com/request_count"
      metric.label."response_code_class"="5xx"
      EOT

      aggregations {
        alignment_period   = var.five_xx_alignment_period
        per_series_aligner = "ALIGN_RATE"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = var.notification_channel_ids
  user_labels           = var.labels
  severity              = "ERROR"
}

resource "google_monitoring_alert_policy" "cloud_run_latency" {
  count        = var.enable_latency_alert ? 1 : 0
  project      = var.project_id
  display_name = "${local.monitored_service_name}-high-latency"
  combiner     = "OR"
  enabled      = true

  documentation {
    mime_type = "text/markdown"
    content   = <<-EOT
    Cloud Run request latency for `${local.monitored_service_name}` in `${var.region}` is above the configured threshold.

    Review recent request logs in Cloud Logging, check upstream dependency latency, and inspect Cloud Run revision scaling behavior.
    EOT
  }

  conditions {
    display_name = "Cloud Run request latency above ${var.latency_threshold_ms} ms"

    condition_threshold {
      comparison      = "COMPARISON_GT"
      threshold_value = var.latency_threshold_ms
      duration        = var.latency_duration
      filter          = <<-EOT
      resource.type="cloud_run_revision"
      resource.label."service_name"="${local.monitored_service_name}"
      resource.label."location"="${var.region}"
      metric.type="run.googleapis.com/request_latencies"
      EOT

      aggregations {
        alignment_period   = var.latency_alignment_period
        per_series_aligner = var.latency_per_series_aligner
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = var.notification_channel_ids
  user_labels           = var.labels
  severity              = "WARNING"
}
