from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from pihole_blocker.config import AppConfig, Settings
from pihole_blocker.db.repository import Repository
from pihole_blocker.llm.summarizer import IncidentSummarizer


class FeedbackRequest(BaseModel):
    verdict: str = Field(pattern="^(tp|fp|ignore|allow_rule)$")
    note: str | None = None


def create_app(config: AppConfig, repo: Repository, summarizer: IncidentSummarizer) -> FastAPI:
    app = FastAPI(title="PiholeBlocker", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/stats")
    def stats():
        return repo.stats()

    @app.get("/api/incidents")
    def incidents(reviewed: bool | None = None, limit: int = 50):
        items = repo.list_incidents(reviewed=reviewed, limit=limit)
        return [
            {
                "id": i.id,
                "hostname": i.hostname,
                "client_ip": i.client_ip,
                "timestamp": i.timestamp,
                "risk_score": i.risk_score,
                "risk_label": i.risk_label,
                "pipeline_stage": i.pipeline_stage,
                "explanation": i.explanation,
                "reviewed": i.reviewed,
            }
            for i in items
        ]

    @app.post("/api/incidents/{incident_id}/feedback")
    def submit_feedback(incident_id: int, body: FeedbackRequest):
        repo.add_feedback(incident_id, body.verdict, body.note)
        return {"ok": True}

    @app.get("/api/summary")
    def summary():
        items = repo.list_incidents(limit=20)
        payload = [
            {
                "hostname": i.hostname,
                "risk_label": i.risk_label,
                "risk_score": i.risk_score,
                "reviewed": i.reviewed,
            }
            for i in items
        ]
        return {"summary": summarizer.summarize_incidents(payload)}

    @app.get("/", response_class=HTMLResponse)
    def dashboard():
        return DASHBOARD_HTML

    return app


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PiholeBlocker</title>
  <style>
    :root { font-family: system-ui, sans-serif; color: #1a1a2e; background: #f4f6fb; }
    body { max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
    h1 { margin-bottom: .25rem; }
    .sub { color: #555; margin-bottom: 1.5rem; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: .75rem; }
    .card { background: #fff; border-radius: 8px; padding: 1rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    .card strong { display: block; font-size: 1.5rem; }
    table { width: 100%; border-collapse: collapse; background: #fff; margin-top: 1.5rem; }
    th, td { text-align: left; padding: .6rem .5rem; border-bottom: 1px solid #eee; font-size: .9rem; }
    button { margin-right: .25rem; padding: .25rem .5rem; cursor: pointer; }
    #summary { background: #fff; padding: 1rem; border-radius: 8px; margin-top: 1rem; white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>PiholeBlocker</h1>
  <p class="sub">Panel local — revisión humana de incidentes DNS</p>
  <div class="cards" id="stats"></div>
  <p><button onclick="loadSummary()">Generar resumen (LLM opcional)</button></p>
  <div id="summary"></div>
  <table>
    <thead>
      <tr>
        <th>Hora</th><th>Cliente</th><th>Hostname</th><th>Riesgo</th><th>Etapa</th><th>Acción</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>
  <script>
    async function loadStats() {
      const s = await fetch('/api/stats').then(r => r.json());
      document.getElementById('stats').innerHTML = [
        ['Eventos', s.events], ['Incidentes', s.incidents],
        ['Pendientes', s.pending_review], ['Falsos positivos', s.false_positives]
      ].map(([k,v]) => `<div class="card"><span>${k}</span><strong>${v}</strong></div>`).join('');
    }
    async function loadIncidents() {
      const items = await fetch('/api/incidents?limit=30').then(r => r.json());
      document.getElementById('rows').innerHTML = items.map(i => `
        <tr>
          <td>${i.timestamp.slice(0,19)}</td>
          <td>${i.client_ip}</td>
          <td>${i.hostname}</td>
          <td>${i.risk_label} (${i.risk_score.toFixed(2)})</td>
          <td>${i.pipeline_stage}</td>
          <td>
            ${i.reviewed ? '✓' : `
              <button onclick="fb(${i.id},'tp')">TP</button>
              <button onclick="fb(${i.id},'fp')">FP</button>
              <button onclick="fb(${i.id},'ignore')">Ignorar</button>
            `}
          </td>
        </tr>`).join('');
    }
    async function fb(id, verdict) {
      await fetch(`/api/incidents/${id}/feedback`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({verdict})
      });
      loadStats(); loadIncidents();
    }
    async function loadSummary() {
      document.getElementById('summary').textContent = 'Generando...';
      const r = await fetch('/api/summary').then(r => r.json());
      document.getElementById('summary').textContent = r.summary;
    }
    loadStats(); loadIncidents();
    setInterval(() => { loadStats(); loadIncidents(); }, 10000);
  </script>
</body>
</html>
"""
