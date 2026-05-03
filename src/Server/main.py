import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from src.RAG.resources import Resources
from src.Server.session_manager import SessionManager


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
async def chat_endpoint(request: Request):
    """
    The endpoint to perform RAG and query the LLM with a prompt.
    :param prompt: The user's query to the LLM.
    :return: The response of the LLM using the context given by RAG.
    """
    data = await request.json()
    prompt = data.get("prompt")
    session_id = data.get("session_id")
    try:
        session = app.state.session_manager.get_session(session_id)
        response = session.prompt(prompt)
        return {"response": response}
    except ValueError as e:
        return {"error": str(e)}, 404
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/chat/end")
async def end_chat_endpoint(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
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