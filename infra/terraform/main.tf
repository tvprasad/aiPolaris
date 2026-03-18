# main.tf — reference existing resources, don't recreate them
data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "shared" {
  name = var.resource_group_name
}

data "azurerm_cognitive_account" "openai" {
  name                = var.openai_resource_name
  resource_group_name = data.azurerm_resource_group.shared.name
}

data "azurerm_search_service" "search" {
  name                = var.search_service_name
  resource_group_name = data.azurerm_resource_group.shared.name
}

# Reference existing ACR (shared with Meridian)
data "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = data.azurerm_resource_group.shared.name
}

# ── NEW resources — aiPolaris only, zero impact on Meridian ──────────────────

resource "azurerm_user_assigned_identity" "aipolaris" {
  name                = "aipolaris-identity"
  resource_group_name = data.azurerm_resource_group.shared.name
  location            = data.azurerm_resource_group.shared.location
}

resource "azurerm_key_vault" "aipolaris" {
  name                       = var.vault_name
  resource_group_name        = data.azurerm_resource_group.shared.name
  location                   = var.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 7
}

resource "azurerm_storage_account" "aipolaris" {
  name                     = var.storage_name
  resource_group_name      = data.azurerm_resource_group.shared.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true # ADLS Gen2
}

resource "azurerm_log_analytics_workspace" "aipolaris" {
  name                = "aipolaris-logs"
  resource_group_name = data.azurerm_resource_group.shared.name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "aipolaris" {
  name                       = "aipolaris-env"
  resource_group_name        = data.azurerm_resource_group.shared.name
  location                   = var.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.aipolaris.id
}

resource "azurerm_container_app" "aipolaris" {
  name                         = "aipolaris-api"
  container_app_environment_id = azurerm_container_app_environment.aipolaris.id
  resource_group_name          = data.azurerm_resource_group.shared.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aipolaris.id]
  }

  registry {
    server   = data.azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.aipolaris.id
  }

  template {
    min_replicas = 0
    max_replicas = 3

    container {
      name   = "aipolaris-api"
      image  = "${data.azurerm_container_registry.acr.login_server}/aipolaris:latest"
      cpu    = 0.5
      memory = "1Gi"

      # All endpoints from Terraform outputs — ADR-009
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "AUTH_ENABLED"
        value = "true"
      }
      env {
        name  = "OPENAI_ENDPOINT"
        value = local.openai_endpoint
      }
      env {
        name  = "OPENAI_DEPLOYMENT"
        value = "gpt-4o"
      }
      env {
        name  = "SEARCH_ENDPOINT"
        value = local.search_endpoint
      }
      env {
        name  = "SEARCH_INDEX_NAME"
        value = "aipolaris-index"
      }
      env {
        name  = "GRAPH_ENDPOINT"
        value = local.graph_endpoint
      }
      env {
        name  = "ADLS_ENDPOINT"
        value = local.adls_endpoint
      }
      env {
        name  = "KEYVAULT_ENDPOINT"
        value = local.keyvault_endpoint
      }
      env {
        name  = "AUTHORITY"
        value = local.authority
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

# ── Outputs ──────────────────────────────────────────────────────────────────

output "container_app_url" {
  value = "https://${azurerm_container_app.aipolaris.ingress[0].fqdn}"
}