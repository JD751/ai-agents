Day 9 – Deploy to Azure: Step-by-Step Plan
Prerequisites (verify first)
Azure CLI installed and logged in (az login)
Docker Desktop running
GitHub repo with secrets access
CI pipeline from Day 8 passing
Step 1 — Create Azure Resource Group
Why: All Azure resources for this project live in one resource group — makes billing, access control, and teardown clean and isolated.


az group create --name bayer-ai-rg --location eastus
Step 2 — Provision Azure Container Registry (ACR)
Why: ACR is where your Docker image lives. Container Apps pulls from it. Using ACR (vs Docker Hub) keeps everything within Azure's private network and avoids rate limits.


az acr create \
  --resource-group bayer-ai-rg \
  --name bayerairegistry \
  --sku Basic \
  --admin-enabled false
--admin-enabled false forces managed identity auth — no hardcoded credentials.

Step 3 — Provision Azure Key Vault
Why: Secrets like OPENAI_API_KEY and DATABASE_URL must never be in environment variable plain text or in code. Key Vault + managed identity is the Azure-native zero-secret pattern.
Note: DATABASE-URL is stored AFTER Step 4 — the PostgreSQL server must exist first.


az keyvault create \
  --name bayer-ai-kv \
  --resource-group bayer-ai-rg \
  --location eastus

# Grant yourself write access BEFORE storing any secrets (required — RBAC vaults have no implicit creator access)
az role assignment create \
  --role "Key Vault Secrets Officer" \
  --assignee $(az ad signed-in-user show --query id -o tsv) \
  --scope $(az keyvault show --name bayer-ai-kv --query id -o tsv)

# Store non-DB secrets now
az keyvault secret set --vault-name bayer-ai-kv --name OPENAI-API-KEY --value "<your-key>"
az keyvault secret set --vault-name bayer-ai-kv --name LANGCHAIN-API-KEY --value "<your-key>"

# Generate and store DB credentials — password is never typed or seen
az keyvault secret set \
  --vault-name bayer-ai-kv \
  --name DB-ADMIN-USER \
  --value "bayeradmin"

az keyvault secret set \
  --vault-name bayer-ai-kv \
  --name DB-ADMIN-PASSWORD \
  --value "$(openssl rand -base64 32)"

# DATABASE-URL is stored after Step 4 once the server hostname is known

Step 4 — Provision Azure Database for PostgreSQL (Flexible Server)
Why: Managed PostgreSQL removes the ops burden of running a DB container in production. It handles backups, patching, and HA. Your existing DATABASE_URL config just points to this instead of localhost.
Note: eastus and eastus2 are restricted for PostgreSQL Flexible Server on free/trial subscriptions. Use northeurope or run the region check below.

# Check which regions work for your subscription
az provider show \
  --namespace Microsoft.DBforPostgreSQL \
  --query "resourceTypes[?resourceType=='flexibleServers'].locations[]" \
  -o tsv

# Retrieve credentials from Key Vault — password never touches shell history
az postgres flexible-server create \
  --resource-group bayer-ai-rg \
  --name bayer-ai-db \
  --location northeurope \
  --admin-user "$(az keyvault secret show --vault-name bayer-ai-kv --name DB-ADMIN-USER --query value -o tsv)" \
  --admin-password "$(az keyvault secret show --vault-name bayer-ai-kv --name DB-ADMIN-PASSWORD --query value -o tsv)" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32

# Now store the full production connection string in Key Vault
az keyvault secret set \
  --vault-name bayer-ai-kv \
  --name DATABASE-URL \
  --value "postgresql+asyncpg://$(az keyvault secret show --vault-name bayer-ai-kv --name DB-ADMIN-USER --query value -o tsv):$(az keyvault secret show --vault-name bayer-ai-kv --name DB-ADMIN-PASSWORD --query value -o tsv)@bayer-ai-db.postgres.database.azure.com/bayerai?ssl=require"

Step 5 — Create Container Apps Environment
Why: The environment is the shared networking boundary for all your containers (app + ChromaDB). It maps to a virtual network and provides a single log analytics workspace — one place to see all logs.


az containerapp env create \
  --name bayer-ai-env \
  --resource-group bayer-ai-rg \
  --location eastus
Step 6 — Assign Managed Identity
Why: Container Apps need to pull images from ACR and read secrets from Key Vault without any stored credentials. Managed identity is the Azure-native way — identity is issued to the container at runtime, not baked into config.


# Create a user-assigned managed identity
az identity create --name bayer-ai-identity --resource-group bayer-ai-rg

# Grant ACR pull access
az role assignment create \
  --assignee <identity-client-id> \
  --role AcrPull \
  --scope /subscriptions/<sub-id>/resourceGroups/bayer-ai-rg/providers/Microsoft.ContainerRegistry/registries/bayerairegistry

# Grant Key Vault secret read access via RBAC (vault uses enableRbacAuthorization — set-policy does not work)
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee <identity-principal-id> \
  --scope $(az keyvault show --name bayer-ai-kv --query id -o tsv)
Step 7 — Push Docker Image to ACR
Why: ACR needs the image before Container Apps can deploy it. This is the manual first push — after this, CI/CD takes over.


az acr login --name bayerairegistry
docker build -t bayerairegistry.azurecr.io/bayer-ai:latest .
docker push bayerairegistry.azurecr.io/bayer-ai:latest
Step 8 — Deploy Container App
Why: This is the actual workload deployment. You configure ingress (public HTTPS), scaling rules (min 0, max 3 replicas), and Key Vault secret references here.


az containerapp create \
  --name bayer-ai-app \
  --resource-group bayer-ai-rg \
  --environment bayer-ai-env \
  --image bayerairegistry.azurecr.io/bayer-ai:latest \
  --registry-server bayerairegistry.azurecr.io \
  --user-assigned <identity-resource-id> \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 3 \
  --secrets "openai-key=keyvaultref:https://bayer-ai-kv.vault.azure.net/secrets/OPENAI-API-KEY,identityref:<identity-resource-id>" \
           "langchain-key=keyvaultref:https://bayer-ai-kv.vault.azure.net/secrets/LANGCHAIN-API-KEY,identityref:<identity-resource-id>" \
  --env-vars "OPENAI_API_KEY=secretref:openai-key" \
             "LANGCHAIN_API_KEY=secretref:langchain-key" \
             "LANGCHAIN_TRACING_V2=true" \
             "LANGCHAIN_PROJECT=bayer-ai" \
             "LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com" \
             "CHROMA_PERSIST_DIR=/chroma_db" \
             "APP_ENV=production"
min-replicas 0 = scale to zero when idle (cost saving). max-replicas 3 = auto-scale under load.

Step 8b — Enable LangSmith Tracing on Deployed Container
Why: The initial deploy only passed OPENAI_API_KEY. Without LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY as env vars, settings.langchain_tracing_v2 defaults to False and the tracing block in main.py never fires. These commands add the missing secret + env vars to the running app without touching existing config.

# 1. Get identity resource ID (if not already saved)
IDENTITY_ID=$(az identity show \
  --name bayer-ai-identity \
  --resource-group bayer-ai-rg \
  --query id -o tsv)

# 2. Register the LangChain API key secret (already in Key Vault from Step 3)
az containerapp secret set \
  --name bayer-ai-app \
  --resource-group bayer-ai-rg \
  --secrets "langchain-key=keyvaultref:https://bayer-ai-kv.vault.azure.net/secrets/LANGCHAIN-API-KEY,identityref:$IDENTITY_ID"

# 3. Add env vars — --set-env-vars adds without removing existing ones
az containerapp update \
  --name bayer-ai-app \
  --resource-group bayer-ai-rg \
  --set-env-vars \
    "LANGCHAIN_API_KEY=secretref:langchain-key" \
    "LANGCHAIN_TRACING_V2=true" \
    "LANGCHAIN_PROJECT=bayer-ai" \
    "LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com"

# 4. Verify all env vars are set
az containerapp show \
  --name bayer-ai-app \
  --resource-group bayer-ai-rg \
  --query "properties.template.containers[0].env" -o table

Step 9 — Add CD Job to GitHub Actions
Why: Manual deploys don't scale. The CD job closes the loop: every merge to main builds, pushes, and redeploys automatically. This is the "always deployable" engineering standard.

Add a deploy job to .github/workflows/ci.yml after docker-build:


deploy:
  name: Deploy to Azure
  runs-on: ubuntu-latest
  needs: [docker-build]
  if: github.ref == 'refs/heads/main'

  steps:
    - uses: actions/checkout@v4

    - name: Azure Login (OIDC)
      uses: azure/login@v2
      with:
        client-id: ${{ secrets.AZURE_CLIENT_ID }}
        tenant-id: ${{ secrets.AZURE_TENANT_ID }}
        subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

    - name: Push image to ACR
      run: |
        az acr login --name bayerairegistry
        docker build -t bayerairegistry.azurecr.io/bayer-ai:${{ github.sha }} .
        docker push bayerairegistry.azurecr.io/bayer-ai:${{ github.sha }}

    - name: Deploy to Container Apps
      run: |
        az containerapp update \
          --name bayer-ai-app \
          --resource-group bayer-ai-rg \
          --image bayerairegistry.azurecr.io/bayer-ai:${{ github.sha }}
GitHub Secrets needed: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID — configure via OIDC federation (no stored service principal passwords).

Step 10 — Verify the Deployment
Why: Trust but verify. Hit the public endpoint to confirm the app is live and secrets are resolving correctly.


# Get the public URL
az containerapp show \
  --name bayer-ai-app \
  --resource-group bayer-ai-rg \
  --query properties.configuration.ingress.fqdn -o tsv

# Test health endpoint
curl https://<fqdn>/health
Summary: What You'll Have at End of Day 9
Component	Azure Service	Purpose
Container image	ACR	Versioned, private image registry
App runtime	Container Apps	Auto-scaling, HTTPS, zero infra ops
Secrets	Key Vault + Managed Identity	Zero hardcoded credentials
Database	PostgreSQL Flexible Server	Managed, persistent, production DB
CI/CD	GitHub Actions + OIDC	Push-to-deploy on every merge
The key senior-engineer move here is managed identity everywhere — no service principal passwords, no secrets in env vars, no ACR admin credentials. Azure handles the identity lifecycle.