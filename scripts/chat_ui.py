"""
Streamlit chat interface for the Turbo-Noodle Movie AI Agent.

Usage:
    uv run streamlit run scripts/chat_ui.py

Expects the FastAPI server to be running on http://localhost:8000.
"""

import html
import os
import uuid
import requests
import streamlit as st

# ── Config ──────────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("CHAT_API_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

st.set_page_config(
    page_title="🍿 Movie AI Agent",
    page_icon="🎬",
    layout="centered",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        min-height: 100vh;
    }

    /* Header */
    .movie-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    .movie-header h1 {
        font-size: 2.6rem;
        font-weight: 700;
        background: linear-gradient(90deg, #f7971e, #ffd200);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .movie-header p {
        color: #a0aec0;
        font-size: 1rem;
    }

    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    .status-online  { background: rgba(72,187,120,0.15); color: #48bb78; border: 1px solid rgba(72,187,120,0.3); }
    .status-offline { background: rgba(245,101,101,0.15); color: #f56565; border: 1px solid rgba(245,101,101,0.3); }

    /* Chat bubbles */
    .chat-bubble {
        display: flex;
        margin-bottom: 1.2rem;
        gap: 12px;
        animation: fadeSlideIn 0.3s ease;
    }
    @keyframes fadeSlideIn {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .chat-bubble.user  { flex-direction: row-reverse; }
    .avatar {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    .avatar.user-av  { background: linear-gradient(135deg, #f7971e, #ffd200); }
    .avatar.agent-av { background: linear-gradient(135deg, #667eea, #764ba2); }
    .bubble-content {
        max-width: 75%;
        padding: 0.85rem 1.1rem;
        border-radius: 16px;
        line-height: 1.6;
        font-size: 0.95rem;
        word-break: break-word;
    }
    .bubble-content.user-bubble {
        background: linear-gradient(135deg, #f7971e, #ffd200);
        color: #1a1a2e;
        border-bottom-right-radius: 4px;
        font-weight: 500;
    }
    .bubble-content.agent-bubble {
        background: rgba(255,255,255,0.07);
        color: #e2e8f0;
        border: 1px solid rgba(255,255,255,0.1);
        border-bottom-left-radius: 4px;
        backdrop-filter: blur(8px);
    }
    .intent-tag {
        display: inline-block;
        margin-top: 6px;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        background: rgba(102,126,234,0.25);
        color: #a78bfa;
        border: 1px solid rgba(102,126,234,0.3);
    }

    /* Input area */
    div[data-testid="stChatInput"] textarea {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        color: #374151 !important;
        border-radius: 12px !important;
        font-family: 'Inter', sans-serif !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder {
        color: #718096 !important;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Helpers ──────────────────────────────────────────────────────────────────
def check_health() -> bool:
    """Return True if the FastAPI server is reachable and healthy."""
    try:
        r = requests.get(HEALTH_ENDPOINT, timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def send_message(query: str) -> dict:
    """POST a chat query to the API and return the parsed JSON response."""
    payload = {"query": query, "session_id": st.session_state.session_id}
    r = requests.post(CHAT_ENDPOINT, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def render_message(role: str, content: str, intent: str | None = None):
    """Render a chat bubble for the given role ('user' or 'agent'), escaping HTML content."""
    safe_content = html.escape(content)
    if role == "user":
        st.markdown(
            f"""
            <div class="chat-bubble user">
                <div class="avatar user-av">🙋</div>
                <div class="bubble-content user-bubble">{safe_content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        intent_html = (
            f'<div class="intent-tag">⚡ {html.escape(intent)}</div>' if intent else ""
        )
        st.markdown(
            f"""
            <div class="chat-bubble agent">
                <div class="avatar agent-av">🎬</div>
                <div class="bubble-content agent-bubble">
                    {safe_content}
                    {intent_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="movie-header">
        <h1>🎬 Movie AI Agent</h1>
        <p>Ask me anything about movies — cast, directors, box office, genres and more.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Server status
online = check_health()
badge_cls = "status-online" if online else "status-offline"
badge_dot = "🟢" if online else "🔴"
badge_txt = "API online" if online else "API offline — start the server"
st.markdown(
    f'<div style="text-align:center"><span class="status-badge {badge_cls}">'
    f"{badge_dot} {badge_txt}</span></div>",
    unsafe_allow_html=True,
)

st.divider()

# ── Chat history ─────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    render_message(msg["role"], msg["content"], msg.get("intent"))

# ── Input ────────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about a movie…", disabled=not online):
    # Append & render user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    render_message("user", prompt)

    # Call API
    with st.spinner("Thinking…"):
        try:
            response = send_message(prompt)
            reply = response.get("reply", "Sorry, I didn't get a response.")
            intent = response.get("intent")
        except requests.exceptions.ConnectionError:
            reply = "⚠️ Cannot reach the API server. Make sure it is running on `localhost:8000`."
            intent = None
        except Exception as e:
            reply = f"⚠️ Unexpected error: {e}"
            intent = None

    # Append & render agent message
    st.session_state.messages.append(
        {"role": "agent", "content": reply, "intent": intent}
    )
    render_message("agent", reply, intent)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Session")
    st.code(st.session_state.session_id, language=None)
    st.caption("Each session maintains its own conversation history on the server.")

    st.markdown("---")
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.markdown("---")
    st.markdown("### 💡 Example queries")
    examples = [
        "What are the top rated sci-fi movies?",
        "Who directed Inception?",
        "Show me movies with Tom Hanks",
        "What's the highest grossing movie ever?",
        "Recommend a thriller from the 90s",
    ]
    for ex in examples:
        st.markdown(f"- _{ex}_")
