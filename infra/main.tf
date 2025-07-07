terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  credentials = var.credentials_file
  project     = var.project_id
  region      = var.region
}

# Enable required APIs
resource "google_project_service" "run_api" {
  project = var.project_id
  service = "run.googleapis.com"
}

resource "google_project_service" "artifactregistry_api" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"
}

# Reference existing Artifact Registry repository
data "google_artifact_registry_repository" "tldw_registry" {
  location      = var.region
  repository_id = "tldw-registry"
}

# Service account for Cloud Run
resource "google_service_account" "tldw_service_account" {
  account_id   = "tldw-cloud-run"
  display_name = "TLDW Cloud Run Service Account"
}

# Secret Manager secret for OpenAI API key
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key"
  replication {
    auto {}
  }
}

# Grant the service account access to the secret
resource "google_secret_manager_secret_iam_member" "openai_api_key_access" {
  secret_id = google_secret_manager_secret.openai_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.tldw_service_account.email}"
}

# Cloud Run service
resource "google_cloud_run_v2_service" "tldw" {
  name     = "tldw-service"
  location = var.region
  depends_on = [
    google_project_service.run_api
  ]

  template {
    service_account = google_service_account.tldw_service_account.email
    
    timeout = "120s"
    
    scaling {
      min_instance_count = 0
      max_instance_count = 1  # Free tier: limit to 1 instance
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/tldw-registry/tldw:latest"
      
      resources {
        limits = {
          cpu    = "1000m"      # Free tier: 1 vCPU max
          memory = "512Mi"      # Free tier: 512MB max
        }
        cpu_idle = true         # Free tier: CPU only allocated when processing
      }

      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }

      ports {
        container_port = 8080
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
}

# Allow public access to Cloud Run service
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_v2_service.tldw.name
  location = google_cloud_run_v2_service.tldw.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Variables
variable "credentials_file" {
  description = "Path to GCP service account JSON key file"
  type        = string
}

variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "OPENAI_API_KEY" {
  description = "OpenAI API key - will be stored in Secret Manager"
  type        = string
  sensitive   = true
}

# Budget alert to monitor costs
resource "google_billing_budget" "free_tier_budget" {
  count = var.enable_budget_alerts ? 1 : 0
  
  billing_account = var.billing_account_id
  display_name    = "Free Tier Budget Alert"
  
  budget_filter {
    projects = ["projects/${var.project_id}"]
  }
  
  amount {
    specified_amount {
      currency_code = "USD"
      units         = "5"  # Alert at $5
    }
  }
  
  threshold_rules {
    threshold_percent = 0.8  # 80% of budget
    spend_basis       = "CURRENT_SPEND"
  }
  
  threshold_rules {
    threshold_percent = 1.0  # 100% of budget
    spend_basis       = "CURRENT_SPEND"
  }
}

# Variables for budget monitoring
variable "enable_budget_alerts" {
  description = "Enable budget alerts (requires billing account ID)"
  type        = bool
  default     = false
}

variable "billing_account_id" {
  description = "Billing account ID for budget alerts"
  type        = string
  default     = ""
}

# Outputs
output "service_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.tldw.uri
}

output "artifact_registry_url" {
  description = "URL of the Artifact Registry repository"
  value       = data.google_artifact_registry_repository.tldw_registry.name
}

output "free_tier_info" {
  description = "Free tier usage information"
  value = {
    cloud_run_requests = "2 million requests/month"
    cloud_run_cpu_time = "400,000 vCPU-seconds/month"
    cloud_run_memory   = "800,000 GiB-seconds/month"
    artifact_registry  = "0.5 GB storage free"
    secret_manager     = "6 active secrets free"
  }
}