from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os

from llm_engine import call_llm_nl_to_sql
from database import ensure_database_exists

app = FastAPI(
    title="FloatChat MVP",
    description="Conversational Ocean ARGO Float Data Explorer",
    version="1.0.0"
)

@app.on_event("startup")
def on_startup():
    """Ensure database is seeded when container starts up on cloud hosts like Render."""
    try:
        ensure_database_exists()
    except Exception as e:
        print(f"[Startup Warning] Failed to seed database: {e}")

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message prompt cannot be empty.")

    try:
        result = call_llm_nl_to_sql(request.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# Serve static files for frontend UI
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "FloatChat API is running. Please check /static/index.html"}
