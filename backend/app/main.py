from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_lookups import router as lookups_router
from app.api.ws import router as ws_router

app = FastAPI(title="Company Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lookups_router, prefix="/api")
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"status": "ok"}
