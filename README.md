# Dynamic AI Chatbot

A complete responsive chatbot based on your supplied chatbot ZIP and project brief. Flask powers the backend; HTML, CSS, and JavaScript power the interface. Gemini AI is optional, and local fallback replies work without an API key.

## Features
- Responsive chat UI and browser-side conversation context
- Gemini-generated answers when configured
- Local fallback responses if no key is present or the API fails
- Lightweight sentiment and topic labels
- Analytics dashboard, chat export, clear conversation, dark/light theme
- API validation and request timeout; no API key hard-coded in source

## Run on Windows
1. Extract this ZIP and open the folder in VS Code.
2. In the terminal run:
   ```powershell
   python -m venv .venv
   .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
3. Optional Gemini setup (use a NEW key, not one pasted into an old notebook):
   ```powershell
   $env:GEMINI_API_KEY="YOUR_NEW_GEMINI_API_KEY"
   python server.py
   ```
4. Open http://127.0.0.1:5000

Without a key, run `python server.py` and the local fallback still works.

## macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="YOUR_NEW_GEMINI_API_KEY"  # optional
python server.py
```

## API & Routes
- `GET /` — Main Chat workspace interface
- `GET /login` — Dedicated standalone Login page
- `GET /register` — Dedicated standalone Register page
- `POST /api/register` with JSON `{"username":"...", "email":"...", "password":"...", "remember": true}`
- `POST /api/login` with JSON `{"username":"...", "password":"...", "remember": true}`
- `GET /api/me` — Current user profile and conversation metrics
- `POST /api/logout` — End session
- `GET /api/history` — Fetch user's saved conversation history from SQLite
- `DELETE /api/history` — Clear user's saved conversations
- `GET /api/health` — Check Gemini AI and server status
- `POST /api/chat` with JSON `{"message":"Hello","history":[]}`
- `GET /api/analytics` — Telemetry and sentiment distribution

## Project layout
```text
Dynamic_AI_Chatbot/
├── server.py              # Flask backend, auth routes, SQLite helpers, Gemini AI proxy
├── chatbot.db             # SQLite database storing users and conversation logs
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── static/
    ├── index.html         # Main Chat & Analytics application
    ├── style.css          # Core design system & interface styling
    ├── app.js             # Chat stream, profile popover, theme, markdown renderer
    ├── login.html         # Standalone split-screen Login & Register interface
    ├── login.css          # Dedicated glassmorphic styling for auth page
    └── login.js           # Real-time password strength, tab switching, auth controller
```

User accounts and conversation history are persistently stored in SQLite (`chatbot.db`). Sessions are managed with encrypted cookies, supporting 30-day "Remember Me" persistence.
