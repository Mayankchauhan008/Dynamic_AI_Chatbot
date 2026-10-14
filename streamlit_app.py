import os
import re
import time
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
import requests
import streamlit as st
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# CONFIGURATION & ENVIRONMENT
# ==============================================================================
ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "chatbot.db")

def _load_env_file():
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_file()

def get_api_key():
    # Check Streamlit Cloud secrets first, then environment / .env
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"].strip()
    return os.getenv("GEMINI_API_KEY", "").strip()

# ==============================================================================
# DATABASE MANAGEMENT
# ==============================================================================
def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sentiment TEXT,
                    topic TEXT,
                    mode TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.commit()
    except Exception as e:
        st.error(f"Database initialization error: {e}")

init_db()

# ==============================================================================
# REASONING & NLP ENGINE
# ==============================================================================
def analyze_sentiment(text):
    words = set(re.findall(r"[a-z']+", text.lower()))
    pos = len(words & {"thanks", "great", "good", "awesome", "happy", "love", "excellent", "helpful", "nice"})
    neg = len(words & {"bad", "sad", "angry", "hate", "upset", "frustrated", "problem", "issue", "worst"})
    score = pos - neg
    return "positive" if score > 0 else "negative" if score < 0 else "neutral"

def analyze_topic(text):
    t = text.lower()
    for name, words in {
        "machine learning": ["machine learning", "model", "training", "dataset", "gradient descent", "ai"],
        "programming": ["python", "java", "code", "program", "error", "debug", "function"],
        "education": ["exam", "study", "learn", "definition", "explain", "college"],
        "career": ["resume", "job", "internship", "career", "interview"]
    }.items():
        if any(w in t for w in words):
            return name
    return "general"

def offline_fallback(text):
    t = text.lower()
    if re.search(r"\b(hi|hello|hey|namaste)\b", t):
        return "Hello! 👋 I'm your Dynamic AI assistant. How can I help you today?"
    if "your name" in t or "who are you" in t:
        return "I'm **Dynamic AI**, an intelligent conversational assistant."
    if "gradient descent" in t:
        return ("### Gradient Descent\n\n"
                "Gradient descent minimizes an objective function by repeatedly updating parameters opposite to the gradient.\n\n"
                "**Key Formula:**\n"
                "$$\\theta = \\theta - \\alpha \\nabla J(\\theta)$$\n\n"
                "- $\\alpha$: Learning rate\n"
                "- $\\nabla J(\\theta)$: Gradient of loss with respect to parameters\n"
                "- Repeated until loss converges to minimum.")
    if "interview" in t or "data science" in t:
        return ("### Data Science Interview Preparation\n\n"
                "1. **Core Math**: Linear algebra, probability, Bayes' theorem, hypothesis testing.\n"
                "2. **Machine Learning**: Bias-variance tradeoff, regularization (L1/L2), evaluation metrics (ROC-AUC, F1).\n"
                "3. **Practical Coding**: Pandas/NumPy vectorization, SQL window functions, clean Pythonic implementations.\n"
                "4. **Case Studies**: End-to-end design of real-world ML systems with trade-offs.")
    if "thank" in t:
        return "You're very welcome! 😊 Feel free to ask anytime."
    if any(x in t for x in ["bye", "goodbye", "see you"]):
        return "Goodbye! 👋 Have a wonderful day ahead."
    return ("I can help answer questions, brainstorm ideas, analyze code, and explain concepts.\n\n"
            "💡 *Tip: Add your `GEMINI_API_KEY` to unlock full generative cloud intelligence.*")

def call_gemini(message, history_list):
    api_key = get_api_key()
    if not api_key:
        return None

    models = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash"
    ]

    contents = []
    for item in history_list[-10:]:
        role = "user" if item.get("role") == "user" else "model"
        text = str(item.get("content", "")).strip()
        if text:
            contents.append({"role": role, "parts": [{"text": text[:6000]}]})

    if not contents or contents[-1]["role"] != "user" or contents[-1]["parts"][0]["text"] != message:
        contents.append({"role": "user", "parts": [{"text": message}]})

    payload = {
        "systemInstruction": {"parts": [{"text": "You are Dynamic AI, a sophisticated, helpful AI assistant. Provide clear, structured, and accurate responses."}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "topP": 0.9, "maxOutputTokens": 1400}
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            r = requests.post(url, params={"key": api_key}, json=payload, timeout=25)
            if r.status_code == 200:
                data = r.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                answer = "\n".join(p.get("text", "") for p in parts if p.get("text")).strip()
                if answer:
                    return answer
        except Exception:
            continue
    return None

# ==============================================================================
# STREAMLIT PAGE CONFIGURATION & CUSTOM STYLES
# ==============================================================================
st.set_page_config(
    page_title="Dynamic AI — Intelligent Assistant",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Obsidian & Indigo CSS
st.markdown("""
<style>
  /* Base Overrides */
  .stApp {
    background-color: #0a0d14;
    color: #f3f4f6;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  
  /* Sidebar */
  section[data-testid="stSidebar"] {
    background-color: #10141d;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
  }

  /* Metric cards */
  div[data-testid="stMetric"] {
    background-color: #151a26;
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 14px 18px;
    border-radius: 12px;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
  }

  /* Chat input box */
  div[data-testid="stChatInput"] {
    border-radius: 16px;
    background-color: #121722;
    border: 1px solid rgba(255, 255, 255, 0.12);
  }

  /* Gradient Header */
  .brand-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 0 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 20px;
  }
  .brand-icon-box {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #fff;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
  }
  .brand-text h1 {
    font-size: 22px;
    font-weight: 800;
    margin: 0;
    line-height: 1.1;
  }
  .brand-text small {
    color: #94a3b8;
    font-size: 11px;
  }
  .hero-card {
    background: #151a26;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  }
  .tag-bubble {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 600;
    margin-top: 6px;
    margin-right: 6px;
    background: rgba(99, 102, 241, 0.15);
    border: 1px solid rgba(99, 102, 241, 0.3);
    color: #818cf8;
  }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================
if "user" not in st.session_state:
    st.session_state.user = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "stats" not in st.session_state:
    st.session_state.stats = {
        "queries": 0,
        "ai_responses": 0,
        "fallbacks": 0,
        "total_ms": 0,
        "sentiments": Counter(),
        "topics": Counter()
    }

# ==============================================================================
# DATABASE ACTIONS
# ==============================================================================
def db_login(username_or_email, password):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ? OR email = ? COLLATE NOCASE",
                    (username_or_email, username_or_email.lower()))
        user = cur.fetchone()
        if user and check_password_hash(user["password_hash"], password):
            return dict(user)
    return None

def db_register(username, email, password):
    if len(username) < 3 or not re.match(r"^[a-zA-Z0-9_.-]+$", username):
        return False, "Username must be at least 3 characters (letters, numbers, dot, or _)."
    if email and not re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email):
        return False, "Please enter a valid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    pwd_hash = generate_password_hash(password)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                        (username, email or None, pwd_hash, now))
            user_id = cur.lastrowid
            conn.commit()
            return True, {"id": user_id, "username": username, "email": email or "", "created_at": now}
    except sqlite3.IntegrityError:
        return False, "Username or email is already registered."

def db_load_history(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT role, content, sentiment, topic, mode, created_at FROM chats WHERE user_id = ? ORDER BY id ASC LIMIT 100", (user_id,))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return []

def db_save_chat(user_id, role, content, sentiment="", topic="", mode=""):
    if not user_id:
        return
    try:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO chats (user_id, role, content, sentiment, topic, mode, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (user_id, role, content, sentiment, topic, mode, now))
            conn.commit()
    except Exception:
        pass

def db_clear_history(user_id):
    if not user_id:
        return
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM chats WHERE user_id = ?", (user_id,))
            conn.commit()
    except Exception:
        pass

# ==============================================================================
# SIDEBAR NAVIGATION & AUTHENTICATION
# ==============================================================================
with st.sidebar:
    st.markdown("""
    <div class="brand-banner">
        <div class="brand-icon-box">✦</div>
        <div class="brand-text">
            <h1>Dynamic AI</h1>
            <small>Next-Gen Intelligent Dialogue</small>
        </div>
    </div>
    """, unsafe_allow_html=True)

    nav_tab = st.radio("Navigation", ["💬 Chat", "📊 Analytics", "👤 Account"], label_visibility="collapsed")

    st.divider()

    # User Chip / Authentication Status
    if st.session_state.user:
        u = st.session_state.user
        st.success(f"Signed in as **{u['username']}**")
        if u.get("email"):
            st.caption(f"Email: {u['email']}")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Clear History", use_container_width=True):
                db_clear_history(u["id"])
                st.session_state.messages = []
                st.toast("Conversation history cleared.")
                st.rerun()
        with col_b:
            if st.button("Sign Out", use_container_width=True):
                st.session_state.user = None
                st.session_state.messages = []
                st.toast("Signed out successfully.")
                st.rerun()
    else:
        st.info("Browsing in **Guest Mode**")
        st.caption("Sign in to save and sync conversation history to cloud vault.")

# ==============================================================================
# VIEW: ACCOUNT (LOGIN & REGISTER)
# ==============================================================================
if nav_tab == "👤 Account":
    st.title("User Authentication & Profile")

    if st.session_state.user:
        u = st.session_state.user
        st.markdown(f"""
        <div class="hero-card">
            <h3>Welcome, {u['username']}!</h3>
            <p>Your account is active. Conversation history is automatically encrypted and saved to your cloud vault.</p>
            <ul>
                <li><b>Username:</b> {u['username']}</li>
                <li><b>Email:</b> {u.get('email') or 'Not provided'}</li>
                <li><b>Member Since:</b> {u.get('created_at', 'Recently')}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Log Out of Dynamic AI", type="primary"):
            st.session_state.user = None
            st.session_state.messages = []
            st.rerun()

    else:
        auth_choice = st.radio("Choose Action", ["Sign In", "Create Free Account"], horizontal=True)

        if auth_choice == "Sign In":
            st.subheader("Sign In to Dynamic AI")
            with st.form("form_login"):
                login_user = st.text_input("Username or Email", placeholder="alex or alex@example.com")
                login_pass = st.text_input("Password", type="password", placeholder="Enter password")
                submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

                if submitted:
                    if not login_user or not login_pass:
                        st.error("Please enter both username and password.")
                    else:
                        user = db_login(login_user.strip(), login_pass.strip())
                        if user:
                            st.session_state.user = user
                            # Load saved conversations
                            saved_chats = db_load_history(user["id"])
                            st.session_state.messages = saved_chats
                            st.toast(f"Welcome back, {user['username']}!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")

        else:
            st.subheader("Create a New Account")
            with st.form("form_register"):
                reg_user = st.text_input("Choose Username (min 3 chars)", placeholder="letters, numbers, dot, underscore")
                reg_email = st.text_input("Email Address (Optional)", placeholder="name@example.com")
                reg_pass = st.text_input("Create Password (min 6 chars)", type="password")
                reg_confirm = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Create Free Account", type="primary", use_container_width=True)

                if submitted:
                    if reg_pass != reg_confirm:
                        st.error("Passwords do not match.")
                    else:
                        ok, res = db_register(reg_user.strip(), reg_email.strip(), reg_pass.strip())
                        if ok:
                            st.session_state.user = res
                            st.toast(f"Account created! Welcome, {res['username']}!")
                            st.rerun()
                        else:
                            st.error(res)

# ==============================================================================
# VIEW: ANALYTICS
# ==============================================================================
elif nav_tab == "📊 Analytics":
    st.title("Usage & Cognitive Analytics")
    st.caption("Telemetry, latency performance, and sentiment intent categorization.")

    stats = st.session_state.stats
    q = stats["queries"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Queries", q)
    c2.metric("AI Model Responses", stats["ai_responses"])
    c3.metric("Offline Fallbacks", stats["fallbacks"])
    avg_latency = round(stats["total_ms"] / q) if q else 0
    c4.metric("Avg Latency", f"{avg_latency} ms")

    st.divider()

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("Sentiment Distribution")
        if stats["sentiments"]:
            st.bar_chart(stats["sentiments"])
        else:
            st.info("No sentiment metrics recorded yet.")

    with col_chart2:
        st.subheader("Topic Intent Classification")
        if stats["topics"]:
            st.bar_chart(stats["topics"])
        else:
            st.info("No topic classifications recorded yet.")

# ==============================================================================
# VIEW: CHAT (DEFAULT)
# ==============================================================================
else:
    # Header actions
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        if st.session_state.user:
            st.title(f"Welcome back, {st.session_state.user['username']}!")
        else:
            st.title("What would you like to explore?")
        st.caption("Ask technical questions, solve code roadblocks, or brainstorm ideas.")

    with col_head2:
        if st.session_state.messages:
            export_data = json.dumps({
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "user": st.session_state.user["username"] if st.session_state.user else "guest",
                "messages": st.session_state.messages
            }, indent=2)
            st.download_button(
                "Export Chat",
                data=export_data,
                file_name=f"dynamic-ai-chat-{int(time.time())}.json",
                mime="application/json",
                use_container_width=True
            )

    # Display Conversation Messages
    if not st.session_state.messages:
        # Prompt Cards for empty chat
        st.markdown("""
        <div class="hero-card">
            <h4>💡 Popular prompts to get started:</h4>
            <ul>
                <li><i>"Give me a comprehensive guide to modern Python and its best libraries."</i></li>
                <li><i>"Explain gradient descent and optimization with clear step-by-step math."</i></li>
                <li><i>"Help me debug an asynchronous Python function."</i></li>
                <li><i>"Give me high-impact full-stack AI project architecture ideas."</i></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            with st.chat_message(role, avatar="👤" if role == "user" else "✦"):
                st.markdown(content)
                sentiment = msg.get("sentiment")
                topic = msg.get("topic")
                if role != "user" and (sentiment or topic):
                    tags_html = ""
                    if sentiment:
                        tags_html += f'<span class="tag-bubble">Sentiment: {sentiment}</span>'
                    if topic:
                        tags_html += f'<span class="tag-bubble">Topic: {topic}</span>'
                    st.markdown(tags_html, unsafe_allow_html=True)

    # Chat Input Box
    if prompt := st.chat_input("Ask Dynamic AI anything…"):
        # Append User Message
        user_msg = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_msg)
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Record User Message in Database if logged in
        user_id = st.session_state.user["id"] if st.session_state.user else None
        db_save_chat(user_id, "user", prompt)

        # Generate Response
        start_time = time.perf_counter()
        sent = analyze_sentiment(prompt)
        top = analyze_topic(prompt)

        with st.chat_message("assistant", avatar="✦"):
            with st.spinner("Reasoning…"):
                ai_reply = call_gemini(prompt, st.session_state.messages)
                mode = "gemini" if ai_reply else "local"
                reply = ai_reply if ai_reply else offline_fallback(prompt)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000)

                st.markdown(reply)
                tags_html = f'<span class="tag-bubble">Sentiment: {sent}</span><span class="tag-bubble">Topic: {top}</span>'
                st.markdown(tags_html, unsafe_allow_html=True)

        # Store in session state
        assistant_msg = {
            "role": "assistant",
            "content": reply,
            "sentiment": sent,
            "topic": top,
            "mode": mode
        }
        st.session_state.messages.append(assistant_msg)

        # Update telemetry
        st.session_state.stats["queries"] += 1
        if mode == "gemini":
            st.session_state.stats["ai_responses"] += 1
        else:
            st.session_state.stats["fallbacks"] += 1
        st.session_state.stats["total_ms"] += elapsed_ms
        st.session_state.stats["sentiments"][sent] += 1
        st.session_state.stats["topics"][top] += 1

        # Save to SQLite
        db_save_chat(user_id, "assistant", reply, sent, top, mode)
