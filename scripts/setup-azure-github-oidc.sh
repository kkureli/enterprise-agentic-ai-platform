#!/usr/bin/env bash
# One-time Azure + GitHub OIDC setup for backend Container Apps CD.
#
# Safe to inspect before running. Does NOT:
# - create client secrets
# - print subscription secrets / DB URLs / API keys
# - delete resources
# - run as part of CI
#
# GitHub Actions issues an *immutable* OIDC subject that includes numeric
# owner and repository IDs (not name-only). Entra federated credentials must
# match that format or token exchange fails with AADSTS700213.
#
# Subject shape (resolved dynamically via `gh api`):
#   repo:<owner>@<OWNER_ID>/<repo>@<REPO_ID>:environment:<env>
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
#   ./scripts/setup-azure-github-oidc.sh

set -euo pipefail

GITHUB_REPO="${GITHUB_REPO:-kkureli/enterprise-agentic-ai-platform}"
GITHUB_ENV_NAME="${GITHUB_ENV_NAME:-production}"
AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-enterprise-agentic-ai}"
AZURE_CONTAINER_APP="${AZURE_CONTAINER_APP:-enterprise-agentic-ai-backend}"
AZURE_CONTAINER_APP_URL="${AZURE_CONTAINER_APP_URL:-https://enterprise-agentic-ai-backend.jollyplant-fb706637.swedencentral.azurecontainerapps.io}"
APP_DISPLAY_NAME="${APP_DISPLAY_NAME:-github-aca-backend-cd}"
FEDERATION_NAME="${FEDERATION_NAME:-github-environment-production}"
OIDC_ISSUER="https://token.actions.githubusercontent.com"
OIDC_AUDIENCE="api://AzureADTokenExchange"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd az
require_cmd gh
require_cmd jq

if [[ "${GITHUB_REPO}" != */* ]]; then
  echo "GITHUB_REPO must be owner/name, got: ${GITHUB_REPO}" >&2
  exit 1
fi

echo "Resolving immutable GitHub owner/repository IDs via gh api…"
REPO_JSON="$(gh api "repos/${GITHUB_REPO}")"
OWNER_ID="$(jq -r '.owner.id' <<<"${REPO_JSON}")"
REPO_ID="$(jq -r '.id' <<<"${REPO_JSON}")"
OWNER_LOGIN="$(jq -r '.owner.login' <<<"${REPO_JSON}")"
REPO_NAME_ACTUAL="$(jq -r '.name' <<<"${REPO_JSON}")"

if [[ -z "${OWNER_ID}" || "${OWNER_ID}" == "null" || -z "${REPO_ID}" || "${REPO_ID}" == "null" ]]; then
  echo "Failed to resolve owner/repo IDs from gh api repos/${GITHUB_REPO}" >&2
  exit 1
fi

# Match the subject GitHub Actions actually presents in production tokens.
SUBJECT="repo:${OWNER_LOGIN}@${OWNER_ID}/${REPO_NAME_ACTUAL}@${REPO_ID}:environment:${GITHUB_ENV_NAME}"

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
APP_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${AZURE_RESOURCE_GROUP}/providers/Microsoft.App/containerApps/${AZURE_CONTAINER_APP}"

cat <<EOF
============================================================
Intended OIDC setup (review before continuing)
============================================================
GitHub repository : ${GITHUB_REPO}
  owner login/id  : ${OWNER_LOGIN} / ${OWNER_ID}
  repo name/id    : ${REPO_NAME_ACTUAL} / ${REPO_ID}
GitHub environment: ${GITHUB_ENV_NAME}
OIDC subject      : ${SUBJECT}
  (immutable ID form — not name-only repo:owner/name:environment:…)
OIDC issuer       : ${OIDC_ISSUER}
OIDC audience     : ${OIDC_AUDIENCE}
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

CRED_JSON="$(jq -n \
  --arg name "${FEDERATION_NAME}" \
  --arg subject "${SUBJECT}" \
  --arg issuer "${OIDC_ISSUER}" \
  --arg audience "${OIDC_AUDIENCE}" \
  '{
    name: $name,
    issuer: $issuer,
    subject: $subject,
    audiences: [$audience],
    description: "GitHub Actions Backend CD (immutable environment subject)"
  }')"

echo "Ensuring federated credential '${FEDERATION_NAME}' matches immutable subject…"
EXISTING_SUBJECT="$(az ad app federated-credential list \
  --id "${CLIENT_ID}" \
  --query "[?name=='${FEDERATION_NAME}'].subject | [0]" \
  -o tsv 2>/dev/null || true)"

if [[ -z "${EXISTING_SUBJECT}" || "${EXISTING_SUBJECT}" == "null" ]]; then
  az ad app federated-credential create \
    --id "${CLIENT_ID}" \
    --parameters "${CRED_JSON}" >/dev/null
  echo "Federated credential created with subject: ${SUBJECT}"
elif [[ "${EXISTING_SUBJECT}" == "${SUBJECT}" ]]; then
  echo "Federated credential already matches immutable subject — no change."
else
  echo "Federated credential subject differs:"
  echo "  current : ${EXISTING_SUBJECT}"
  echo "  desired : ${SUBJECT}"
  echo "Updating federated credential in place (no duplicate)…"
  az ad app federated-credential update \
    --id "${CLIENT_ID}" \
    --federated-credential-id "${FEDERATION_NAME}" \
    --parameters "${CRED_JSON}" >/dev/null
  echo "Federated credential updated."
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

OIDC subject in use:
  ${SUBJECT}

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
