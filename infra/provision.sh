#!/usr/bin/env bash
# infra/provision.sh — One-shot Azure provisioning for bayer-ai
#
# Implements Day 9 Steps 1-8: resource group, ACR, Key Vault, PostgreSQL,
# Container Apps environment, managed identity, image push, and app deploy.
#
# Usage:
#   export OPENAI_API_KEY=<your-key>
#   export LANGCHAIN_API_KEY=<your-key>
#   ./infra/provision.sh
#
# Prerequisites: az CLI logged in, Docker running, jq installed.
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
RESOURCE_GROUP="bayer-ai-rg"
LOCATION="eastus"
DB_LOCATION="northeurope"   # eastus is restricted for PostgreSQL on free tiers
ACR_NAME="bayerairegistry"
KV_NAME="bayer-ai-kv"
DB_SERVER="bayer-ai-db"
DB_NAME="bayerai"
ENV_NAME="bayer-ai-env"
IDENTITY_NAME="bayer-ai-identity"
APP_NAME="bayer-ai-app"
IMAGE_TAG="latest"
IMAGE="${ACR_NAME}.azurecr.io/bayer-ai:${IMAGE_TAG}"

# ── Validate required secrets ─────────────────────────────────────────────────
# Secrets must come from the environment, never be hardcoded.
: "${OPENAI_API_KEY:?OPENAI_API_KEY env var is required}"
: "${LANGCHAIN_API_KEY:?LANGCHAIN_API_KEY env var is required}"

echo "==> [1/8] Creating resource group: $RESOURCE_GROUP in $LOCATION"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

# ── Step 2: Azure Container Registry ─────────────────────────────────────────
echo "==> [2/8] Creating ACR: $ACR_NAME"
# --admin-enabled false enforces managed identity auth — no stored credentials.
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled false \
  --output none

# ── Step 3: Key Vault + secrets ───────────────────────────────────────────────
echo "==> [3/8] Creating Key Vault: $KV_NAME"
az keyvault create \
  --name "$KV_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

# Grant the current CLI user secrets-write access (RBAC vault: no implicit creator access).
CURRENT_USER_ID=$(az ad signed-in-user show --query id -o tsv)
KV_SCOPE=$(az keyvault show --name "$KV_NAME" --query id -o tsv)

az role assignment create \
  --role "Key Vault Secrets Officer" \
  --assignee "$CURRENT_USER_ID" \
  --scope "$KV_SCOPE" \
  --output none

echo "    Storing API key secrets..."
az keyvault secret set --vault-name "$KV_NAME" --name OPENAI-API-KEY  --value "$OPENAI_API_KEY"  --output none
az keyvault secret set --vault-name "$KV_NAME" --name LANGCHAIN-API-KEY --value "$LANGCHAIN_API_KEY" --output none

# Generate DB credentials — password is never printed to terminal or shell history.
DB_ADMIN_USER="bayeradmin"
DB_ADMIN_PASSWORD=$(openssl rand -base64 32)
az keyvault secret set --vault-name "$KV_NAME" --name DB-ADMIN-USER     --value "$DB_ADMIN_USER"     --output none
az keyvault secret set --vault-name "$KV_NAME" --name DB-ADMIN-PASSWORD --value "$DB_ADMIN_PASSWORD" --output none

# ── Step 4: PostgreSQL Flexible Server ───────────────────────────────────────
echo "==> [4/8] Provisioning PostgreSQL Flexible Server in $DB_LOCATION (takes ~5 min)"
# Using DB_LOCATION (northeurope) because eastus has quota restrictions on free tiers.
az postgres flexible-server create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$DB_SERVER" \
  --location "$DB_LOCATION" \
  --admin-user "$DB_ADMIN_USER" \
  --admin-password "$DB_ADMIN_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --output none

# Store the full async connection string so the app never builds it at runtime.
DATABASE_URL="postgresql+asyncpg://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_SERVER}.postgres.database.azure.com/${DB_NAME}?ssl=require"
az keyvault secret set --vault-name "$KV_NAME" --name DATABASE-URL --value "$DATABASE_URL" --output none

# ── Step 5: Container Apps Environment ───────────────────────────────────────
echo "==> [5/8] Creating Container Apps Environment: $ENV_NAME"
# The environment is the shared networking boundary — one log analytics workspace
# for all containers (app + ChromaDB sidecar if added later).
az containerapp env create \
  --name "$ENV_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

# ── Step 6: Managed Identity + role assignments ───────────────────────────────
echo "==> [6/8] Creating managed identity and assigning roles"
az identity create \
  --name "$IDENTITY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --output none

IDENTITY_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)
IDENTITY_PRINCIPAL_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query principalId -o tsv)

ACR_SCOPE=$(az acr show --name "$ACR_NAME" --query id -o tsv)

# AcrPull: lets the Container App pull images without ACR admin credentials.
az role assignment create \
  --assignee "$IDENTITY_PRINCIPAL_ID" \
  --role AcrPull \
  --scope "$ACR_SCOPE" \
  --output none

# Key Vault Secrets User: read-only access to secrets at runtime.
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee "$IDENTITY_PRINCIPAL_ID" \
  --scope "$KV_SCOPE" \
  --output none

# ── Step 7: Build and push image ──────────────────────────────────────────────
echo "==> [7/8] Building and pushing Docker image to ACR"
# az acr login uses the current CLI identity — no docker login with credentials.
az acr login --name "$ACR_NAME"
docker build -t "$IMAGE" .
docker push "$IMAGE"

# ── Step 8: Deploy Container App ─────────────────────────────────────────────
echo "==> [8/8] Deploying Container App: $APP_NAME"
# Key Vault references resolve at startup via the managed identity — secrets are
# never passed as plain env vars or stored in Container Apps config.
az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENV_NAME" \
  --image "$IMAGE" \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --user-assigned "$IDENTITY_ID" \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 3 \
  --secrets \
    "openai-key=keyvaultref:https://${KV_NAME}.vault.azure.net/secrets/OPENAI-API-KEY,identityref:${IDENTITY_ID}" \
    "langchain-key=keyvaultref:https://${KV_NAME}.vault.azure.net/secrets/LANGCHAIN-API-KEY,identityref:${IDENTITY_ID}" \
    "database-url=keyvaultref:https://${KV_NAME}.vault.azure.net/secrets/DATABASE-URL,identityref:${IDENTITY_ID}" \
  --env-vars \
    "OPENAI_API_KEY=secretref:openai-key" \
    "LANGCHAIN_API_KEY=secretref:langchain-key" \
    "DATABASE_URL=secretref:database-url" \
    "LANGCHAIN_TRACING_V2=true" \
    "LANGCHAIN_PROJECT=bayer-ai" \
    "LANGCHAIN_ENDPOINT=https://eu.api.smith.langchain.com" \
    "CHROMA_PERSIST_DIR=/chroma_db" \
    "APP_ENV=production" \
  --output none

# ── Done ──────────────────────────────────────────────────────────────────────
FQDN=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "✓ Deployment complete"
echo "  App URL : https://${FQDN}"
echo "  Health  : https://${FQDN}/health"
echo ""
echo "Next: run infra/setup-oidc.sh to wire up GitHub Actions CD"
