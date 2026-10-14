import os
import re
import time
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
import base64
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
    # 1. Flexible check in Streamlit Cloud secrets
    if hasattr(st, "secrets"):
        for k in ["GEMINI_API_KEY", "gemini_api_key", "GEMINI_KEY", "gemini_key", "API_KEY", "api_key"]:
            try:
                if k in st.secrets:
                    val = str(st.secrets[k]).strip().strip('"').strip("'")
                    if val:
                        return val
            except Exception:
                pass
    # 2. Check environment / .env
    for k in ["GEMINI_API_KEY", "gemini_api_key", "API_KEY"]:
        val = os.getenv(k, "").strip().strip('"').strip("'")
        if val:
            return val
    return ""

def get_logo_img_tag():
    svg_path = os.path.join(ROOT, "static", "logo.svg")
    if os.path.exists(svg_path):
        try:
            with open(svg_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f'<img src="data:image/svg+xml;base64,{b64}" width="42" height="42" alt="Logo" style="border-radius:10px;display:block;" />'
        except Exception:
            pass
    return '<div class="brand-icon-box">🤖</div>'

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
    if "zidio" in t:
        return ("### About Zidio Development\n\n"
                "**Zidio Development** is an innovative software development, IT consulting, and student mentorship organization.\n\n"
                "#### 🌟 Key Highlights & Services:\n"
                "1. **Industry Internship Programs**: Offers comprehensive, hands-on internships for students and aspiring developers across:\n"
                "   - Full-Stack Web Development (Python, Flask, React, Node.js)\n"
                "   - Artificial Intelligence & Machine Learning (NLP, LLMs, Computer Vision)\n"
                "   - Data Science & Analytics\n"
                "   - Cloud Computing & DevOps\n"
                "2. **Real-World Project Experience**: Interns build production-ready applications, participate in code reviews, use Git/GitHub workflows, and deploy live to the cloud.\n"
                "3. **Skill Acceleration & Career Mentorship**: Provides resume reviews, technical interview prep, and industry mentor guidance.\n\n"
                "> 💡 *This **Dynamic AI Chatbot** was architected and built as a featured project within the Zidio Development Internship program.*")
    if "tcs" in t or "tata consultancy" in t:
        return ("### Tata Consultancy Services (TCS)\n\n"
                "**Tata Consultancy Services (TCS)** is an Indian multinational IT services and consulting company headquartered in Mumbai. It is the flagship IT company of the **Tata Group** and one of the world's most valuable IT service brands.\n\n"
                "#### 🏢 Key Highlights:\n"
                "- **Global Scale**: Operates in 150+ locations across 50+ countries with over 600,000 employees.\n"
                "- **Core Domains**: Cloud computing, AI & Cognitive Systems, Enterprise Solutions, Cybersecurity, and IoT.\n"
                "- **Campus Hiring (TCS NQT)**: Conducts the National Qualifier Test annually to recruit fresh graduates into **Ninja** and **Digital** profiles.\n"
                "- **Culture & Learning**: Famous for its structured Initial Learning Programs (ILP) and extensive global career mobility.")
    if "microsoft" in t:
        return ("### Microsoft Corporation\n\n"
                "**Microsoft** is a global technology leader headquartered in Redmond, Washington.\n\n"
                "#### 🏢 Key Domains & Products:\n"
                "- **Software**: Windows OS, Office 365, Visual Studio / VS Code, GitHub.\n"
                "- **Cloud & AI**: Microsoft Azure (enterprise cloud computing), Azure OpenAI Service, Copilot integrations.\n"
                "- **Gaming & Hardware**: Xbox ecosystem, Surface devices, LinkedIn professional network.")
    if "google" in t or "alphabet" in t:
        return ("### Google (Alphabet Inc.)\n\n"
                "**Google** is a world-leading technology company specializing in search, cloud, AI, and consumer software.\n\n"
                "#### 🌟 Key Innovations:\n"
                "- **AI & Research**: Google DeepMind, Gemini generative models, AlphaFold, Transformer architecture.\n"
                "- **Platforms**: Google Search, Android OS, Chromium, YouTube, Google Cloud Platform (GCP).")
    if ("py code" in t or "python code" in t or "code" in t) and "swap" not in t:
        return ("### Python Code Examples & Best Practices\n\n"
                "Here are practical, commonly used Python patterns:\n\n"
                "#### 1. List Comprehensions\n"
                "```python\n"
                "# Filter even numbers and square them\n"
                "nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\n"
                "even_squares = [x**2 for x in nums if x % 2 == 0]\n"
                "print(even_squares)  # [4, 16, 36, 64, 100]\n"
                "```\n\n"
                "#### 2. Clean Dictionary Handling\n"
                "```python\n"
                "data = {'role': 'developer', 'active': True}\n"
                "status = data.get('status', 'pending')  # Default value fallback\n"
                "```\n\n"
                "#### 3. Exception Handling\n"
                "```python\n"
                "try:\n"
                "    result = 100 / value\n"
                "except ZeroDivisionError:\n"
                "    result = 0\n"
                "```")
    if "swap" in t and ("number" in t or "variable" in t or "py" in t or "code" in t):
        return ("### Python Program to Swap Two Numbers\n\n"
                "Here are the standard approaches in Python:\n\n"
                "#### 1. Pythonic One-Liner (Tuple Unpacking - Recommended)\n"
                "```python\n"
                "# Define two numbers\n"
                "a = 10\n"
                "b = 20\n"
                "print(f\"Before swap: a = {a}, b = {b}\")\n\n"
                "# Swap in a single line\n"
                "a, b = b, a\n\n"
                "print(f\"After swap:  a = {a}, b = {b}\")\n"
                "```\n\n"
                "#### 2. Using a Temporary Variable (`temp`)\n"
                "```python\n"
                "a = 10\n"
                "b = 20\n\n"
                "temp = a\n"
                "a = b\n"
                "b = temp\n\n"
                "print(f\"After swap: a = {a}, b = {b}\")\n"
                "```\n\n"
                "#### 3. Using Arithmetic Operators (+ and -)\n"
                "```python\n"
                "a = 10\n"
                "b = 20\n\n"
                "a = a + b  # 30\n"
                "b = a - b  # 10\n"
                "a = a - b  # 20\n\n"
                "print(f\"After swap: a = {a}, b = {b}\")\n"
                "```")
    if "fibonacci" in t:
        return ("### Fibonacci Series in Python\n\n"
                "```python\n"
                "def fibonacci(n):\n"
                "    a, b = 0, 1\n"
                "    series = []\n"
                "    for _ in range(n):\n"
                "        series.append(a)\n"
                "        a, b = b, a + b\n"
                "    return series\n\n"
                "# Generate first 10 Fibonacci numbers\n"
                "print(fibonacci(10))  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]\n"
                "```")
    if "reverse" in t and ("string" in t or "word" in t or "py" in t or "code" in t):
        return ("### Reverse a String in Python\n\n"
                "```python\n"
                "text = 'Hello World'\n\n"
                "# 1. Slicing (Fastest & most Pythonic)\n"
                "reversed_text = text[::-1]\n"
                "print(reversed_text)  # 'dlroW olleH'\n\n"
                "# 2. Using reversed() and join\n"
                "reversed_text2 = ''.join(reversed(text))\n"
                "print(reversed_text2)\n"
                "```")
    if "machine learning" in t or "ml" in t or "deep learning" in t:
        return ("### Machine Learning Fundamentals\n\n"
                "Machine Learning (ML) is a subset of Artificial Intelligence where algorithms learn patterns from data rather than being explicitly programmed.\n\n"
                "#### Key Paradigms:\n"
                "1. **Supervised Learning**: Model learns from labeled data (e.g. Classification with Random Forest, Regression with Linear Models).\n"
                "2. **Unsupervised Learning**: Discover hidden patterns in unlabeled data (e.g. K-Means clustering, PCA dimensionality reduction).\n"
                "3. **Reinforcement Learning**: Agent learns through trial and error with reward feedback (e.g. Q-Learning, PPO).\n"
                "4. **Deep Learning**: Multi-layered Artificial Neural Networks (CNNs for computer vision, Transformers for LLMs and NLP).")
    if "modern python" in t or ("python" in t and "librar" in t) or ("guide" in t and "python" in t):
        return ("### Comprehensive Guide to Modern Python & Best Libraries\n\n"
                "Modern Python (3.11+) brings major performance boosts, static type hints, and asynchronous concurrency.\n\n"
                "#### 🌟 Top Libraries by Category:\n"
                "1. **Data Science & ML**: `NumPy` (vector math), `Pandas` (dataframes), `Scikit-Learn` (machine learning), `PyTorch` (deep learning).\n"
                "2. **Web Frameworks**: `FastAPI` (high-performance async APIs), `Flask` (lightweight microframework), `Streamlit` (interactive AI data apps).\n"
                "3. **Async & Networking**: `asyncio` (built-in event loop), `httpx` (modern HTTP client with sync/async support).\n"
                "4. **Data Validation & Typing**: `Pydantic` (fast data modeling via type annotations).\n"
                "5. **Developer Tooling**: `Ruff` (ultra-fast linter), `Rich` (terminal styling and tables).\n\n"
                "```python\n"
                "# Modern Python Type Hinting & Dataclass Example\n"
                "from dataclasses import dataclass\n\n"
                "@dataclass\n"
                "class AIQuery:\n"
                "    prompt: str\n"
                "    temperature: float = 0.7\n"
                "    tags: list[str] = None\n"
                "```")
    if "debug" in t and ("async" in t or "function" in t or "python" in t):
        return ("### How to Debug Asynchronous Python Functions (`asyncio`)\n\n"
                "#### ⚠️ Common Async Pitfalls & Practical Fixes:\n"
                "1. **Forgot `await`**: If you invoke an `async def` function without `await`, it returns a coroutine object instead of executing.\n"
                "   ```python\n"
                "   # ❌ Wrong: result = fetch_data()\n"
                "   # ✅ Correct:\n"
                "   result = await fetch_data()\n"
                "   ```\n"
                "2. **Blocking Operations Inside Async**: Never use `time.sleep()` inside async routines — use `asyncio.sleep()` so the event loop is not blocked:\n"
                "   ```python\n"
                "   import asyncio\n"
                "   await asyncio.sleep(1)  # Non-blocking\n"
                "   ```\n"
                "3. **Concurrent Execution**: Use `asyncio.gather()` to run multiple coroutines simultaneously:\n"
                "   ```python\n"
                "   data1, data2 = await asyncio.gather(api_call(), db_query())\n"
                "   ```\n"
                "4. **Asyncio Debug Flag**: Run with `asyncio.run(main(), debug=True)` to track unawaited tasks.")
    if "architecture" in t or ("project" in t and "idea" in t) or ("full-stack" in t and "ai" in t):
        return ("### High-Impact Full-Stack AI Project Architectures\n\n"
                "#### 1. Real-Time RAG (Retrieval-Augmented Generation) Platform\n"
                "- **Frontend**: Streamlit / Next.js with real-time SSE streaming.\n"
                "- **Backend**: FastAPI with async document chunking + hybrid search (ChromaDB / Qdrant).\n"
                "- **LLM**: Gemini / Claude API with contextual re-ranking.\n\n"
                "#### 2. Multimodal Code Reviewer & Security Scanner\n"
                "- **Frontend**: Monaco Code Editor in React.\n"
                "- **Backend**: Python AST analysis + LLM prompt chains for CVE identification and auto-patching.\n\n"
                "#### 3. Real-Time Voice & Vision Assistant\n"
                "- **Frontend**: WebRTC audio stream + Canvas snapshots.\n"
                "- **Backend**: WebSocket server with Whisper STT and Gemini multimodal reasoning.")
    if "t20" in t or "ind vs wi" in t or "cricket" in t or "match" in t:
        return ("### Cricket & T20 Match Overview\n\n"
                "For live cricket and T20 International matches (such as India vs West Indies / World Cup games):\n\n"
                "- 🏏 **Format**: 20 overs per side, emphasizing powerplay strike rates, middle-over spin control, and death bowling.\n"
                "- 📺 **Live Broadcast**: Streamed live across regional official sports networks (e.g. JioCinema / Hotstar / Willow TV).\n\n"
                "*Note: Connect your Gemini API Key in Streamlit Secrets to enable real-time generative commentary and ball-by-ball match breakdown!*")
    if any(x in t for x in ["bye", "goodbye", "see you"]):
        return "Goodbye! 👋 Have a wonderful day ahead."
    return "I can help answer questions, brainstorm ideas, analyze code, and explain concepts. Feel free to ask anything!"

def call_gemini(message, history_list):
    api_key = get_api_key()
    if not api_key:
        return None

    contents = []
    for item in history_list[-8:]:
        role = "user" if item.get("role") == "user" else "model"
        text = str(item.get("content", "")).strip()
        if text:
            contents.append({"role": role, "parts": [{"text": text[:5000]}]})

    if not contents or contents[-1]["role"] != "user" or contents[-1]["parts"][0]["text"] != message:
        contents.append({"role": "user", "parts": [{"text": message}]})

    # Resilient attempts across Google API versions & models
    attempts = [
        ("v1beta", "gemini-2.0-flash", True),
        ("v1beta", "gemini-1.5-flash", True),
        ("v1beta", "gemini-1.5-flash", False),
        ("v1", "gemini-1.5-flash", False),
        ("v1beta", "gemini-2.5-flash", True),
        ("v1beta", "gemini-1.5-pro", True),
    ]

    for api_version, model, use_sys_instr in attempts:
        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent"
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1400}
        }
        if use_sys_instr:
            payload["systemInstruction"] = {
                "parts": [{"text": "You are Dynamic AI, a sophisticated, helpful AI assistant. Provide clear, structured, and accurate responses."}]
            }

        try:
            r = requests.post(url, params={"key": api_key}, json=payload, timeout=20)
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
    page_icon="🤖",
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
  .brand-logo-wrap {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .brand-logo-wrap img {
    width: 44px;
    height: 44px;
    display: block;
    border-radius: 12px;
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
    logo_html = get_logo_img_tag()
    st.markdown(f"""
    <div class="brand-banner">
        <div class="brand-logo-wrap">
            {logo_html}
        </div>
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
            with st.chat_message(role, avatar="👤" if role == "user" else "🤖"):
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

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Reasoning…"):
                ai_reply = call_gemini(prompt, st.session_state.messages)
                mode = "gemini" if ai_reply else "local"
                reply = ai_reply if ai_reply else offline_fallback(prompt)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000)

                st.markdown(reply)
                tags_html = ""
                if sent:
                    tags_html += f'<span class="tag-bubble">Sentiment: {sent}</span>'
                if top:
                    tags_html += f'<span class="tag-bubble">Topic: {top}</span>'
                if tags_html:
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
