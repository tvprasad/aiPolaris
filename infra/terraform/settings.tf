# infra/terraform/settings.tf
# GCCH endpoint matrix — ADR-009
# Every Azure endpoint parameterized by var.environment.
# application code reads ALL endpoints from settings.py (Terraform outputs).
# Zero hardcoded URLs in application code — enforced by /gcch-check skill + CI.

locals {
  # Azure OpenAI
  openai_endpoint = var.environment == "gcch" ? (
    "https://${var.resource_name}.openai.azure.us"
  ) : (
    "https://${var.resource_name}.openai.azure.com"
  )

  # Azure AI Search
  search_endpoint = var.environment == "gcch" ? (
    "https://${var.search_name}.search.azure.us"
  ) : (
    "https://${var.search_name}.search.windows.net"
  )

  # Microsoft Graph API
  graph_endpoint = var.environment == "gcch" ? (
    "https://graph.microsoft.us"
  ) : (
    "https://graph.microsoft.com"
  )

  # ADLS Gen2
  adls_endpoint = var.environment == "gcch" ? (
    "https://${var.storage_name}.dfs.core.usgovcloudapi.net"
  ) : (
    "https://${var.storage_name}.dfs.core.windows.net"
  )

  # Azure Key Vault
  keyvault_endpoint = var.environment == "gcch" ? (
    "https://${var.vault_name}.vault.usgovcloudapi.net"
  ) : (
    "https://${var.vault_name}.vault.azure.net"
  )

  # Entra ID authority
  authority = var.environment == "gcch" ? (
    "https://login.microsoftonline.us"
  ) : (
    "https://login.microsoftonline.com"
  )
}

# Outputs — read by settings.py at deploy time
output "openai_endpoint"   { value = local.openai_endpoint }
output "search_endpoint"   { value = local.search_endpoint }
output "graph_endpoint"    { value = local.graph_endpoint }
output "adls_endpoint"     { value = local.adls_endpoint }
output "keyvault_endpoint" { value = local.keyvault_endpoint }
output "authority"         { value = local.authority }
output "environment"       { value = var.environment }
