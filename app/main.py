from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from app.api.routes import search, graph, health, entities

app = FastAPI(title="Graph RAG Engine - SAP O2C")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(ServiceUnavailable)
@app.exception_handler(SessionExpired)
async def neo4j_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=503,
        content={"message": "The database is currently busy or unavailable. Please try your request again in a few seconds."},
    )


app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(entities.router, prefix="/api/entities", tags=["Entities"])

import os
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
