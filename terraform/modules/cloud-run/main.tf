locals {
  service_account_id = substr(replace("${var.service_name}-${var.environment}", "_", "-"), 0, 30)
  merged_env_vars = merge(
    {
      PORT = tostring(var.container_port)
    },
    var.env_vars
  )
}

resource "google_service_account" "this" {
  project      = var.project_id
  account_id   = local.service_account_id
  display_name = "${var.service_name} ${var.environment} Cloud Run runtime"
  description  = "Dedicated runtime identity for the ${var.service_name} Cloud Run service."
}

resource "google_cloud_run_v2_service" "this" {
  name     = "${var.service_name}-${var.environment}"
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL"
  labels   = var.labels

  template {
    service_account = google_service_account.this.email
    timeout         = var.timeout
    labels          = var.labels

    scaling {
      min_instance_count = var.min_instance_count
      max_instance_count = var.max_instance_count
    }

    containers {
      image   = var.container_image
      command = ["uvicorn"]
      args = [
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        tostring(var.container_port)
      ]

      ports {
        container_port = var.container_port
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
      }

      dynamic "env" {
        for_each = local.merged_env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count    = var.allow_unauthenticated ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
