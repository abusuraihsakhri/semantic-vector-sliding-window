"""
FastAPI REST API Server for Semantic Vector Sliding Window.
"""
from typing import Dict, Any, List
import os
import hmac
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .metrics import GLOBAL_METRICS
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Semantic Vector Sliding Window API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "semantic-vector-sliding-window", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(GLOBAL_METRICS.export_prometheus_text(), media_type="text/plain; version=0.0.4")


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException:
        raise HTTPException(status_code=422, detail="Sensitive identifiers are not permitted in this endpoint")
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException:
        raise HTTPException(status_code=422, detail="Sensitive identifiers are not permitted in this endpoint")


@app.get("/api/audit/logs")
def api_audit_logs(x_audit_token: str = Header(default="")):
    expected = os.getenv("AUDIT_ACCESS_TOKEN")
    if not expected or not hmac.compare_digest(x_audit_token, expected):
        raise HTTPException(status_code=403, detail="Audit log access is disabled or unauthorized")
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
