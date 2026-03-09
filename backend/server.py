import os
from typing import Optional

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# -----------------------------------------------------------------------------
# Configuration (via .env)
# -----------------------------------------------------------------------------
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
CASES_SERVICE_URL = os.getenv("CASES_SERVICE_URL", "http://cases-service:8002")
IMAGES_SERVICE_URL = os.getenv("WORKFLOW_SERVICE_URL", "http://workflow-service:8003")
REPORTS_SERVICE_URL = os.getenv("REPORTS_SERVICE_URL", "http://reports-service:8004")
WORKFLOW_SERVICE_URL = os.getenv("IMAGES_SERVICE_URL", "http://images-service:8005")

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"

# Timeout proxy (en secondes)
PROXY_TIMEOUT = float(os.getenv("PROXY_TIMEOUT", "60"))

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(title="PathoCollab API Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS.split(",")] if CORS_ORIGINS != "*" else ["*"],
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Un client HTTP réutilisé (perf + keep-alive)
http_client: Optional[httpx.AsyncClient] = None


@app.on_event("startup")
async def _startup():
    global http_client
    http_client = httpx.AsyncClient(timeout=PROXY_TIMEOUT)


@app.on_event("shutdown")
async def _shutdown():
    global http_client
    if http_client:
        await http_client.aclose()
        http_client = None


@app.get("/health")
async def health():
    # Health minimal (gateway vivant)
    return {"status": "ok"}


def _pick_upstream(path: str) -> str:
    """
    Mappe un chemin API gateway -> URL du service cible.
    Règles (à adapter si besoin) :
        /api/auth/*        -> auth-service
        /api/cases/*       -> cases-service
        /api/patients/*    -> cases-service
        /api/images/*      -> images-service
        /api/reports/*     -> reports-service
        /api/workflow/*    -> workflow-service
    """
    if path.startswith("/api/auth"):
        return AUTH_SERVICE_URL
    if path.startswith("/api/cases") or path.startswith("/api/patients"):
        return CASES_SERVICE_URL
    if path.startswith("/api/images"):
        return IMAGES_SERVICE_URL
    if path.startswith("/api/reports"):
        return REPORTS_SERVICE_URL
    if path.startswith("/api/workflow"):
        return WORKFLOW_SERVICE_URL

    # Par défaut, tu peux choisir de renvoyer 404 (plus safe)
    # ou router sur cases-service. Ici: 404 géré dans le handler.
    return ""


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def _filter_headers(headers: httpx.Headers) -> dict:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}


@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_api(full_path: str, request: Request):
    """
    Proxy générique pour toutes routes /api/*.
    Le frontend continue d'appeler le gateway, et le gateway forward vers le bon service.
    """
    assert http_client is not None, "HTTP client not initialized"

    incoming_path = f"/api/{full_path}"
    upstream_base = _pick_upstream(incoming_path)

    if not upstream_base:
        return Response(
            content=f"Unknown API route: {incoming_path}",
            status_code=404,
            media_type="text/plain",
        )

    upstream_url = f"{upstream_base}{incoming_path}"

    # Query params + body
    params = dict(request.query_params)
    body = await request.body()

    # Headers: on forward presque tout (sauf hop-by-hop)
    headers = dict(request.headers)
    # Optionnel: tu peux ajouter un header de traçage
    headers["x-forwarded-by"] = "pathocollab-gateway"

    try:
        upstream_resp = await http_client.request(
            method=request.method,
            url=upstream_url,
            params=params,
            content=body if body else None,
            headers={k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS},
        )
    except httpx.RequestError as e:
        return Response(
            content=f"Upstream unreachable: {upstream_base} ({type(e).__name__}: {e})",
            status_code=502,
            media_type="text/plain",
        )

    # Réponse: on renvoie status + body + headers filtrés
    resp_headers = _filter_headers(upstream_resp.headers)
    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )