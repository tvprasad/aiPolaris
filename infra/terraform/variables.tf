variable "environment" {
  description = "Deployment environment: commercial or gcch"
  type        = string
  default     = "commercial"
  validation {
    condition     = contains(["commercial", "gcch"], var.environment)
    error_message = "environment must be 'commercial' or 'gcch'."
  }
}

variable "resource_name" {
  description = "Base name for Azure OpenAI resource"
  type        = string
}

variable "search_name" {
  description = "Azure AI Search resource name"
  type        = string
}

variable "storage_name" {
  description = "ADLS Gen2 storage account name"
  type        = string
}

variable "vault_name" {
  description = "Azure Key Vault resource name"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the existing shared resource group"
  type        = string
}

variable "openai_resource_name" {
  description = "Name of the existing Azure OpenAI resource"
  type        = string
}

variable "search_service_name" {
  description = "Name of the existing Azure AI Search service"
  type        = string
}

variable "acr_name" {
  description = "Name of the existing Azure Container Registry"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}
