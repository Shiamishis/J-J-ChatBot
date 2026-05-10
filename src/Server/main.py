import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from pydantic import BaseModel

from src.RAG.resources import Resources
from src.Server.session_manager import SessionManager

class ChatMessage(BaseModel):
    session_id: str
    prompt: str

class EndChat(BaseModel):
    session_id: str


# lifespan — composition root, owns all config and instantiation
@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO change this to load from a config file or secret manager
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")
    app.state.api_key = api_key
    app.state.resources = Resources(app.state.api_key)
    app.state.session_manager = SessionManager()
    yield
    app.state.session_manager.close()
    app.state.resources.close()

app = FastAPI(lifespan=lifespan)

@app.post("/chat/start")
async def create_chat_endpoint():
    # TODO: potentially take user_id for personalization and analytics
    session_id = app.state.session_manager.create_session(app.state.resources)
    return {"session_id": session_id}


@app.post("/chat/message")
async def chat_endpoint(data: ChatMessage):
    """
    The endpoint to perform RAG and query the LLM with a prompt.
    """
    # Notice we don't need `await request.json()` anymore!
    # FastAPI parses and validates it automatically.
    prompt = data.prompt
    session_id = data.session_id

    try:
        session = app.state.session_manager.get_session(session_id)
        response = session.prompt(prompt)
        return {"response": response}
    except ValueError as e:
        return {"error": str(e)}, 404
    except Exception as e:
        return {"error": str(e)}, 500


@app.post("/chat/end")
async def end_chat_endpoint(data: EndChat):
    session_id = data.session_id
    try:
        session = app.state.session_manager.get_session(session_id)
        session.end()
        return {"success": True}
    except ValueError as e:
        return {"error": str(e)}, 404
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/health")
async def health_endpoint():
    try:
        session_manager = app.state.session_manager
        resources = app.state.resources
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}, 500