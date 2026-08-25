#!/usr/bin/env bash
# One-time Azure + GitHub OIDC setup for backend Container Apps CD.
#
# Safe to inspect before running. Does NOT:
# - create client secrets
# - print subscription secrets / DB URLs / API keys
# - delete resources
# - run as part of CI
#
# Prerequisites:
# - Azure CLI logged in with permission to create an app registration + role assignment
# - gh CLI authenticated to kkureli/enterprise-agentic-ai-platform
# - Existing Container App: enterprise-agentic-ai-backend in rg-enterprise-agentic-ai
#
# Usage:
#   export GITHUB_REPO="kkureli/enterprise-agentic-ai-platform"
#   export GITHUB_ENV_NAME="production"
#   export AZURE_RESOURCE_GROUP="rg-enterprise-agentic-ai"
#   export AZURE_CONTAINER_APP="enterprise-agentic-ai-backend"
#   export AZURE_CONTAINER_APP_URL="https://enterprise-agentic-ai-backend.jollyplant-fb706637.swedencentral.azurecontainerapps.io"
#   # optional overrides:
#   # export APP_DISPLAY_NAME="github-aca-backend-cd"
#   # export AZURE_LOCATION from az account
#   ./scripts/setup-azure-github-oidc.sh

set -euo pipefail

GITHUB_REPO="${GITHUB_REPO:-kkureli/enterprise-agentic-ai-platform}"
GITHUB_ENV_NAME="${GITHUB_ENV_NAME:-production}"
AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-enterprise-agentic-ai}"
AZURE_CONTAINER_APP="${AZURE_CONTAINER_APP:-enterprise-agentic-ai-backend}"
AZURE_CONTAINER_APP_URL="${AZURE_CONTAINER_APP_URL:-https://enterprise-agentic-ai-backend.jollyplant-fb706637.swedencentral.azurecontainerapps.io}"
APP_DISPLAY_NAME="${APP_DISPLAY_NAME:-github-aca-backend-cd}"
FEDERATION_NAME="${FEDERATION_NAME:-github-environment-production}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd az
require_cmd gh
require_cmd jq

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
APP_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${AZURE_RESOURCE_GROUP}/providers/Microsoft.App/containerApps/${AZURE_CONTAINER_APP}"
SUBJECT="repo:${GITHUB_REPO}:environment:${GITHUB_ENV_NAME}"

cat <<EOF
============================================================
Intended one-time OIDC setup (review before continuing)
============================================================
GitHub repository : ${GITHUB_REPO}
GitHub environment: ${GITHUB_ENV_NAME}
OIDC subject      : ${SUBJECT}
Azure tenant      : ${TENANT_ID}
Azure subscription: ${SUBSCRIPTION_ID}
Resource group    : ${AZURE_RESOURCE_GROUP}
Container App     : ${AZURE_CONTAINER_APP}
Role              : Container Apps Contributor
Role scope        : ${APP_SCOPE}
Backend URL var   : ${AZURE_CONTAINER_APP_URL}
App display name  : ${APP_DISPLAY_NAME}
============================================================
EOF

read -r -p "Continue? [y/N] " reply
if [[ ! "${reply}" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

echo "Ensuring Container App exists…"
az containerapp show \
  --name "${AZURE_CONTAINER_APP}" \
  --resource-group "${AZURE_RESOURCE_GROUP}" \
  --query "{name:name,fqdn:properties.configuration.ingress.fqdn}" \
  -o json >/dev/null

echo "Creating (or reusing) Microsoft Entra application…"
EXISTING_APP_ID="$(az ad app list --display-name "${APP_DISPLAY_NAME}" --query "[0].appId" -o tsv)"
if [[ -n "${EXISTING_APP_ID}" && "${EXISTING_APP_ID}" != "null" ]]; then
  CLIENT_ID="${EXISTING_APP_ID}"
  echo "Reusing app registration appId=${CLIENT_ID}"
else
  CLIENT_ID="$(az ad app create --display-name "${APP_DISPLAY_NAME}" --query appId -o tsv)"
  echo "Created app registration appId=${CLIENT_ID}"
fi

echo "Ensuring service principal exists…"
if ! az ad sp show --id "${CLIENT_ID}" >/dev/null 2>&1; then
  az ad sp create --id "${CLIENT_ID}" >/dev/null
fi
SP_OBJECT_ID="$(az ad sp show --id "${CLIENT_ID}" --query id -o tsv)"

echo "Creating federated credential for GitHub Environment subject…"
CRED_JSON="$(jq -n \
  --arg name "${FEDERATION_NAME}" \
  --arg subject "${SUBJECT}" \
  '{
    name: $name,
    issuer: "https://token.actions.githubusercontent.com",
    subject: $subject,
    audiences: ["api://AzureADTokenExchange"],
    description: "GitHub Actions Backend CD via environment production"
  }')"

if az ad app federated-credential list --id "${CLIENT_ID}" --query "[?name=='${FEDERATION_NAME}'].name" -o tsv | grep -q "${FEDERATION_NAME}"; then
  echo "Federated credential '${FEDERATION_NAME}' already exists — leaving unchanged."
else
  az ad app federated-credential create \
    --id "${CLIENT_ID}" \
    --parameters "${CRED_JSON}" >/dev/null
  echo "Federated credential created."
fi

echo "Assigning Container Apps Contributor on the Container App only…"
EXISTING_ROLE="$(az role assignment list \
  --assignee-object-id "${SP_OBJECT_ID}" \
  --assignee-principal-type ServicePrincipal \
  --scope "${APP_SCOPE}" \
  --query "[?roleDefinitionName=='Container Apps Contributor'].id" \
  -o tsv || true)"

if [[ -n "${EXISTING_ROLE}" ]]; then
  echo "Role assignment already present."
else
  az role assignment create \
    --assignee-object-id "${SP_OBJECT_ID}" \
    --assignee-principal-type ServicePrincipal \
    --role "Container Apps Contributor" \
    --scope "${APP_SCOPE}" >/dev/null
  echo "Role assignment created."
fi

echo "Ensuring GitHub Environment '${GITHUB_ENV_NAME}' exists…"
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${GITHUB_REPO}/environments/${GITHUB_ENV_NAME}" \
  --silent >/dev/null || true

echo "Setting GitHub Environment variables (identifiers only — no secrets)…"
gh variable set AZURE_CLIENT_ID --env "${GITHUB_ENV_NAME}" --repo "${GITHUB_REPO}" --body "${CLIENT_ID}"
gh variable set AZURE_TENANT_ID --env "${GITHUB_ENV_NAME}" --repo "${GITHUB_REPO}" --body "${TENANT_ID}"
gh variable set AZURE_SUBSCRIPTION_ID --env "${GITHUB_ENV_NAME}" --repo "${GITHUB_REPO}" --body "${SUBSCRIPTION_ID}"
gh variable set AZURE_RESOURCE_GROUP --env "${GITHUB_ENV_NAME}" --repo "${GITHUB_REPO}" --body "${AZURE_RESOURCE_GROUP}"
gh variable set AZURE_CONTAINER_APP --env "${GITHUB_ENV_NAME}" --repo "${GITHUB_REPO}" --body "${AZURE_CONTAINER_APP}"
gh variable set AZURE_CONTAINER_APP_URL --env "${GITHUB_ENV_NAME}" --repo "${GITHUB_REPO}" --body "${AZURE_CONTAINER_APP_URL}"

cat <<EOF

Done.

Next steps:
1. Confirm GHCR access for the Container App still works (already configured in Azure).
2. Do NOT create an Azure client secret.
3. Trigger Backend CD via workflow_dispatch, or push a backend-relevant change to master.
4. Confirm the Actions run: validate → image → deploy → /health → /ready.

Rollback (manual):
  az containerapp update \\
    --name ${AZURE_CONTAINER_APP} \\
    --resource-group ${AZURE_RESOURCE_GROUP} \\
    --image ghcr.io/kkureli/enterprise-agentic-ai-platform-backend:sha-<PREVIOUS_FULL_SHA>
EOF
