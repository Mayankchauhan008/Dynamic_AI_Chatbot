const $ = s => document.querySelector(s);
const historyItems = [];
let busy = false;
let toastTimer;
let currentUser = null;

function toast(message) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2400);
}

function time() {
  return new Intl.DateTimeFormat([], { hour: "2-digit", minute: "2-digit" }).format(new Date());
}

function startChat() {
  const welcome = $("#welcome");
  const messages = $("#messages");
  if (welcome) welcome.classList.add("hidden");
  if (messages) messages.classList.add("active");
}

function formatMarkdown(text) {
  if (!text) return "";
  let s = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks: ```language\ncode```
  s = s.replace(/```(?:([a-zA-Z0-9_-]+)\n)?([\s\S]*?)```/g, (_, lang, code) => {
    const l = lang || "code";
    return `<div class="code-block"><div class="code-header"><span>${l}</span><button type="button" class="copy-btn" onclick="copyCode(this)">Copy</button></div><pre><code>${code.trim()}</code></pre></div>`;
  });

  // Inline code: `code`
  s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");

  // Bold: **text**
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  // Italic: *text*
  s = s.replace(/(^|[^\*])\*([^*]+)\*([^\*]|$)/g, "$1<em>$2</em>$3");

  const lines = s.split("\n");
  const res = [];
  let inUl = false, inOl = false;

  for (let line of lines) {
    const trimmed = line.trim();
    const ulMatch = trimmed.match(/^[-*•]\s+(.*)$/);
    const olMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);

    if (ulMatch) {
      if (inOl) { res.push("</ol>"); inOl = false; }
      if (!inUl) { res.push("<ul>"); inUl = true; }
      res.push(`<li>${ulMatch[1]}</li>`);
    } else if (olMatch) {
      if (inUl) { res.push("</ul>"); inUl = false; }
      if (!inOl) { res.push("<ol>"); inOl = true; }
      res.push(`<li>${olMatch[2]}</li>`);
    } else {
      if (inUl) { res.push("</ul>"); inUl = false; }
      if (inOl) { res.push("</ol>"); inOl = false; }
      if (trimmed === "") {
        res.push("<div style='height:8px;'></div>");
      } else {
        res.push(`<div>${line}</div>`);
      }
    }
  }
  if (inUl) res.push("</ul>");
  if (inOl) res.push("</ol>");

  return res.join("");
}

window.copyCode = function(btn) {
  const code = btn.closest(".code-block").querySelector("code").innerText;
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = "Copied!";
    setTimeout(() => btn.textContent = "Copy", 2000);
  });
};

function addMessage(role, text, meta = {}) {
  startChat();
  const messagesContainer = $("#messages");
  const el = document.createElement("div");
  el.className = "message-row " + role;
  
  const av = document.createElement("div");
  av.className = "msg-avatar";
  if (role === "user") {
    av.textContent = currentUser ? currentUser.username.slice(0, 1).toUpperCase() : "Y";
  } else {
    av.innerHTML = '<img src="/static/logo.svg" alt="Dynamic AI" class="brand-logo-img">';
  }
  
  const wrapper = document.createElement("div");
  wrapper.className = "msg-wrapper";
  
  const ts = document.createElement("div");
  ts.className = "msg-timestamp";
  const senderLabel = role === "user" ? (currentUser ? currentUser.username : "You") : "Dynamic AI";
  ts.textContent = senderLabel + " · " + time();
  
  const b = document.createElement("div");
  b.className = "msg-bubble";
  
  if (meta.isTyping) {
    b.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
  } else if (role === "user") {
    b.textContent = text;
  } else {
    b.innerHTML = formatMarkdown(text);
  }
  
  wrapper.append(ts, b);
  
  if (role !== "user" && meta.sentiment && !meta.isTyping) {
    const tags = document.createElement("div");
    tags.className = "response-tags";

    const sentTag = document.createElement("span");
    sentTag.className = "tag-pill sent-" + meta.sentiment;
    sentTag.textContent = meta.sentiment;
    tags.append(sentTag);

    if (meta.topic) {
      const topicTag = document.createElement("span");
      topicTag.className = "tag-pill";
      topicTag.textContent = meta.topic;
      tags.append(topicTag);
    }

    wrapper.append(tags);
  }
  
  el.append(av, wrapper);
  messagesContainer.append(el);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  return el;
}

async function send(raw) {
  const message = raw.trim();
  if (!message || busy) return;
  
  busy = true;
  $("#send").disabled = true;
  $("#input").value = "";
  resize();
  
  addMessage("user", message);
  const typing = addMessage("assistant", "", { isTyping: true });
  
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history: [...historyItems, { role: "user", content: message }]
      })
    });
    
    const d = await r.json();
    typing.remove();
    
    if (!r.ok) {
      throw new Error(d.error || "Request failed with status " + r.status);
    }
    
    addMessage("assistant", d.reply || "No response returned.", d);
    historyItems.push({ role: "user", content: message }, { role: "model", content: d.reply || "" });
    historyItems.splice(0, Math.max(0, historyItems.length - 12));
    
  } catch (e) {
    typing.remove();
    addMessage("assistant", "Sorry, something went wrong: " + e.message + ". Please ensure server.py is running in terminal.");
  } finally {
    busy = false;
    $("#send").disabled = false;
    $("#input").focus();
  }
}

function resize() {
  const input = $("#input");
  if (!input) return;
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 150) + "px";
}

$("#form").addEventListener("submit", e => {
  e.preventDefault();
  send($("#input").value);
});

$("#input").addEventListener("input", resize);
$("#input").addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("#form").requestSubmit();
  }
});

// Prompt cards
document.querySelectorAll("[data-prompt]").forEach(card => {
  card.addEventListener("click", () => send(card.dataset.prompt));
});

// New Chat button
$("#newChat").onclick = () => {
  historyItems.length = 0;
  $("#messages").replaceChildren();
  $("#messages").classList.remove("active");
  $("#welcome").classList.remove("hidden");
  view("chat");
  $("#sidebar").classList.remove("open");
  $("#input").focus();
  toast("New conversation started");
};

// Export button
$("#export").onclick = () => {
  const blob = new Blob([
    JSON.stringify({ exported_at: new Date().toISOString(), user: currentUser ? currentUser.username : "guest", messages: historyItems }, null, 2)
  ], { type: "application/json" });
  
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `dynamic-ai-chat-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
  toast("Conversation export downloaded");
};

// Theme toggle
function updateThemeUI(isDark) {
  const text = $("#themeText");
  if (text) text.textContent = isDark ? "Light Mode" : "Dark Mode";
}

$("#theme").onclick = () => {
  document.body.classList.toggle("dark-mode");
  const isDark = document.body.classList.contains("dark-mode");
  localStorage.setItem("dynamic-ai-theme", isDark ? "dark" : "light");
  updateThemeUI(isDark);
};

// Restore theme from localStorage
const storedTheme = localStorage.getItem("dynamic-ai-theme") || "dark";
if (storedTheme === "dark") {
  document.body.classList.add("dark-mode");
  updateThemeUI(true);
} else {
  document.body.classList.remove("dark-mode");
  updateThemeUI(false);
}

// Mobile sidebar toggle
$("#menu").onclick = () => $("#sidebar").classList.toggle("open");

// View navigation (Chat vs Analytics)
document.querySelectorAll("[data-view]").forEach(btn => {
  btn.onclick = () => view(btn.dataset.view);
});

function view(v) {
  const isChat = v === "chat";
  $("#chatView").classList.toggle("hidden", !isChat);
  $("#analyticsView").classList.toggle("hidden", isChat);
  
  $("#title").textContent = isChat
    ? (historyItems.length ? "Active Conversation" : "What would you like to explore?")
    : "Usage & Sentiment Analytics";
    
  $("#crumb").textContent = isChat ? "CHAT" : "ANALYTICS";
  
  document.querySelectorAll("[data-view]").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.view === v);
  });
  
  $("#sidebar").classList.remove("open");
  if (!isChat) refreshAnalytics();
}

function renderBars(sel, dataObj) {
  const el = $(sel);
  const items = Object.entries(dataObj || {}).sort((a, b) => b[1] - a[1]);
  el.replaceChildren();
  
  if (!items.length) {
    el.innerHTML = '<div class="chart-content">No conversation metrics recorded yet.</div>';
    return;
  }
  
  const max = Math.max(...items.map(x => x[1]), 1);
  items.forEach(([name, count]) => {
    const row = document.createElement("div");
    row.className = "chart-bar-row";
    
    const label = document.createElement("div");
    label.className = "chart-bar-labels";
    
    const l = document.createElement("span");
    l.textContent = name;
    const v = document.createElement("span");
    v.textContent = `${count} query${count > 1 ? 'ies' : ''}`;
    label.append(l, v);
    
    const track = document.createElement("div");
    track.className = "chart-track";
    const fill = document.createElement("div");
    fill.className = "chart-fill";
    fill.style.width = ((count / max) * 100) + "%";
    track.append(fill);
    
    row.append(label, track);
    el.append(row);
  });
}

async function refreshAnalytics() {
  try {
    const r = await fetch("/api/analytics");
    const d = await r.json();
    $("#mMessages").textContent = d.messages;
    $("#mAI").textContent = d.ai_responses;
    $("#mFallback").textContent = d.fallback_responses;
    $("#mTime").textContent = `${d.average_response_ms} ms`;
    renderBars("#sentiments", d.sentiments);
    renderBars("#topics", d.topics);
  } catch {
    toast("Could not refresh analytics");
  }
}

$("#refresh").onclick = refreshAnalytics;

// Optional Health check
function checkHealth() {
  fetch("/api/health")
    .then(r => r.json())
    .catch(() => {});
}
checkHealth();

// ==============================================================================
// AUTHENTICATION & PROFILE SYSTEM
// ==============================================================================

function setAuthAlert(msg, type = "error") {
  const alertEl = $("#authAlert");
  if (!alertEl) return;
  alertEl.textContent = msg;
  alertEl.className = "auth-alert " + type;
}

function clearAuthAlert() {
  const alertEl = $("#authAlert");
  if (!alertEl) return;
  alertEl.textContent = "";
  alertEl.className = "auth-alert hidden";
}

function switchAuthTab(tab) {
  clearAuthAlert();
  if (tab === "login") {
    $("#tabLogin").classList.add("active");
    $("#tabRegister").classList.remove("active");
    $("#loginForm").classList.remove("hidden");
    $("#registerForm").classList.add("hidden");
    $("#authModalTitle").textContent = "Welcome to Dynamic AI";
    setTimeout(() => $("#loginUser").focus(), 100);
  } else {
    $("#tabRegister").classList.add("active");
    $("#tabLogin").classList.remove("active");
    $("#registerForm").classList.remove("hidden");
    $("#loginForm").classList.add("hidden");
    $("#authModalTitle").textContent = "Create an Account";
    setTimeout(() => $("#regUser").focus(), 100);
  }
}

function openAuthModal(initialTab = "login") {
  $("#authModal").classList.remove("hidden");
  switchAuthTab(initialTab);
}

function closeAuthModal() {
  $("#authModal").classList.add("hidden");
  clearAuthAlert();
  $("#loginForm").reset();
  $("#registerForm").reset();
}

function updateUserUI(user, stats = {}) {
  currentUser = user;
  const nameEl = $("#userName");
  const roleEl = $("#userRole");
  const avEl = $("#userAvatar");
  const authBtn = $("#authBtn");
  const headerAuthBtn = $("#headerAuthBtn");

  // Profile Popover elements
  const dAvatar = $("#dropdownAvatar");
  const dName = $("#dropdownUserName");
  const dEmail = $("#dropdownUserEmail");
  const dDate = $("#dropdownUserDate");
  const dChatCount = $("#dChatCount");
  const dStatus = $("#dMemberStatus");
  const btnLogout = $("#btnLogoutAction");
  const btnClearHist = $("#btnClearSavedHistory");
  const heroTitle = $(".hero-title");

  if (user && user.username) {
    nameEl.textContent = user.username;
    roleEl.textContent = user.email || "Active Member";
    const initials = user.username.slice(0, 2).toUpperCase();
    avEl.textContent = initials;
    authBtn.textContent = "Profile";
    authBtn.title = "View account details & settings";

    if (dAvatar) dAvatar.textContent = initials;
    if (dName) dName.textContent = user.username;
    if (dEmail) dEmail.textContent = user.email || "No email provided";
    if (dDate) {
      const dateStr = user.created_at ? new Date(user.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'Recent';
      dDate.textContent = `Member since ${dateStr}`;
    }
    if (dChatCount) dChatCount.textContent = (stats && stats.chat_count !== undefined) ? stats.chat_count : 'Saved';
    if (dStatus) dStatus.textContent = 'Active';

    if (btnLogout) btnLogout.classList.remove("hidden");
    if (btnClearHist) btnClearHist.classList.remove("hidden");
    if (headerAuthBtn) headerAuthBtn.classList.add("hidden");

    if (heroTitle && !historyItems.length) {
      heroTitle.innerHTML = `Welcome back, <span style="background:var(--accent-gradient);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;">${user.username}</span>!`;
    }
  } else {
    nameEl.textContent = "Guest User";
    roleEl.textContent = "Personal Workspace";
    avEl.textContent = "AI";
    authBtn.textContent = "Sign In";
    authBtn.title = "Sign In or Register";

    if (dAvatar) dAvatar.textContent = "AI";
    if (dName) dName.textContent = "Guest User";
    if (dEmail) dEmail.textContent = "Not signed in";
    if (dDate) dDate.textContent = "Temporary session";
    if (dChatCount) dChatCount.textContent = "0";
    if (dStatus) dStatus.textContent = "Guest";

    if (btnLogout) btnLogout.classList.add("hidden");
    if (btnClearHist) btnClearHist.classList.add("hidden");
    if (headerAuthBtn) headerAuthBtn.classList.remove("hidden");

    if (heroTitle) {
      heroTitle.textContent = "Where curiosity meets intelligence.";
    }
  }
}

async function loadChatHistory() {
  if (!currentUser) return;
  try {
    const r = await fetch("/api/history");
    const d = await r.json();
    if (d && Array.isArray(d.history) && d.history.length > 0) {
      startChat();
      const messagesContainer = $("#messages");
      messagesContainer.replaceChildren();
      historyItems.length = 0;

      d.history.forEach(item => {
        addMessage(item.role === "assistant" ? "assistant" : "user", item.content, {
          sentiment: item.sentiment,
          topic: item.topic,
          mode: item.mode
        });
        historyItems.push({
          role: item.role === "assistant" ? "model" : "user",
          content: item.content
        });
      });
      // Keep trailing context
      historyItems.splice(0, Math.max(0, historyItems.length - 12));
      toast(`Loaded ${d.history.length} saved messages from cloud vault`);
      const countEl = $("#dChatCount");
      if (countEl) countEl.textContent = d.history.length;
    }
  } catch (err) {
    console.warn("Could not load history:", err);
  }
}

async function checkSession() {
  try {
    const r = await fetch("/api/me");
    const d = await r.json();
    if (d && d.user) {
      updateUserUI(d.user, d.stats);
      loadChatHistory();
    } else {
      updateUserUI(null);
    }
  } catch (err) {
    console.warn("Session check failed:", err);
    updateUserUI(null);
  }
}

// Login submission in modal
$("#loginForm").addEventListener("submit", async e => {
  e.preventDefault();
  clearAuthAlert();
  const username = $("#loginUser").value.trim();
  const password = $("#loginPass").value;
  const submitBtn = $("#loginSubmit");

  if (!username || !password) {
    setAuthAlert("Please enter both username and password.");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.style.opacity = "0.6";

  try {
    const r = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, remember: true })
    });
    const d = await r.json();
    if (!r.ok) {
      throw new Error(d.error || "Login failed.");
    }
    updateUserUI(d.user, d.stats);
    closeAuthModal();
    toast(`Welcome back, ${d.user.username}!`);
    loadChatHistory();
  } catch (err) {
    setAuthAlert(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.style.opacity = "1";
  }
});

// Register submission in modal
$("#registerForm").addEventListener("submit", async e => {
  e.preventDefault();
  clearAuthAlert();
  const username = $("#regUser").value.trim();
  const email = $("#regEmail").value.trim();
  const password = $("#regPass").value;
  const submitBtn = $("#regSubmit");

  if (username.length < 3) {
    setAuthAlert("Username must be at least 3 characters long.");
    return;
  }
  if (password.length < 6) {
    setAuthAlert("Password must be at least 6 characters long.");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.style.opacity = "0.6";

  try {
    const r = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password, remember: true })
    });
    const d = await r.json();
    if (!r.ok) {
      throw new Error(d.error || "Registration failed.");
    }
    updateUserUI(d.user, d.stats);
    closeAuthModal();
    toast(`Account created! Welcome, ${d.user.username}!`);
  } catch (err) {
    setAuthAlert(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.style.opacity = "1";
  }
});

// Toggle Profile Dropdown
const profileDropdown = $("#profileDropdown");
const userChip = $("#userChip");

if (userChip) {
  userChip.addEventListener("click", (e) => {
    // If clicking the auth button directly
    if (e.target && e.target.id === "authBtn") {
      if (!currentUser) {
        openAuthModal("login");
        return;
      }
    }
    if (profileDropdown) {
      profileDropdown.classList.toggle("hidden");
    }
  });
}

// Close dropdown when clicking outside
document.addEventListener("click", (e) => {
  if (profileDropdown && !profileDropdown.classList.contains("hidden")) {
    const container = $("#userChipContainer");
    if (container && !container.contains(e.target)) {
      profileDropdown.classList.add("hidden");
    }
  }
});

// Sign Out Action
const btnLogoutAction = $("#btnLogoutAction");
if (btnLogoutAction) {
  btnLogoutAction.addEventListener("click", async () => {
    try {
      await fetch("/api/logout", { method: "POST" });
      updateUserUI(null);
      if (profileDropdown) profileDropdown.classList.add("hidden");
      historyItems.length = 0;
      $("#messages").replaceChildren();
      $("#messages").classList.remove("active");
      $("#welcome").classList.remove("hidden");
      toast("You have been signed out.");
    } catch {
      toast("Sign out failed");
    }
  });
}

// Clear Cloud History Action
const btnClearSavedHistory = $("#btnClearSavedHistory");
if (btnClearSavedHistory) {
  btnClearSavedHistory.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to delete all saved cloud conversation history?")) {
      return;
    }
    try {
      const r = await fetch("/api/history", { method: "DELETE" });
      const d = await r.json();
      if (r.ok) {
        historyItems.length = 0;
        $("#messages").replaceChildren();
        $("#messages").classList.remove("active");
        $("#welcome").classList.remove("hidden");
        const countEl = $("#dChatCount");
        if (countEl) countEl.textContent = "0";
        if (profileDropdown) profileDropdown.classList.add("hidden");
        toast("Cloud conversation history cleared.");
      } else {
        toast(d.error || "Failed to clear history");
      }
    } catch {
      toast("Failed to clear history");
    }
  });
}

// Tab Buttons
$("#tabLogin").addEventListener("click", () => switchAuthTab("login"));
$("#tabRegister").addEventListener("click", () => switchAuthTab("register"));
$("#closeAuthModal").addEventListener("click", closeAuthModal);

// Close on backdrop click
$("#authModal").addEventListener("click", e => {
  if (e.target === $("#authModal")) {
    closeAuthModal();
  }
});

// Close on Escape key
document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    if (!$("#authModal").classList.contains("hidden")) {
      closeAuthModal();
    }
    if (profileDropdown && !profileDropdown.classList.contains("hidden")) {
      profileDropdown.classList.add("hidden");
    }
  }
});

// Check session on initial load
checkSession();
