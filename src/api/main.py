from fastapi import FastAPI

app = FastAPI(title="FAB Financial Agent (dev)")


@app.get("/")
def root():
    return {"status": "ok", "service": "fab-financial-agent"}


@app.get("/health")
def health():
    return {"healthy": True}
