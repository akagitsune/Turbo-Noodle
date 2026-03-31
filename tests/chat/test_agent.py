"""Unit tests for the MovieChatAgent and its LangGraph nodes."""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from src.chat.agent import MovieChatAgent


@pytest.fixture
def mock_llm():
    """Return a MagicMock LLM that defaults to replying with 'NO'."""
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="NO")
    return llm


@pytest.fixture
def agent(mock_llm):
    """Return a MovieChatAgent with ChatOllama patched to use mock_llm."""
    with patch("src.chat.agent.ChatOllama", return_value=mock_llm):
        return MovieChatAgent()


def test_load_prompt():
    """Verify that load_prompt returns a non-empty string for an existing prompt file."""
    from src.chat.agent import load_prompt
    content = load_prompt("answer.txt")
    assert isinstance(content, str)
    assert len(content) > 0


def test_route_after_retrieval_check_needs_db(agent):
    """Route to query_database when requires_retrieval is True."""
    state = {"requires_retrieval": True}
    assert agent.route_after_retrieval_check(state) == "query_database"


def test_route_after_retrieval_check_use_history(agent):
    """Route to answer when requires_retrieval is False."""
    state = {"requires_retrieval": False}
    assert agent.route_after_retrieval_check(state) == "answer"


def test_retrieve_data_node_no_history(agent):
    """Always require retrieval when there is no chat history."""
    state = {"query": "What movies did Nolan direct?", "messages": []}
    result = agent.retrieve_data_node(state, {})
    assert result["requires_retrieval"] is True


def test_retrieve_data_node_history_hit(agent, mock_llm):
    """Skip retrieval when the LLM confirms the answer is in history."""
    mock_llm.invoke.return_value = AIMessage(content="YES")
    state = {
        "query": "What was that movie?",
        "messages": [
            HumanMessage(content="Tell me about Inception"),
            AIMessage(content="Inception is a 2010 sci-fi film by Christopher Nolan."),
        ],
    }
    result = agent.retrieve_data_node(state, {})
    assert result["requires_retrieval"] is False


def test_retrieve_data_node_history_miss(agent, mock_llm):
    """Require retrieval when the LLM says the answer is not in history."""
    mock_llm.invoke.return_value = AIMessage(content="NO")
    state = {
        "query": "Who directed The Dark Knight?",
        "messages": [
            HumanMessage(content="Tell me about Inception"),
            AIMessage(content="Inception is a 2010 sci-fi film."),
        ],
    }
    result = agent.retrieve_data_node(state, {})
    assert result["requires_retrieval"] is True


@patch("src.chat.agent.db_connector")
def test_query_database_node(mock_db_connector, agent, mock_llm):
    """Verify that valid SQL is executed and results are returned as a string."""
    mock_db_connector.sql_db.get_usable_table_names.return_value = ["movies", "directors"]
    mock_db_connector.sql_db.get_table_info.return_value = "CREATE TABLE movies (id INTEGER, title TEXT)"
    mock_llm.invoke.return_value = AIMessage(content="Action: SELECT name FROM directors WHERE id = 1")
    # execute_sql returns list[dict], matching the real DatabaseConnector implementation
    mock_db_connector.execute_sql.return_value = [{"name": "Christopher Nolan"}]

    state = {"query": "Who directed Inception?"}
    result = agent.query_database_node(state, {})

    assert result["db_results"] == "{'name': 'Christopher Nolan'}"
    mock_db_connector.execute_sql.assert_called_once()


@patch("src.chat.agent.db_connector")
def test_query_database_node_failure(mock_db_connector, agent, mock_llm):
    """Return empty db_results when SQL execution raises an exception."""
    mock_db_connector.sql_db.get_usable_table_names.return_value = ["movies"]
    mock_db_connector.sql_db.get_table_info.return_value = "CREATE TABLE movies (id INTEGER, title TEXT)"
    mock_llm.invoke.return_value = AIMessage(content="Action: SELECT * FROM movies")
    mock_db_connector.execute_sql.side_effect = Exception("DB connection error")

    state = {"query": "Who directed Inception?"}
    result = agent.query_database_node(state, {})

    assert result["db_results"] == ""


def test_answer_node(agent, mock_llm):
    """Verify that answer_node generates an answer and appends messages to state."""
    mock_llm.invoke.return_value = AIMessage(content="Inception is a great film directed by Nolan.")
    state = {
        "query": "Tell me about Inception",
        "messages": [
            HumanMessage(content="What movies did Nolan make?"),
            AIMessage(content="He made Inception, The Dark Knight, Interstellar."),
        ],
    }
    result = agent.answer_node(state, {})

    assert "Inception" in result["answer"]
    assert len(result["messages"]) == 2
    assert isinstance(result["messages"][0], HumanMessage)
    assert isinstance(result["messages"][1], AIMessage)


def test_answer_node_no_db_results_returns_fallback(agent):
    """Verify answer_node does not hallucinate when db_results is None or empty."""
    for bad_results in (None, ""):
        state = {
            "query": "Who starred in Inception?",
            "requires_retrieval": True,
            "db_results": bad_results,
        }
        result = agent.answer_node(state, {})
        assert "couldn't find" in result["answer"].lower()
        assert len(result["messages"]) == 2
