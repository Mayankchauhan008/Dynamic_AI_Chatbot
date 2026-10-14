/* ==========================================================================
   DYNAMIC AI — LOGIN & REGISTER CLIENT CONTROLLER
   ========================================================================== */

(function () {
  'use strict';

  // DOM Elements
  const tabBtnLogin = document.getElementById('tabBtnLogin');
  const tabBtnRegister = document.getElementById('tabBtnRegister');
  const tabIndicator = document.getElementById('tabIndicator');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const formTitle = document.getElementById('formTitle');
  const formSubtitle = document.getElementById('formSubtitle');
  const switchTabBtn = document.getElementById('switchTabBtn');
  const togglePrompt = document.getElementById('togglePrompt');
  const authAlert = document.getElementById('authAlert');
  const alertMsg = document.getElementById('alertMsg');
  const authToast = document.getElementById('authToast');
  const themeToggle = document.getElementById('themeToggle');

  // Register Fields for real-time validation
  const regUser = document.getElementById('regUsername');
  const userHint = document.getElementById('userHint');
  const regPass = document.getElementById('regPassword');
  const regConfirm = document.getElementById('regConfirmPassword');
  const confirmHint = document.getElementById('confirmHint');
  const strengthBar = document.getElementById('strengthBar');
  const strengthText = document.getElementById('strengthText');

  let activeTab = 'login';
  let toastTimer = null;

  // --------------------------------------------------------------------------
  // Theme Management
  // --------------------------------------------------------------------------
  function initTheme() {
    const saved = localStorage.getItem('dynamic-ai-theme') || 'dark';
    if (saved === 'dark') {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }

  themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('dynamic-ai-theme', isDark ? 'dark' : 'light');
  });

  // --------------------------------------------------------------------------
  // Toast Notifications
  // --------------------------------------------------------------------------
  function showToast(message) {
    if (!authToast) return;
    authToast.textContent = message;
    authToast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      authToast.classList.remove('show');
    }, 2800);
  }

  // --------------------------------------------------------------------------
  // Alert Banner
  // --------------------------------------------------------------------------
  function showAlert(msg, type = 'error') {
    if (!authAlert) return;
    alertMsg.textContent = msg;
    authAlert.className = `auth-alert ${type}`;
    authAlert.classList.remove('hidden');

    // Subtle vibration on card
    const card = document.getElementById('authCard');
    if (card && type === 'error') {
      card.style.transform = 'translateX(-4px)';
      setTimeout(() => { card.style.transform = 'translateX(4px)'; }, 80);
      setTimeout(() => { card.style.transform = 'translateX(-2px)'; }, 160);
      setTimeout(() => { card.style.transform = 'translateX(0)'; }, 240);
    }
  }

  function hideAlert() {
    if (!authAlert) return;
    authAlert.classList.add('hidden');
    alertMsg.textContent = '';
  }

  // --------------------------------------------------------------------------
  // Tab Switching
  // --------------------------------------------------------------------------
  function switchTab(target) {
    hideAlert();
    activeTab = target;

    if (target === 'login') {
      tabBtnLogin.classList.add('active');
      tabBtnLogin.setAttribute('aria-selected', 'true');
      tabBtnRegister.classList.remove('active');
      tabBtnRegister.setAttribute('aria-selected', 'false');
      tabIndicator.classList.remove('register');

      loginForm.classList.remove('hidden');
      registerForm.classList.add('hidden');

      formTitle.textContent = 'Welcome Back';
      formSubtitle.textContent = 'Enter your credentials to access your personal AI workspace.';

      togglePrompt.innerHTML = `
        <span>New to Dynamic AI?</span>
        <button type="button" class="link-switch" id="switchTabBtn">Create an account</button>
      `;
      document.getElementById('switchTabBtn').addEventListener('click', () => switchTab('register'));

      // Focus first input
      setTimeout(() => {
        const inp = document.getElementById('loginUsername');
        if (inp) inp.focus();
      }, 100);

      // Update URL without reload
      if (window.location.pathname === '/register' || window.location.hash === '#register') {
        history.replaceState(null, '', '/login');
      }

    } else {
      tabBtnRegister.classList.add('active');
      tabBtnRegister.setAttribute('aria-selected', 'true');
      tabBtnLogin.classList.remove('active');
      tabBtnLogin.setAttribute('aria-selected', 'false');
      tabIndicator.classList.add('register');

      registerForm.classList.remove('hidden');
      loginForm.classList.add('hidden');

      formTitle.textContent = 'Create Your Account';
      formSubtitle.textContent = 'Join Dynamic AI to preserve chats, insights, and continuous reasoning.';

      togglePrompt.innerHTML = `
        <span>Already have an account?</span>
        <button type="button" class="link-switch" id="switchTabBtn">Sign in instead</button>
      `;
      document.getElementById('switchTabBtn').addEventListener('click', () => switchTab('login'));

      setTimeout(() => {
        const inp = document.getElementById('regUsername');
        if (inp) inp.focus();
      }, 100);

      if (window.location.pathname === '/login' || window.location.hash === '#login') {
        history.replaceState(null, '', '/register');
      }
    }
  }

  tabBtnLogin.addEventListener('click', () => switchTab('login'));
  tabBtnRegister.addEventListener('click', () => switchTab('register'));
  if (switchTabBtn) {
    switchTabBtn.addEventListener('click', () => switchTab('register'));
  }

  // --------------------------------------------------------------------------
  // Password Visibility Toggle
  // --------------------------------------------------------------------------
  document.querySelectorAll('.btn-toggle-pwd').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.target;
      const input = document.getElementById(targetId);
      if (!input) return;

      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';

      const openEye = btn.querySelector('.eye-open');
      const closedEye = btn.querySelector('.eye-closed');

      if (isPassword) {
        openEye.classList.add('hidden');
        closedEye.classList.remove('hidden');
      } else {
        openEye.classList.remove('hidden');
        closedEye.classList.add('hidden');
      }
    });
  });

  // --------------------------------------------------------------------------
  // Password Strength Evaluator
  // --------------------------------------------------------------------------
  function evaluatePasswordStrength(pwd) {
    if (!pwd) return { score: 0, text: 'None', level: '' };

    let score = 0;
    if (pwd.length >= 6) score += 1;
    if (pwd.length >= 10) score += 1;
    if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) score += 1;
    if (/\d/.test(pwd)) score += 1;
    if (/[^a-zA-Z0-9]/.test(pwd)) score += 1;

    if (pwd.length < 6) {
      return { score: 1, text: 'Too short (min 6)', level: 'weak' };
    }
    if (score <= 2) return { score: 1, text: 'Weak', level: 'weak' };
    if (score === 3) return { score: 2, text: 'Fair', level: 'fair' };
    if (score === 4) return { score: 3, text: 'Good', level: 'good' };
    return { score: 4, text: 'Strong', level: 'strong' };
  }

  regPass.addEventListener('input', () => {
    const val = regPass.value;
    const result = evaluatePasswordStrength(val);

    strengthBar.className = 'strength-bar ' + result.level;
    strengthText.textContent = result.text;

    // Check confirm password match
    checkPasswordMatch();
  });

  function checkPasswordMatch() {
    const p1 = regPass.value;
    const p2 = regConfirm.value;

    if (!p2) {
      confirmHint.textContent = '';
      confirmHint.className = 'field-hint';
      return;
    }

    if (p1 === p2) {
      confirmHint.textContent = '✓ Passwords match';
      confirmHint.className = 'field-hint valid';
    } else {
      confirmHint.textContent = '✕ Passwords do not match';
      confirmHint.className = 'field-hint invalid';
    }
  }

  regConfirm.addEventListener('input', checkPasswordMatch);

  // Username validation
  regUser.addEventListener('input', () => {
    const val = regUser.value.trim();
    if (!val) {
      userHint.textContent = 'Min 3 characters (letters, numbers, dot, or _)';
      userHint.className = 'field-hint';
      return;
    }
    if (val.length < 3) {
      userHint.textContent = 'Too short: needs at least 3 characters';
      userHint.className = 'field-hint invalid';
    } else if (!/^[a-zA-Z0-9_.-]+$/.test(val)) {
      userHint.textContent = 'Only letters, numbers, dot (.), and underscore (_) allowed';
      userHint.className = 'field-hint invalid';
    } else {
      userHint.textContent = '✓ Valid username format';
      userHint.className = 'field-hint valid';
    }
  });

  // --------------------------------------------------------------------------
  // Button State Helper
  // --------------------------------------------------------------------------
  function setButtonLoading(btn, isLoading, originalText) {
    const textEl = btn.querySelector('.btn-text');
    const spinner = btn.querySelector('.btn-spinner');
    const arrow = btn.querySelector('.btn-arrow');

    btn.disabled = isLoading;
    if (isLoading) {
      if (textEl) textEl.textContent = 'Processing…';
      if (spinner) spinner.classList.remove('hidden');
      if (arrow) arrow.classList.add('hidden');
    } else {
      if (textEl) textEl.textContent = originalText;
      if (spinner) spinner.classList.add('hidden');
      if (arrow) arrow.classList.remove('hidden');
    }
  }

  // --------------------------------------------------------------------------
  // Handle Login Submission
  // --------------------------------------------------------------------------
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideAlert();

    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    const remember = document.getElementById('loginRemember').checked;
    const submitBtn = document.getElementById('loginSubmitBtn');

    if (!username || !password) {
      showAlert('Please enter both your username and password.');
      return;
    }

    setButtonLoading(submitBtn, true, 'Sign In to Dynamic AI');

    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, remember })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Authentication failed. Please verify credentials.');
      }

      showToast(`Welcome back, ${data.user.username}! Redirecting…`);
      showAlert(`Authenticated as ${data.user.username}. Loading workspace…`, 'success');

      // Seamless transition to chat app
      setTimeout(() => {
        window.location.href = '/';
      }, 700);

    } catch (err) {
      showAlert(err.message || 'Unable to connect to server. Please ensure server is running.');
      setButtonLoading(submitBtn, false, 'Sign In to Dynamic AI');
    }
  });

  // --------------------------------------------------------------------------
  // Handle Register Submission
  // --------------------------------------------------------------------------
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideAlert();

    const username = regUser.value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = regPass.value;
    const confirmPassword = regConfirm.value;
    const remember = document.getElementById('regTerms').checked;
    const submitBtn = document.getElementById('regSubmitBtn');

    if (username.length < 3) {
      showAlert('Username must be at least 3 characters long.');
      regUser.focus();
      return;
    }

    if (!/^[a-zA-Z0-9_.-]+$/.test(username)) {
      showAlert('Username can only contain letters, numbers, dot, or underscore.');
      regUser.focus();
      return;
    }

    if (email && !/^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$/.test(email)) {
      showAlert('Please enter a valid email address or leave it blank.');
      document.getElementById('regEmail').focus();
      return;
    }

    if (password.length < 6) {
      showAlert('Password must be at least 6 characters long.');
      regPass.focus();
      return;
    }

    if (password !== confirmPassword) {
      showAlert('Passwords do not match. Please re-enter your password.');
      regConfirm.focus();
      return;
    }

    setButtonLoading(submitBtn, true, 'Create Free Account');

    try {
      const response = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password, remember })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Registration failed.');
      }

      showToast(`Account created! Welcome, ${data.user.username}!`);
      showAlert(`Welcome to Dynamic AI, ${data.user.username}! Initializing your vault…`, 'success');

      setTimeout(() => {
        window.location.href = '/';
      }, 750);

    } catch (err) {
      showAlert(err.message || 'An error occurred during registration.');
      setButtonLoading(submitBtn, false, 'Create Free Account');
    }
  });

  // --------------------------------------------------------------------------
  // Check Existing Session
  // --------------------------------------------------------------------------
  async function checkActiveSession() {
    try {
      const r = await fetch('/api/me');
      const d = await r.json();
      if (d && d.user) {
        // User is already logged in, redirect to chat
        window.location.href = '/';
      }
    } catch {
      // Server offline or not logged in, remain on page
    }
  }

  // --------------------------------------------------------------------------
  // Initialization
  // --------------------------------------------------------------------------
  initTheme();
  checkActiveSession();

  // Determine initial tab from pathname or hash or query
  const path = window.location.pathname;
  const hash = window.location.hash;
  const params = new URLSearchParams(window.location.search);

  if (path === '/register' || hash === '#register' || params.get('tab') === 'register' || params.get('mode') === 'register') {
    switchTab('register');
  } else {
    switchTab('login');
  }

})();
