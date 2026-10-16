/* ═══════════════════════════════════════════════════════════
   FFGlory — Login / Signup Page Logic
   ═══════════════════════════════════════════════════════════ */

// ═══════════════ Tab switching ═══════════════
function switchAuthTab(tab) {
    const loginForm  = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');
    const loginTab   = document.getElementById('login-tab');
    const signupTab  = document.getElementById('signup-tab');
    const title      = document.getElementById('auth-title');
    const subtitle   = document.getElementById('auth-subtitle');

    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        signupForm.classList.add('hidden');
        loginTab.className  = 'flex-1 py-3 px-4 rounded-lg text-sm font-medium transition-all bg-gradient-to-r from-[#F5E6D3] to-[#D4C4A8] text-[#0E0E0E] shadow-sm';
        signupTab.className = 'flex-1 py-3 px-4 rounded-lg text-sm font-medium transition-all text-[var(--ng-text-muted)] hover:text-white hover:bg-white/5';
        if (title)    title.textContent = 'Welcome Back';
        if (subtitle) subtitle.innerHTML = 'Sign in to <span class="text-[#F5E6D3] font-semibold">FFGlory</span> panel';
    } else {
        loginForm.classList.add('hidden');
        signupForm.classList.remove('hidden');
        signupTab.className = 'flex-1 py-3 px-4 rounded-lg text-sm font-medium transition-all bg-gradient-to-r from-[#F5E6D3] to-[#D4C4A8] text-[#0E0E0E] shadow-sm';
        loginTab.className  = 'flex-1 py-3 px-4 rounded-lg text-sm font-medium transition-all text-[var(--ng-text-muted)] hover:text-white hover:bg-white/5';
        if (title)    title.textContent = 'Create Account';
        if (subtitle) subtitle.innerHTML = 'Join <span class="text-[#F5E6D3] font-semibold">FFGlory</span> today';
    }
}

// ═══════════════ Turnstile callbacks ═══════════════
let _turnstileToken = null;

function onTurnstileSuccess(token) {
    _turnstileToken = token;
    const btn = document.getElementById('signup-btn');
    if (btn) btn.disabled = false;
}

function onTurnstileExpired() {
    _turnstileToken = null;
    const btn = document.getElementById('signup-btn');
    if (btn) btn.disabled = true;
}

// ═══════════════ Login Submit ═══════════════
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');
    const loginError = document.getElementById('login-error');
    const signupSuccess = document.getElementById('signup-success');

    // ═══ Login ═══
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn  = document.getElementById('login-btn');
            const text = document.getElementById('login-text');
            const origText = text.textContent;

            const fd = new FormData(loginForm);
            const payload = {
                username: fd.get('username'),
                password: fd.get('password')
            };

            loginError.classList.add('hidden');
            btn.disabled = true;
            text.textContent = 'Signing in...';

            try {
                const res = await fetch(API.login, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    window.location.href = '/client';
                    return;
                }

                let errMsg = 'Login failed';
                try {
                    const data = await res.json();
                    errMsg = data.error || data.message || errMsg;
                } catch {
                    errMsg = await res.text() || errMsg;
                }
                loginError.textContent = errMsg;
                loginError.classList.remove('hidden');
            } catch (err) {
                loginError.textContent = 'Network error. Please try again.';
                loginError.classList.remove('hidden');
            } finally {
                btn.disabled = false;
                text.textContent = origText;
            }
        });
    }

    // ═══ Signup ═══
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const pwd     = document.getElementById('signup-password').value;
            const confirm = document.getElementById('signup-confirm-password').value;
            const btn     = document.getElementById('signup-btn');
            const text    = document.getElementById('signup-text');
            const origText = text.textContent;

            signupSuccess.classList.add('hidden');
            loginError.classList.add('hidden');

            if (pwd !== confirm) {
                loginError.textContent = 'Passwords do not match';
                loginError.classList.remove('hidden');
                return;
            }
            if (pwd.length < 6) {
                loginError.textContent = 'Password must be at least 6 characters';
                loginError.classList.remove('hidden');
                return;
            }
            if (!_turnstileToken) {
                loginError.textContent = 'Please complete the security check';
                loginError.classList.remove('hidden');
                return;
            }

            const fd = new FormData(signupForm);
            const payload = {
                username: fd.get('username'),
                password: pwd,
                turnstile_token: _turnstileToken,
                invitation_code: fd.get('invitation_code') || ''
            };

            btn.disabled = true;
            text.textContent = 'Creating...';

            try {
                const res = await fetch(API.signup, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    signupSuccess.textContent = 'Account created! You can now sign in.';
                    signupSuccess.classList.remove('hidden');
                    setTimeout(() => switchAuthTab('login'), 1500);
                    signupForm.reset();
                    _turnstileToken = null;
                } else {
                    let errMsg = 'Signup failed';
                    try {
                        const data = await res.json();
                        errMsg = data.error || data.message || errMsg;
                    } catch {
                        errMsg = await res.text() || errMsg;
                    }
                    loginError.textContent = errMsg;
                    loginError.classList.remove('hidden');
                }
            } catch (err) {
                loginError.textContent = 'Network error. Please try again.';
                loginError.classList.remove('hidden');
            } finally {
                btn.disabled = false;
                text.textContent = origText;
            }
        });
    }

    // Auto-hide URL-param message if present
    const params = new URLSearchParams(window.location.search);
    if (params.get('msg')) {
        loginError.textContent = params.get('msg');
        loginError.classList.remove('hidden');
    }
});