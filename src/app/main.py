"""FastAPI application entry point for the Movie AI Agent."""

import logging
import sys
import uuid
from fastapi import FastAPI, HTTPException

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
    force=True,  # override any handlers uvicorn may have already set
)

logger = logging.getLogger(__name__)

from src.app import schemas  # noqa: E402
from src.chat.agent import MovieChatAgent  # noqa: E402

app = FastAPI(
    title="Conversational Movie AI Agent",
    description="REST API for answering queries using a LangGraph Movie Agent.",
    version="1.0.0"
)

# Initialize the chat agent
chat_agent = MovieChatAgent()


@app.get("/health")
def health_check():
    """Return a simple liveness status for health-check probes."""
    return {"status": "ok"}


@app.post("/chat", response_model=schemas.ChatResponse)
def chat_endpoint(request: schemas.ChatRequest):
    """
    Core endpoint that takes a user's natural language question, processes it,
    retrieves data via a LangGraph state machine, and returns a conversational LLM response.
    """
    # Each request without a session_id gets its own isolated thread.
    # Sharing "default" would mix conversations across users.
    thread_id = request.session_id or str(uuid.uuid4())
    logger.info("chat: session_id=%r query=%r", thread_id, request.query)

    config = {"configurable": {"thread_id": thread_id}}

    # Run the graph
    try:
        app_state = chat_agent.invoke(request.query, config)
    except Exception as exc:
        logger.error("chat: agent invoke failed | session_id=%r error=%s", thread_id, exc)
        raise HTTPException(status_code=503, detail="Agent temporarily unavailable")

    # Extract outputs
    reply = app_state.get("answer", "I could not generate an answer.")
    requires_retrieval = app_state.get("requires_retrieval", False)

    intent = "retrieve" if requires_retrieval else "chat"
    retrieved = ["Executed DB Query"] if requires_retrieval else []

    logger.info("chat: session_id=%r intent=%s reply_length=%d", thread_id, intent, len(reply))
    return schemas.ChatResponse(
        reply=reply,
        intent=intent,
        retrieved_movies=retrieved
    )
