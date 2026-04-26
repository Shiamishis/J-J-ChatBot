from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.LLM.llms import get_llm
from src.RAG.agent import RAGOrchestrator
import os
# lifespan — composition root, owns all config and instantiation
@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")

    small_llm = get_llm("groq", api_key=api_key, model="llama-3.1-8b-instant")
    large_llm = get_llm("groq", api_key=api_key, model="llama-3.3-70b-versatile")

    orchestrator = RAGOrchestrator(small_llm=small_llm, large_llm=large_llm)
    await orchestrator.initialize()
    app.state.orchestrator = orchestrator
    yield
    await orchestrator.close()

app = FastAPI(lifespan=lifespan)

@app.get("/prompt/{prompt}")
async def prompt_endpoint(prompt: str):
    """
    The endpoint to perform RAG and query the LLM with a prompt.
    :param prompt: The user's query to the LLM.
    :return: The response of the LLM using the context given by RAG.
    """
    orchestrator = app.state.orchestrator
    response = orchestrator.prompt(prompt)
    return {"response": response}
