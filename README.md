# Turbo-Noodle

Conversational Movie AI Agent REST API. Ask natural-language questions about movies and get intelligent, data-backed answers powered by a local LLM and a SQLite database built from TMDB data.

## Architecture

```
User
 └── Streamlit UI (port 8501)
      └── POST /chat → FastAPI (port 8000)
           └── MovieChatAgent (LangGraph ReAct agent)
                ├── Checks chat history for cached answers
                ├── Generates SQL via LLM → queries SQLite
                └── Synthesises a conversational response
```

## Prerequisites

- TMDB dataset CSV files placed in the project root:
  - `tmdb_5000_movies.csv`
  - `tmdb_5000_credits.csv`

## Quick install

Run the one-shot setup script to check prerequisites, install dependencies, create `.env`, pull the Ollama model, and verify the installation with the test suite:

```bash
./install.sh
```

| Flag | Description |
|---|---|
| `--skip-model` | Skip pulling the Ollama model |
| `--skip-tests` | Skip running the test suite |

After the script completes, continue from [step 2 (Ingest data)](#2-ingest-data).

---

## 1. Install uv and create virtual environment

Install [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create a virtual environment and install dependencies:

```bash
uv sync
```

## 2. Ingest data

Populate the SQLite database from TMDB CSV files (only needed once):

```bash
./ingest.sh
```

To use CSV files from a custom location:

```bash
./ingest.sh /path/to/tmdb_5000_movies.csv /path/to/tmdb_5000_credits.csv
```

## 3. Install Ollama and pull the model

Install [Ollama](https://ollama.com/download), then pull the model:

```bash
ollama pull qwen2.5:14b
```

Ollama must be running at `http://localhost:11434` before starting the server. To use a different model or host, create a `.env` file in the project root:

```dotenv
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
```

## 4. Start the API server

```bash
./server.sh
```

| Flag | Default | Description |
|---|---|---|
| `--host HOST` | `0.0.0.0` | Bind address |
| `--port PORT` | `8000` | Listen port |
| `--no-reload` | — | Disable hot-reload |

Once running:
- Health check: `http://localhost:8000/health`
- Interactive API docs: `http://localhost:8000/docs`

## 5. Run traces or the chat UI

### Streamlit chat UI

In a separate terminal:

```bash
./chat_ui.sh
```

| Flag | Default | Description |
|---|---|---|
| `--port PORT` | `8501` | Streamlit listen port |
| `--server-port PORT` | `8000` | API server port |

Opens at `http://localhost:8501`.

### Scripted traces

Run pre-written dialog scripts against the API to test multi-turn conversations:

```bash
./traces.sh
```

Dialog scripts live in `data/dialogs/` (YAML format).

## Running tests

```bash
uv run pytest
```

## Example traces

### Trace 1
[1/4] You: What are the top rated thriller movies in the database?
          Bot: The top-rated thriller movies in the database are Pulp Fiction (8.3) and The Dark Knight, Psycho, Inception, Se7en, The Silence of the Lambs, The Shining, Room, The Usual Suspects, Memento, and The Prestige (all with a score of 8.1 or higher).
               (intent: retrieve)

[2/4] You: Can you narrow it down to thrillers from the 2000s?
          Bot: I couldn't find any thrillers from the 2000s in your database query results. You might want to try rephrasing your search or using different keywords.
               (intent: retrieve)

[3/4] You: Who directed the highest rated one from that list?
          Bot: The highest-rated movie from the list is directed by Gary Sinyor.
               (intent: retrieve)

[4/4] You: What other movies did that director make?
          Bot: The director of "Star Wars: Episode III - Revenge of the Sith" also directed "Star Wars: Episode II - Attack of the Clones", "Star Wars: Episode I - The Phantom Menace", and "American Graffiti".
               (intent: retrieve)

### Trace 2
[1/3] You: Tell me about the movie Inception
          Bot: Inception is a movie with the tagline "Your mind is the scene of the crime." The story follows Cobb, a skilled thief who infiltrates his targets' subconscious to steal corporate secrets. He's offered a chance to regain his old life if he can perform inception, which means planting an idea into someone else's subconscious.
               (intent: retrieve)

[2/3] You: Who plays the lead role in it?
          Bot: The lead role is played by Sam Worthington.
               (intent: retrieve)

[3/3] You: What other movies has that actor starred in?
          Bot: I couldn't find any movies matching the actor you asked about. You might want to try rephrasing your question or using a different name.
               (intent: retrieve)

### Trace 3
 [1/4] You: What movies has Christopher Nolan directed?
           Bot: Christopher Nolan has directed several movies including The Dark Knight Rises, The Dark Knight, Interstellar, Inception, Batman Begins, Insomnia, The Prestige, and Memento.
                (intent: retrieve)

  [2/4] You: Which of those are sci-fi?
           Bot: Among the movies Christopher Nolan has directed, the ones that fall under the science fiction genre are "Interstellar," "Inception," and to some extent, "Tenet."
                (intent: chat)

  [3/4] You: What is the plot of Interstellar?
           Bot: I couldn't find any plot details for Interstellar in the database. You might want to try rephrasing your question or asking about a different aspect of the movie.
                (intent: retrieve)

  [4/4] You: Who are the main actors in it?
           Bot: I couldn't find any information about the main actors for that movie. You might want to try rephrasing your question or providing more details.
                (intent: retrieve)

## Limitations

As seen from the traces above the LLM refuses to answer the questions of the user.
The main cause of it CANNOT_GENERATE response from query_database_node of the Agent.
In order to fix this issue we should use deeper chain-of-thought chain which tells if the question can be answered using SQL or not.
More powerful and fresh LLM model can also help solving this problem.

There are no guardrails to prevent hallucinations so in Trace 2 it can be seen, that the model created a main actor, thou, he wasn't retrieved successfuly from the database.

## Roadmap

- [ ] Evaluations (Synthetic Traces)
- [ ] Observability (LangFuse or similar)
- [ ] Docker container
- [ ] Different SQL connectors
- [ ] Easier support for different LLM providers
- [ ] Tackle hallucinations
