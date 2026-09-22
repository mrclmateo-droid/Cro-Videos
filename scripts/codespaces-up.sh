#!/usr/bin/env bash
# Levanta todo el backend dentro de GitHub Codespaces (o en local).
set -euo pipefail
cd "$(dirname "$0")/../infra"

[ -f .env ] || { cp .env.example .env; echo ">> Creé infra/.env. Editalo y pegá tu ANTHROPIC_API_KEY."; }

if [ -n "${CODESPACE_NAME:-}" ]; then
  # Las URLs firmadas de MinIO deben ser alcanzables desde tu navegador.
  export S3_ENDPOINT_PUBLIC="https://${CODESPACE_NAME}-9000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
  # Los puertos deben ser públicos para que el navegador pueda usarlos sin login extra.
  gh codespace ports visibility 3000:public 8000:public 9000:public -c "$CODESPACE_NAME" \
    || echo ">> No pude hacer públicos los puertos. Hacelo a mano en la pestaña PORTS."
  echo ">> APP:   https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}   <- abrí esta en el iPhone"
  echo ">> API:   https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}/docs"
fi

docker compose up --build
