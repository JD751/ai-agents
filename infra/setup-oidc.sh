#!/usr/bin/env bash
# infra/setup-oidc.sh — Configure OIDC federation for GitHub Actions → Azure
#
# OIDC federation lets GitHub Actions authenticate to Azure using short-lived
# tokens signed by GitHub's OIDC provider. No service principal password is
# ever created or stored — the credentials can't be leaked because they don't
# exist as persistent secrets.
#
# Run this ONCE after provision.sh. Then add the three output values as GitHub
# repository secrets: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID.
#
# Usage:
#   export GITHUB_ORG=<your-github-username-or-org>
#   export GITHUB_REPO=<your-repo-name>
#   ./infra/setup-oidc.sh
set -euo pipefail

: "${GITHUB_ORG:?GITHUB_ORG env var is required (GitHub username or org)}"
: "${GITHUB_REPO:?GITHUB_REPO env var is required}"

RESOURCE_GROUP="bayer-ai-rg"
APP_NAME="bayer-ai-oidc-sp"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "==> Creating Entra ID app registration for OIDC"
# A lightweight app registration with no password — identity only.
APP_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)
SP_OBJECT_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)

echo "==> Assigning Contributor role on resource group"
# Scoped to resource group only — least-privilege: CD can update the app
# but cannot touch other subscriptions or resource groups.
az role assignment create \
  --assignee "$SP_OBJECT_ID" \
  --role Contributor \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
  --output none

echo "==> Adding AcrPush role so CD can push images"
ACR_SCOPE=$(az acr show --name bayerairegistry --query id -o tsv)
az role assignment create \
  --assignee "$SP_OBJECT_ID" \
  --role AcrPush \
  --scope "$ACR_SCOPE" \
  --output none

echo "==> Creating federated credential for main branch pushes"
# This OIDC subject exactly matches the token GitHub issues for push events
# on the main branch. Any other branch or event type is rejected by Azure.
APP_OBJECT_ID=$(az ad app show --id "$APP_ID" --query id -o tsv)
az ad app federated-credential create \
  --id "$APP_OBJECT_ID" \
  --parameters "{
    \"name\": \"github-main\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:${GITHUB_ORG}/${GITHUB_REPO}:ref:refs/heads/main\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"

echo ""
echo "✓ OIDC federation configured"
echo ""
echo "Add these three secrets to your GitHub repository"
echo "(Settings → Secrets and variables → Actions → New repository secret):"
echo ""
echo "  AZURE_CLIENT_ID       = ${APP_ID}"
echo "  AZURE_TENANT_ID       = ${TENANT_ID}"
echo "  AZURE_SUBSCRIPTION_ID = ${SUBSCRIPTION_ID}"
echo ""
echo "No passwords were created. These IDs are safe to store as GitHub secrets."
