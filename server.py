import os, re, time, sqlite3
from collections import Counter
from datetime import datetime, timezone, timedelta
import requests
from flask import Flask, jsonify, request, send_from_directory, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")
DB_PATH = os.path.join(ROOT, "chatbot.db")

# Native .env loader (loads environment variables without requiring python-dotenv)
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

app = Flask(__name__, static_folder=STATIC, static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY", "dynamic-ai-secure-secret-key-2026")
app.permanent_session_lifetime = timedelta(days=30)

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
        print(f"[Database Error] Could not initialize database: {e}")

init_db()

_DETECTED_MODEL = None


def get_api_config():
    _load_env_file()
    key = os.getenv("GEMINI_API_KEY", "AIzaSyCfqf3DBB8D221yBkeDTM_yPw3XrSDo--I").strip()
    model = os.getenv("GEMINI_MODEL", "").strip()
    return key, model

def get_supported_model(api_key):
    global _DETECTED_MODEL
    if _DETECTED_MODEL:
        return _DETECTED_MODEL
    _DETECTED_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    return _DETECTED_MODEL



stats = {"messages": 0, "ai_responses": 0, "fallback_responses": 0, "total_ms": 0,
         "sentiments": Counter(), "topics": Counter(), "started_at": datetime.now(timezone.utc).isoformat()}



def sentiment(text):
    words = set(re.findall(r"[a-z']+", text.lower()))
    score = len(words & {"thanks","great","good","awesome","happy","love","excellent","helpful","nice"}) - len(words & {"bad","sad","angry","hate","upset","frustrated","problem","issue","worst"})
    return "positive" if score > 0 else "negative" if score < 0 else "neutral"

def topic(text):
    t = text.lower()
    for name, words in {
        "machine learning": ["machine learning","model","training","dataset","gradient descent"],
        "programming": ["python","java","code","program","error","debug"],
        "education": ["exam","study","learn","definition","explain","college"],
        "career": ["resume","job","internship","career","interview"]
    }.items():
        if any(w in t for w in words): return name
    return "general"

def fallback(text):
    t = text.lower()
    if re.search(r"\b(hi|hello|hey|namaste)\b", t):
        return "Hello! 👋 I'm your Dynamic AI Chatbot. What would you like help with today?"
    if "your name" in t or "who are you" in t:
        return "I'm Dynamic AI Chatbot, built with Flask, JavaScript, and optional Gemini AI."
    if "gradient descent" in t:
        return ("Gradient descent minimizes a loss function by repeatedly updating parameters opposite to the gradient.\n\n"
                "**Key Steps:**\n"
                "1. Initialize parameters (weights and biases)\n"
                "2. Calculate gradients of the loss with respect to parameters\n"
                "3. Update parameters using learning rate: θ = θ - α · ∇J(θ)\n"
                "4. Repeat until convergence")
    if "optimization" in t:
        return ("Optimization means finding the best solution under given constraints.\n\n"
                "Common types include:\n"
                "- **Linear Optimization**: Linear objective and constraints (Simplex algorithm)\n"
                "- **Non-linear Optimization**: Gradient-based methods (Adam, SGD, Newton-Raphson)\n"
                "- **Integer & Convex Optimization**: Widely used in operations research and machine learning.")
    if "debug" in t or "python error" in t:
        return ("Here is a practical guide to debug Python errors:\n\n"
                "1. **Read the traceback**: Check the bottom-most line to identify the exact error (e.g. `KeyError`, `IndexError`, `AttributeError`) and the file/line number.\n"
                "2. **Verify variable types**: Use `type(var)` and `print(repr(var))` to confirm unexpected values or `None`.\n"
                "3. **Use breakpoints**: Add `breakpoint()` to start the interactive `pdb` debugger.\n"
                "4. **Check environment**: Ensure required dependencies are installed in your active virtual environment.")
    if "interview" in t or "data science" in t:
        return ("Here is a roadmap for Data Science interview preparation:\n\n"
                "1. **Statistics & Math**: Probability distributions, hypothesis testing, p-values, Bayes' theorem.\n"
                "2. **Core ML Algorithms**: Supervised vs unsupervised methods, bias-variance tradeoff, regularization (L1/L2), evaluation metrics (ROC-AUC, F1).\n"
                "3. **Practical Coding**: Data manipulation in Pandas/NumPy, SQL queries (joins, window functions), clean Python.\n"
                "4. **System & Projects**: Prepare to discuss past ML projects end-to-end, including data cleaning, validation, and business impact.")
    if "machine learning" in t or "ml project" in t or "ideas" in t or "project" in t:
        return ("Here are high-impact Machine Learning project ideas:\n\n"
                "1. **Customer Churn Predictor**: Tabular classification with XGBoost and SHAP explainability.\n"
                "2. **Document QA with RAG**: Vector search (FAISS/Chroma) + LLM embeddings for PDF analysis.\n"
                "3. **Real-time Object Detection**: Computer vision with YOLOv8 on custom video streams.\n"
                "4. **Sentiment & Aspect Mining**: Fine-tuned Transformer (BERT/RoBERTa) on user feedback.")
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
    if "thank" in t: return "You're welcome! 😊 What else can I help with?"
    if any(x in t for x in ["bye", "goodbye", "see you"]): return "Goodbye! 👋 Have a great day."
    return ("I can help explain concepts, answer questions, brainstorm, and assist with programming.\n\n"
            "💡 *Tip: Configure your `GEMINI_API_KEY` in `.env` to unlock live generative responses.*")

def ask_gemini(message, history):
    api_key, _ = get_api_config()
    if not api_key: return None

    # Try verified active models in order of speed and availability
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-flash-latest"
    ]

    contents = []
    for item in history[-12:]:
        role, text = item.get("role"), str(item.get("content", "")).strip()
        if role in ("user", "model") and text:
            contents.append({"role": role, "parts": [{"text": text[:6000]}]})
    if not contents or contents[-1]["role"] != "user" or contents[-1]["parts"][0]["text"] != message:
        contents.append({"role": "user", "parts": [{"text": message}]})
    payload = {
      "systemInstruction": {"parts": [{"text": "You are a friendly, helpful AI assistant. Explain clearly with well-structured answers."}]},
      "contents": contents,
      "generationConfig": {"temperature": 0.7, "topP": 0.9, "maxOutputTokens": 1200}
    }

    last_error = None
    for model in models_to_try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            r = requests.post(api_url, params={"key": api_key}, json=payload, timeout=25)
            if r.status_code == 200:
                data = r.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                answer = "\n".join(p.get("text", "") for p in parts if p.get("text")).strip()
                if answer:
                    return answer
            else:
                print(f"[Gemini Notice] Model {model} returned status {r.status_code}: {r.text[:100]}")
        except requests.RequestException as e:
            last_error = e
            continue

    if last_error:
        print(f"[Gemini Error] All models failed. Last error: {last_error}")
    return None

@app.get("/")
def home():
    return send_from_directory(STATIC, "index.html")

@app.get("/login")
def login_page():
    if session.get("user"):
        return redirect("/")
    return send_from_directory(STATIC, "login.html")

@app.get("/register")
def register_page():
    if session.get("user"):
        return redirect("/")
    return send_from_directory(STATIC, "login.html")

@app.get("/favicon.ico")
def favicon():
    return send_from_directory(STATIC, "logo.svg", mimetype="image/svg+xml")

@app.get("/api/health")
def health():
    key, _ = get_api_config()
    return jsonify(status="ok", ai_configured=bool(key), model="gemini-3.6-flash")


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message: return jsonify(error="Please enter a message."), 400
    if len(message) > 6000: return jsonify(error="Message too long (maximum 6000 characters)."), 413
    history = data.get("history", [])
    if not isinstance(history, list): history = []
    start = time.perf_counter()
    sent, top = sentiment(message), topic(message)
    used_ai = False
    try:
        answer = ask_gemini(message, history)
        if answer:
            used_ai = True
        else:
            answer = fallback(message)
    except requests.RequestException as e:
        print(f"[Gemini API Notice] Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                err_detail = e.response.json().get('error', {}).get('message', e.response.text)
                print(f"[Gemini API Details] {err_detail}")
            except Exception:
                pass
        answer = fallback(message)
    except (ValueError, KeyError, TypeError) as e:
        print(f"[Gemini API Notice] Processing error: {e}")
        answer = fallback(message)
    elapsed = round((time.perf_counter() - start) * 1000)
    stats["messages"] += 1
    stats["ai_responses" if used_ai else "fallback_responses"] += 1
    stats["total_ms"] += elapsed
    stats["sentiments"][sent] += 1
    stats["topics"][top] += 1

    # Save to database if user is logged in
    user = session.get("user")
    if user and user.get("id"):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                now_str = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    "INSERT INTO chats (user_id, role, content, sentiment, topic, mode, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user["id"], "user", message, sent, top, "user", now_str)
                )
                cursor.execute(
                    "INSERT INTO chats (user_id, role, content, sentiment, topic, mode, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user["id"], "assistant", answer, sent, top, "gemini" if used_ai else "local", now_str)
                )
                conn.commit()
        except Exception as e:
            print(f"[Database Notice] Error saving message: {e}")

    return jsonify(reply=answer, sentiment=sent, topic=top, response_ms=elapsed, mode="gemini" if used_ai else "local")

# ==============================================================================
# AUTHENTICATION & USER PROFILE ENDPOINTS
# ==============================================================================

@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()
    remember = bool(data.get("remember", True))

    if not username or len(username) < 3:
        return jsonify(error="Username must be at least 3 characters long."), 400
    if len(username) > 30:
        return jsonify(error="Username cannot exceed 30 characters."), 400
    if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
        return jsonify(error="Username can only contain letters, numbers, dots, and underscores."), 400
    if email and not re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email):
        return jsonify(error="Please provide a valid email address."), 400
    if not password or len(password) < 6:
        return jsonify(error="Password must be at least 6 characters long."), 400

    pwd_hash = generate_password_hash(password)
    now = datetime.now(timezone.utc).isoformat()

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (username, email or None, pwd_hash, now)
            )
            user_id = cursor.lastrowid
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="Username or email already registered. Please sign in or choose another."), 409

    session.permanent = remember
    session["user"] = {
        "id": user_id,
        "username": username,
        "email": email or "",
        "created_at": now
    }
    return jsonify(status="ok", user=session["user"], stats={"chat_count": 0})

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username_or_email = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    remember = bool(data.get("remember", True))

    if not username_or_email or not password:
        return jsonify(error="Please enter your username and password."), 400

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? OR email = ? COLLATE NOCASE",
            (username_or_email, username_or_email.lower())
        )
        user = cursor.fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify(error="Invalid username or password."), 401

        cursor.execute("SELECT COUNT(*) FROM chats WHERE user_id = ?", (user["id"],))
        chat_count = cursor.fetchone()[0]

    session.permanent = remember
    session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"] or "",
        "created_at": user["created_at"]
    }
    return jsonify(status="ok", user=session["user"], stats={"chat_count": chat_count})

@app.get("/api/me")
def me():
    user = session.get("user")
    if not user or not user.get("id"):
        return jsonify(user=None)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user["id"],))
            row = cursor.fetchone()
            if not row:
                session.pop("user", None)
                return jsonify(user=None)

            cursor.execute("SELECT COUNT(*) FROM chats WHERE user_id = ?", (user["id"],))
            chat_count = cursor.fetchone()[0]

            fresh_user = {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"] or "",
                "created_at": row["created_at"]
            }
            session["user"] = fresh_user
            return jsonify(user=fresh_user, stats={"chat_count": chat_count})
    except Exception as e:
        print(f"[Auth Error] /api/me failed: {e}")
        return jsonify(user=user, stats={"chat_count": 0})

@app.post("/api/logout")
def logout():
    session.pop("user", None)
    return jsonify(status="ok")

@app.get("/api/history")
def history():
    user = session.get("user")
    if not user:
        return jsonify(history=[])
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, sentiment, topic, mode, created_at FROM chats WHERE user_id = ? ORDER BY id ASC LIMIT 100",
                (user["id"],)
            )
            rows = [dict(r) for r in cursor.fetchall()]
            return jsonify(history=rows)
    except Exception:
        return jsonify(history=[])

@app.delete("/api/history")
def clear_history():
    user = session.get("user")
    if user and user.get("id"):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM chats WHERE user_id = ?", (user["id"],))
                conn.commit()
            return jsonify(status="ok", message="Chat history cleared successfully.")
        except Exception as e:
            return jsonify(error=str(e)), 500
    return jsonify(status="ok", message="Guest session cleared.")

@app.get("/api/analytics")
def analytics():
    n = stats["messages"]
    return jsonify(messages=n, ai_responses=stats["ai_responses"], fallback_responses=stats["fallback_responses"],
                   average_response_ms=round(stats["total_ms"]/n) if n else 0,
                   sentiments=dict(stats["sentiments"]), topics=dict(stats["topics"]), started_at=stats["started_at"])


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    key, fallback_model = get_api_config()
    print("=" * 60)
    print(" * Dynamic AI Chatbot Server")
    print(f" - Running at: http://127.0.0.1:{port}")
    if key:
        active_model = get_supported_model(key)
        print(f" - Gemini AI: Active (Model: {active_model})")
    else:
        print(" - Gemini AI: Not configured (Running in Local Fallback mode)")
        print("   To enable Gemini: add GEMINI_API_KEY in .env or environment")
    print("=" * 60)
    app.run(host="127.0.0.1", port=port, debug=False)

