#!/usr/bin/env bash
# Levanta todo el backend y frontend dentro de GitHub Codespaces (o en local).
# Reintenta solo si Docker Hub falla por límite de descargas.
set -uo pipefail
cd "$(dirname "$0")/../infra"

[ -f .env ] || { cp .env.example .env; echo ">> Creé infra/.env. Editalo y pegá tu ANTHROPIC_API_KEY, después volvé a correr este script."; }

if [ -n "${CODESPACE_NAME:-}" ]; then
  export S3_ENDPOINT_PUBLIC="https://${CODESPACE_NAME}-9000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
  gh codespace ports visibility 3000:public 8000:public 9000:public -c "$CODESPACE_NAME" 2>/dev/null \
    || echo ">> No pude hacer públicos los puertos. Hacelo a mano en la pestaña PORTS."
fi

# Descarga cada imagen base por separado, con reintentos, antes de levantar todo junto.
# Esto evita que un solo fallo de red (típico límite de Docker Hub) tire abajo todo el intento.
pull_with_retry() {
  local image="$1" tries=6 wait=10
  for i in $(seq 1 $tries); do
    docker pull "$image" && return 0
    echo ">> No se pudo descargar $image (intento $i/$tries). Reintento en ${wait}s..."
    sleep "$wait"
    wait=$((wait * 2))
  done
  echo ">> No se pudo descargar $image después de $tries intentos."
  return 1
}

for img in postgres:16-alpine redis:7-alpine quay.io/minio/minio:latest; do
  pull_with_retry "$img" || echo ">> Seguirá reintentando dentro de docker compose."
done

up_with_retry() {
  local tries=5 wait=15
  for i in $(seq 1 $tries); do
    if docker compose up --build -d; then
      return 0
    fi
    echo ">> docker compose falló (intento $i/$tries). Reintento en ${wait}s..."
    sleep "$wait"
    wait=$((wait * 2))
  done
  return 1
}

if up_with_retry; then
  echo ""
  echo ">> Todo arriba."
  if [ -n "${CODESPACE_NAME:-}" ]; then
    echo ">> APP:   https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}   <- abrí esta en el iPhone"
    echo ">> API:   https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}/docs"
  fi
  echo ">> Para ver los logs: cd infra && docker compose logs -f"
else
  echo ""
  echo ">> No se pudo levantar todo después de varios intentos (probablemente Docker Hub sigue limitando descargas)."
  echo ">> Probá: docker login   (con una cuenta gratis de hub.docker.com) y correé este script de nuevo."
fi
