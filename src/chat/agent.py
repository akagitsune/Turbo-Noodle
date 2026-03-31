"""LangGraph-based conversational movie agent."""

import os
import re
import logging
from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_ollama import ChatOllama
from src.data.database import db_connector

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")


class ChatState(TypedDict):
    """Typed state dict passed between nodes in the LangGraph workflow."""

    messages: Annotated[list[BaseMessage], add_messages]
    query: str
    requires_retrieval: bool
    answer: Optional[str]
    db_results: Optional[str]


PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt(filename: str) -> str:
    """Load a prompt text file from the prompts directory, returning an empty string on failure."""
    path = os.path.join(PROMPTS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning("load_prompt: prompt file not found — %s", path)
        return ""


ANSWER_PROMPT = load_prompt("answer.txt")
CHECK_HISTORY_PROMPT = load_prompt("check_history.txt")
SQL_GENERATION_PROMPT = load_prompt("sql_generation.txt")
SYNTHESIS_PROMPT = load_prompt("synthesis.txt")
SYNTHESIS_HUMAN_PROMPT = load_prompt("synthesis_human.txt")


class MovieChatAgent:
    """LangGraph agent that answers movie-related questions using a text-to-SQL ReAct loop."""

    def __init__(self):
        """Initialise LLMs, memory, and compile the LangGraph workflow."""
        client_kwargs = {}
        if OLLAMA_API_KEY:
            client_kwargs["headers"] = {"Authorization": f"Bearer {OLLAMA_API_KEY}"}

        self.llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_HOST,
            temperature=0.0,
            client_kwargs=client_kwargs,
        )
        self.answer_llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_HOST,
            temperature=0.7,
            client_kwargs=client_kwargs,
        )
        self.memory = MemorySaver()
        self.app = self._build_graph()

    def _build_graph(self):
        """Construct and compile the LangGraph StateGraph with retrieval and answer nodes."""
        workflow = StateGraph(ChatState)

        workflow.add_node("retrieve_data", self.retrieve_data_node)
        workflow.add_node("query_database", self.query_database_node)
        workflow.add_node("answer", self.answer_node)

        workflow.add_edge(START, "retrieve_data")

        workflow.add_conditional_edges(
            "retrieve_data",
            self.route_after_retrieval_check,
            {
                "answer": "answer",
                "query_database": "query_database",
            },
        )

        workflow.add_edge("query_database", "answer")
        workflow.add_edge("answer", END)

        return workflow.compile(checkpointer=self.memory)

    def route_after_retrieval_check(self, state: ChatState) -> str:
        """Return the next node name based on whether database retrieval is required."""
        if state.get("requires_retrieval"):
            return "query_database"
        return "answer"

    def retrieve_data_node(self, state: ChatState, config: RunnableConfig) -> dict:
        """Checks if the answer is already in the chat history."""
        query = state.get("query", "")
        history_msgs = state.get("messages", [])

        if not history_msgs:
            logger.info("retrieve_data_node: no history — routing to query_database")
            return {"requires_retrieval": True}

        logger.info("retrieve_data_node: checking history for query=%r", query)

        system_msg = SystemMessage(content=CHECK_HISTORY_PROMPT)
        messages = [system_msg] + history_msgs + [
            HumanMessage(content=f"User Query: {query}\nDoes the history above contain the answer?")
        ]

        try:
            response = self.llm.invoke(messages, config=config)
            content = response.content.strip().upper()
        except Exception as exc:
            logger.error("retrieve_data_node: LLM call failed — %s", exc)
            return {"requires_retrieval": True}
        logger.debug("retrieve_data_node: history check response=%r", content)

        if "YES" in content:
            logger.info("retrieve_data_node: answer found in history")
            return {"requires_retrieval": False}

        logger.info("retrieve_data_node: answer NOT in history — routing to query_database")
        return {"requires_retrieval": True}

    @staticmethod
    def _extract_sql(text: str) -> str:
        """Strip markdown code fences from an LLM SQL response."""
        match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text.strip()

    def query_database_node(self, state: ChatState, config: RunnableConfig) -> dict:
        """Text-to-SQL pipeline with ReAct loop (up to 5 iterations): schema → (Thought → SQL → Observation) × N."""
        query = state.get("query", "")
        logger.info("query_database_node: start | query=%r", query)

        # Step 1: Gather live schema from the database
        try:
            table_names = db_connector.sql_db.get_usable_table_names()
            schema = db_connector.sql_db.get_table_info()
            logger.info(
                "query_database_node: schema loaded for tables: %s",
                ", ".join(table_names),
            )
        except Exception as exc:
            logger.error("query_database_node: schema load failed — %s", exc)
            return {"db_results": None}

        # Step 2: ReAct loop — Thought → Action (SQL) → Observation → repeat
        sql_system_prompt = SQL_GENERATION_PROMPT.format(schema=schema)

        messages = [SystemMessage(content=sql_system_prompt), HumanMessage(content=query)]
        MAX_ITERATIONS = 5
        last_rows: list | None = None

        for iteration in range(MAX_ITERATIONS):
            logger.info("query_database_node: ReAct iteration %d/%d", iteration + 1, MAX_ITERATIONS)

            try:
                response = self.llm.invoke(messages, config=config)
                raw_output = response.content.strip()
                logger.debug("query_database_node: LLM output=%r", raw_output)
            except Exception as exc:
                logger.error("query_database_node: LLM call failed — %s", exc)
                return {"db_results": None}

            # Parse Thought and Action from ReAct output
            thought_match = re.search(r"Thought:\s*(.+?)(?=Action:|$)", raw_output, re.DOTALL | re.IGNORECASE)
            action_match = re.search(r"Action:\s*(.+?)$", raw_output, re.DOTALL | re.IGNORECASE)

            thought = thought_match.group(1).strip() if thought_match else ""
            action = action_match.group(1).strip() if action_match else raw_output
            logger.debug("query_database_node: thought=%r", thought)

            sql = self._extract_sql(action)
            logger.info("query_database_node: extracted SQL=%r", sql)

            if not sql or sql.upper() == "CANNOT_GENERATE":
                logger.warning("query_database_node: LLM indicated query cannot be generated | query=%r", query)
                return {"db_results": None}

            if not sql.lstrip().upper().startswith("SELECT"):
                observation = f"Observation: Error — only SELECT statements are allowed. Received: {sql[:100]}"
                logger.error("query_database_node: non-SELECT SQL rejected | sql=%r", sql)
                messages = messages + [AIMessage(content=raw_output), HumanMessage(content=observation)]
                continue

            # Execute the SQL and observe the outcome
            try:
                rows = db_connector.execute_sql(sql)
                logger.info("query_database_node: SQL executed | rows=%d", len(rows))
            except Exception as exc:
                observation = f"Observation: SQL execution error — {exc}. Refine the query and try again."
                logger.error("query_database_node: execution failed — %s | sql=%r", exc, sql)
                messages = messages + [AIMessage(content=raw_output), HumanMessage(content=observation)]
                continue

            last_rows = rows

            if rows:
                results_text = "\n".join(str(row) for row in rows[:20])
                logger.info(
                    "query_database_node: success — %d row(s) on iteration %d",
                    len(rows), iteration + 1,
                )
                return {"db_results": results_text}

            observation = "Observation: Query returned 0 rows. Try a broader search or alternative approach."
            logger.info("query_database_node: empty result on iteration %d — retrying", iteration + 1)
            messages = messages + [AIMessage(content=raw_output), HumanMessage(content=observation)]

        # All iterations exhausted — return whatever the last execution produced
        logger.warning("query_database_node: all %d iterations exhausted | query=%r", MAX_ITERATIONS, query)
        if last_rows is not None:
            return {"db_results": "\n".join(str(row) for row in last_rows[:20])}
        return {"db_results": ""}

    def answer_node(self, state: ChatState, config: RunnableConfig) -> dict:
        """Generates a conversational answer — from DB results or conversation history."""
        query = state.get("query", "")

        if state.get("requires_retrieval"):
            db_results = state.get("db_results")
            if not db_results:
                # Guard against hallucinations: never synthesise without actual data.
                fallback = "I couldn't find any relevant information in the database for your query."
                logger.warning("answer_node: db_results empty/None — returning fallback to avoid hallucination")
                return {
                    "answer": fallback,
                    "messages": [HumanMessage(content=query), AIMessage(content=fallback)],
                }
            db_results_len = len(db_results)
            logger.info("answer_node: synthesising from DB results | result_chars=%d", db_results_len)
            try:
                response = self.answer_llm.invoke(
                    [
                        SystemMessage(content=SYNTHESIS_PROMPT),
                        HumanMessage(content=SYNTHESIS_HUMAN_PROMPT.format(query=query, db_results=db_results)),
                    ],
                    config=config,
                )
                answer = response.content.strip()
            except Exception as exc:
                logger.error("answer_node: LLM synthesis call failed — %s", exc)
                answer = "I encountered a technical issue while generating the answer."
        else:
            logger.info("answer_node: answering from history for query=%r", query)
            messages = [SystemMessage(content=ANSWER_PROMPT)] + state.get("messages", []) + [HumanMessage(content=query)]
            try:
                response = self.answer_llm.invoke(messages, config=config)
                answer = response.content
            except Exception as exc:
                logger.error("answer_node: LLM history call failed — %s", exc)
                answer = "I encountered a technical issue while generating the answer."

        logger.debug("answer_node: answer generated (length=%d)", len(answer))
        return {
            "answer": answer,
            "messages": [HumanMessage(content=query), AIMessage(content=answer)],
        }

    def invoke(self, query: str, config: dict):
        """Run the full agent graph for a single user query and return the final state."""
        thread_id = config.get("configurable", {}).get("thread_id", "?")
        logger.info("invoke: thread_id=%r query=%r", thread_id, query)
        initial_state = {"query": query}
        result = self.app.invoke(initial_state, config=config)
        logger.info("invoke: completed | thread_id=%r", thread_id)
        return result
