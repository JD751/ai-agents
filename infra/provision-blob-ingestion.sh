#!/usr/bin/env bash
# infra/provision-blob-ingestion.sh — Provision Azure Blob Storage + Function App ingestion pipeline
#
# Run once after provision.sh has completed (requires ACR, Key Vault, Container Apps env to exist).
#
# What this script does:
#   1. Creates Azure Storage account + blob container for documents
#   2. Generates a ChromaDB auth token and stores it in Key Vault
#   3. Updates ChromaDB Container App: external ingress + token auth enabled
#   4. Creates Azure Function App (consumption plan) with Managed Identity
#   5. Grants Function identity read access to Blob Storage and Key Vault
#   6. Sets all required env vars on the Function App
#   7. Uploads existing documents/ to blob storage to seed the vector store
#
# Usage:
#   ./infra/provision-blob-ingestion.sh
#
# Prerequisites: az CLI logged in, provision.sh already run.
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
RESOURCE_GROUP="bayer-ai-rg"
LOCATION="eastus"
KV_NAME="bayer-ai-kv"
ENV_NAME="bayer-ai-env"
STORAGE_ACCOUNT="bayeraidocsstorage"
BLOB_CONTAINER="bayer-ai-documents"
FUNCTION_APP="bayer-ai-ingest-fn"
CHROMA_APP="chromadb"
DOCUMENTS_DIR="documents"

# ── Step 1: Storage account + blob container ──────────────────────────────────
echo "==> [1/7] Creating storage account: $STORAGE_ACCOUNT"
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --output none

echo "    Creating blob container: $BLOB_CONTAINER"
az storage container create \
  --account-name "$STORAGE_ACCOUNT" \
  --name "$BLOB_CONTAINER" \
  --auth-mode login \
  --output none

STORAGE_SCOPE=$(az storage account show \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --query id -o tsv)

# ── Step 2: ChromaDB auth token → Key Vault ───────────────────────────────────
echo "==> [2/7] Generating ChromaDB auth token and storing in Key Vault"
CHROMA_TOKEN=$(openssl rand -base64 32 | tr -d '=+/' | head -c 40)
az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name "CHROMA-AUTH-TOKEN" \
  --value "$CHROMA_TOKEN" \
  --output none

KV_SCOPE=$(az keyvault show --name "$KV_NAME" --query id -o tsv)

# ── Step 3: Update ChromaDB — external ingress + token auth ───────────────────
echo "==> [3/7] Updating ChromaDB Container App: external ingress + token auth"
az containerapp ingress update \
  --name "$CHROMA_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --type external \
  --target-port 8000 \
  --output none

CHROMA_FQDN=$(az containerapp show \
  --name "$CHROMA_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

# Retrieve Key Vault resource ID for secret references on the ChromaDB Container App.
# ChromaDB uses a user-assigned identity — reuse bayer-ai-identity provisioned in provision.sh.
IDENTITY_ID=$(az identity show \
  --name "bayer-ai-identity" \
  --resource-group "$RESOURCE_GROUP" \
  --query id -o tsv)

az containerapp update \
  --name "$CHROMA_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --secrets \
    "chroma-auth-token=keyvaultref:https://${KV_NAME}.vault.azure.net/secrets/CHROMA-AUTH-TOKEN,identityref:${IDENTITY_ID}" \
  --set-env-vars \
    "CHROMA_SERVER_AUTH_CREDENTIALS=secretref:chroma-auth-token" \
    "CHROMA_SERVER_AUTH_CREDENTIALS_PROVIDER=chromadb.auth.token.TokenConfigServerAuthCredentialsProvider" \
    "CHROMA_SERVER_AUTH_PROVIDER=chromadb.auth.token.TokenAuthServerProvider" \
  --output none

echo "    ChromaDB FQDN: https://${CHROMA_FQDN}"

# ── Step 4: Create Function App with Managed Identity ─────────────────────────
echo "==> [4/7] Creating Function App: $FUNCTION_APP"
az functionapp create \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --storage-account "$STORAGE_ACCOUNT" \
  --consumption-plan-location "$LOCATION" \
  --runtime python \
  --runtime-version 3.12 \
  --functions-version 4 \
  --assign-identity \
  --output none

FN_PRINCIPAL=$(az functionapp identity show \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --query principalId -o tsv)

# ── Step 5: RBAC — Blob Storage + Key Vault access ────────────────────────────
echo "==> [5/7] Assigning RBAC roles to Function identity"

# Blob Storage: read blobs to download documents for ingestion
az role assignment create \
  --role "Storage Blob Data Reader" \
  --assignee "$FN_PRINCIPAL" \
  --scope "$STORAGE_SCOPE" \
  --output none

# Key Vault: read secrets (OPENAI_API_KEY, CHROMA_AUTH_TOKEN)
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee "$FN_PRINCIPAL" \
  --scope "$KV_SCOPE" \
  --output none

# ── Step 6: Function App env vars ─────────────────────────────────────────────
echo "==> [6/7] Configuring Function App settings"

OPENAI_KEY_URI="https://${KV_NAME}.vault.azure.net/secrets/OPENAI-API-KEY"
CHROMA_TOKEN_URI="https://${KV_NAME}.vault.azure.net/secrets/CHROMA-AUTH-TOKEN"

az functionapp config appsettings set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    "OPENAI_API_KEY=@Microsoft.KeyVault(SecretUri=${OPENAI_KEY_URI})" \
    "CHROMA_AUTH_TOKEN=@Microsoft.KeyVault(SecretUri=${CHROMA_TOKEN_URI})" \
    "CHROMA_HOST=https://${CHROMA_FQDN}" \
    "EMBEDDING_MODEL=text-embedding-3-small" \
    "BlobStorageConnection__accountName=${STORAGE_ACCOUNT}" \
    "BlobStorageConnection__credential=managedidentity" \
  --output none

# ── Step 7: Upload existing documents to blob storage ─────────────────────────
echo "==> [7/7] Uploading existing documents to blob storage"
if [ -d "$DOCUMENTS_DIR" ] && [ "$(ls -A $DOCUMENTS_DIR)" ]; then
  az storage blob upload-batch \
    --account-name "$STORAGE_ACCOUNT" \
    --destination "$BLOB_CONTAINER" \
    --source "$DOCUMENTS_DIR" \
    --auth-mode login \
    --output none
  echo "    Documents uploaded from ./$DOCUMENTS_DIR"
else
  echo "    No documents found in ./$DOCUMENTS_DIR — skipping upload"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "✓ Blob ingestion infrastructure provisioned"
echo "  Storage account : $STORAGE_ACCOUNT"
echo "  Blob container  : $BLOB_CONTAINER"
echo "  Function App    : $FUNCTION_APP"
echo "  ChromaDB        : https://${CHROMA_FQDN} (external, token auth enabled)"
echo ""
echo "Next: push to main to deploy the Function code via CI/CD (Step D)"
