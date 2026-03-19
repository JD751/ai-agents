#!/usr/bin/env bash
# infra/github-secrets.sh — Set GitHub Actions secrets required for CD
#
# Run this AFTER infra/setup-oidc.sh has printed the three IDs.
# The gh CLI must be authenticated: `gh auth login`
#
# Usage:
#   export GITHUB_ORG=<your-github-username-or-org>
#   export GITHUB_REPO=<your-repo-name>
#   export AZURE_CLIENT_ID=<from setup-oidc.sh output>
#   export AZURE_TENANT_ID=<from setup-oidc.sh output>
#   export AZURE_SUBSCRIPTION_ID=<from setup-oidc.sh output>
#   ./infra/github-secrets.sh
set -euo pipefail

: "${GITHUB_ORG:?GITHUB_ORG env var is required}"
: "${GITHUB_REPO:?GITHUB_REPO env var is required}"
: "${AZURE_CLIENT_ID:?AZURE_CLIENT_ID env var is required}"
: "${AZURE_TENANT_ID:?AZURE_TENANT_ID env var is required}"
: "${AZURE_SUBSCRIPTION_ID:?AZURE_SUBSCRIPTION_ID env var is required}"

REPO="${GITHUB_ORG}/${GITHUB_REPO}"

echo "==> Setting GitHub Actions secrets on ${REPO}"

gh secret set AZURE_CLIENT_ID       --body "$AZURE_CLIENT_ID"       --repo "$REPO"
gh secret set AZURE_TENANT_ID       --body "$AZURE_TENANT_ID"       --repo "$REPO"
gh secret set AZURE_SUBSCRIPTION_ID --body "$AZURE_SUBSCRIPTION_ID" --repo "$REPO"

echo ""
echo "==> Enabling branch protection on main"
# Requires all three CI jobs to pass before any push to main is accepted.
# --input reads a proper JSON body — --field cannot handle nested objects.
gh api "repos/${REPO}/branches/main/protection" \
  --method PUT \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Test", "Lint", "Docker Build"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
EOF

echo ""
echo "✓ Secrets set and branch protection enabled."
echo "  Main branch now requires Test, Lint, and Docker Build to pass."
echo "  The CD deploy job will trigger on the next push to main."
