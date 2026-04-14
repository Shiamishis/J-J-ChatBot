from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.RAG.agent import RAGAgent

@asynccontextmanager
async def lifespan(app: FastAPI):
    agent = RAGAgent()
    await agent.initialize()
    app.state.agent = agent
    yield
    await agent.close()

app = FastAPI(lifespan=lifespan)

@app.get("/prompt/{prompt}")
async def prompt_endpoint(prompt: str):
    """
    The endpoint to perform RAG and query the LLM with a prompt.
    :param prompt: The user's query to the LLM.
    :return: The response of the LLM using the context given by RAG.
    """
    agent = app.state.agent
    response = agent.prompt(prompt)
    return {"response": response}
