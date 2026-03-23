from fastapi import FastAPI
from rag import retrieve_context
from llm import query

app = FastAPI()

@app.get("/prompt/{prompt}")
async def query(prompt: str):
    """
    The endpoint to perform RAG and query the LLM with a prompt.
    :param prompt: The user's query to the LLM.
    :return: The response of the LLM using the context given by RAG.
    """
    context = retrieve_context(prompt)
    response = query(prompt, context)
    return {"response": response}
