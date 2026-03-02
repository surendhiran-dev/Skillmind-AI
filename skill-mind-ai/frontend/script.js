(() => {
    'use strict';

    const API = '';  // same origin
    const socket = io(); // Initialize Socket.IO connection

    /* ===== State ===== */
    const rawUser = sessionStorage.getItem('user');
    const safeParse = (key, defaultVal) => {
        const val = sessionStorage.getItem(key);
        if (!val || val === 'undefined') return defaultVal;
        try { return JSON.parse(val); } catch { return defaultVal; }
    };
    const state = {
        token: sessionStorage.getItem('token'),
        user: rawUser && rawUser !== 'undefined' ? JSON.parse(rawUser) : null,
        activePage: 'home', // New
        activeJD: sessionStorage.getItem('activeJD') || '',
        activeResumeSkills: safeParse('activeResumeSkills', []),
        activeJDSkills: safeParse('activeJDSkills', []),
        quizQuestions: [],
        quizIndex: 0,
        quizResponses: [],
        codingChallenges: [],
        codingIndex: 0,
        codingSubmissions: [],
        codingTotalMarks: 0,
        currentEntities: {}, // New
        charts: {}, // Store chart instances // New
        interviewSessionId: null,
        interviewActive: false,
        interviewQuestionIndex: 0,
        interviewMessages: [],
        lastReport: null
    };

    /* ===== Helpers ===== */
    const $ = (s) => document.querySelector(s);
    const $$ = (s) => document.querySelectorAll(s);

    // --- Utilities ---
    const animateValue = (id, start, end, duration) => {
        const obj = document.getElementById(id);
        if (!obj) return;
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start) + '%';
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    };

    const updateCircularStrength = (score) => {
        const circle = document.getElementById('resStrengthCircle');
        const label = document.getElementById('resAnalysisScore');
        if (circle) {
            circle.style.strokeDasharray = `${score}, 100`;
        }
        if (label) {
            let current = 0;
            const interval = setInterval(() => {
                if (current >= score) {
                    label.innerText = score;
                    clearInterval(interval);
                } else {
                    current++;
                    label.innerText = current;
                }
            }, 15);
        }
    };

    function showToast(message, type = 'info') {
        const container = $('#toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '✅',
            error: '❌',
            info: 'ℹ️',
            warning: '⚠️'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${message}</span>
        `;

        container.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('active'), 10);

        // Remove after 4s
        setTimeout(() => {
            toast.classList.remove('active');
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    }

    async function api(path, opts = {}) {
        const headers = { ...(opts.headers || {}) };

        // Only add Authorization header if it's not a login/register request
        if (state.token && !path.includes('/auth/login') && !path.includes('/auth/register')) {
            headers['Authorization'] = `Bearer ${state.token}`;
        }

        // Only stringify if body is a plain object (not FormData)
        let body = opts.body;
        if (body && !(body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
            body = JSON.stringify(body);
        }

        let res;
        try {
            res = await fetch(`${API}${path}`, {
                method: opts.method || 'GET',
                headers,
                body
            });
        } catch (networkErr) {
            // Network error (server down, CORS, etc.)
            const msg = 'Network error — is the server running?';
            showToast(msg, 'error');
            throw new Error(msg);
        }

        // Parse response
        let data = {};
        const ct = res.headers.get('content-type') || '';
        if (ct.includes('application/json')) {
            try { data = await res.json(); } catch { data = {}; }
        }

        if (!res.ok) {
            if (res.status === 401 && !path.includes('/auth/login')) {
                showToast('Session expired. Please log in again.', 'warning');
                logout();
            }
            const errMsg = data.message || `Error ${res.status}`;
            showToast(errMsg, 'error');
            const err = new Error(errMsg);
            err.status = res.status;
            err.data = data;
            throw err;
        }

        return data;
    }

    /* ===== View Management ===== */
    function showView(viewId) {
        $$('.view').forEach(v => {
            v.classList.remove('active');
            v.classList.add('hidden');
        });
        const el = $(`#${viewId}`);
        if (el) {
            el.classList.remove('hidden');
            el.classList.add('active');
        }
    }

    function showPage(pageId) {
        if (!canAccessPage(pageId)) {
            showToast(`Please complete the previous steps first.`, 'warning');
            return;
        }

        $$('.page').forEach(p => { p.classList.remove('active'); p.classList.add('hidden'); });
        const el = $(`#${pageId}Page`);
        if (el) { el.classList.remove('hidden'); el.classList.add('active'); }
        $$('.nav-link').forEach(l => l.classList.remove('active'));
        const link = $(`.nav-link[data-view="${pageId}"]`);
        if (link) link.classList.add('active');

        // Refresh lock state on navigation
        enforceFlow();
    }

    function canAccessPage(pageId) {
        if (pageId === 'dashboard') return true;
        if (pageId === 'resume') return true;
        const hasResume = state.activeResumeSkills && state.activeResumeSkills.length > 0;
        return hasResume; // Simplified for retake support
    }

    function enforceFlow() {
        const hasResume = state.activeResumeSkills && state.activeResumeSkills.length > 0;
        const navQuiz = $('.nav-link[data-view="quiz"]');
        const navCoding = $('.nav-link[data-view="coding"]');
        const navInterview = $('.nav-link[data-view="interview"]');

        if (navQuiz) navQuiz.classList.toggle('locked', !hasResume);
        if (navCoding) navCoding.classList.toggle('locked', !hasResume);
        if (navInterview) navInterview.classList.toggle('locked', !hasResume);
    }

    /* ===== Auth ===== */
    function initAuth() {
        console.log('initAuth called');

        // If already logged in, go straight to app
        if (state.token && state.user) {
            enterApp();
            return;
        }
        showView('authView');

        // Switch between login / register
        window.switchAuth = (mode) => {
            const authWrapper = document.querySelector('.auth-wrapper');
            if (mode === 'register') {
                authWrapper.classList.add('toggled');
            } else {
                authWrapper.classList.remove('toggled');
                // Clear OTP timer when switching to login
                if (otpTimer) {
                    clearInterval(otpTimer);
                    otpTimer = null;
                }
                if (otpCountdown) otpCountdown.style.display = 'none';
                if (sendOtpBtn) sendOtpBtn.style.display = 'none';
            }
        };

        $('#showRegister')?.addEventListener('click', e => {
            e.preventDefault();
            window.switchAuth('register');
        });
        $('#showLogin')?.addEventListener('click', e => {
            e.preventDefault();
            window.switchAuth('login');
        });

        // -------- PASSWORD UTILS --------
        const initPasswordTools = () => {
            // Toggle Visibility
            $$('.toggle-password').forEach(btn => {
                btn.addEventListener('click', () => {
                    const input = $(`#${btn.dataset.target}`);
                    if (!input) return;

                    if (input.type === 'password') {
                        input.type = 'text';
                        btn.classList.remove('fa-eye');
                        btn.classList.add('fa-eye-slash');
                    } else {
                        input.type = 'password';
                        btn.classList.remove('fa-eye-slash');
                        btn.classList.add('fa-eye');
                    }
                });
            });

            // Strength Meter
            const regPass = $('#regPassword');
            const meter = $('#password-strength');
            const bar = $('#strength-bar');
            const text = $('#strength-text');

            regPass?.addEventListener('input', () => {
                const val = regPass.value;
                if (!val) {
                    meter.classList.remove('active');
                    return;
                }

                meter.classList.add('active');
                let score = 0;
                if (val.length > 6) score++;
                if (val.length > 10) score++;
                if (/[A-Z]/.test(val)) score++;
                if (/[0-9]/.test(val)) score++;
                if (/[^A-Za-z0-9]/.test(val)) score++;

                const levels = [
                    { color: '#ff4d4d', width: '20%', label: 'Very Weak - Use symbols/numbers' },
                    { color: '#ff4d4d', width: '40%', label: 'Weak - Longer is better' },
                    { color: '#ffa500', width: '60%', label: 'Medium - Add uppercase letters' },
                    { color: '#2ecc71', width: '80%', label: 'Strong - Good password' },
                    { color: '#00d4ff', width: '100%', label: 'Very Strong! ✨' }
                ];

                const level = levels[Math.min(score, 4)];
                bar.style.backgroundColor = level.color;
                bar.style.width = level.width;
                text.textContent = level.label;
            });
        };
        // -------- USERNAME UTILS --------
        const initUsernameTools = () => {
            const fields = [$('#loginUsername'), $('#regUsername')];
            fields.forEach(field => {
                field?.addEventListener('input', () => {
                    if (/\d/.test(field.value)) {
                        showToast('Only letters are allowed in the username!', 'warning');
                        field.value = field.value.replace(/\d/g, '');
                    }
                });
            });
        };
        initUsernameTools();
        initPasswordTools();

        // -------- LOGIN --------
        window.handleLogin = async (e) => {
            if (e) e.preventDefault();
            const btn = $('#loginFormInner button[type="submit"]');
            const errEl = $('#loginError');
            const username = $('#loginUsername').value.trim();
            const password = $('#loginPassword').value.trim();

            errEl.classList.add('hidden');
            if (!username || !password) {
                errEl.textContent = 'Please enter both username and password';
                errEl.classList.remove('hidden');
                return;
            }

            if (username.length < 3) {
                errEl.textContent = 'Username must be at least 3 characters long';
                errEl.classList.remove('hidden');
                return;
            }

            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner"></span> Signing in...';
            }

            try {
                const data = await api('/api/auth/login', {
                    method: 'POST',
                    body: { username, password }
                });
                state.token = data.token;
                state.user = data.user;
                sessionStorage.setItem('token', data.token);
                sessionStorage.setItem('user', JSON.stringify(data.user));
                showToast(`Welcome back, ${data.user.username}!`, 'success');
                enterApp();
            } catch (err) {
                errEl.textContent = err.message || 'Login failed';
                errEl.classList.remove('hidden');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = 'Login';
                }
            }
        };

        // -------- REGISTER --------
        const sendOtpBtn = $('#sendOtpBtn');
        const regEmail = $('#regEmail');
        const regOTP = $('#regOTP');
        const otpCountdown = $('#otpCountdown');
        let otpTimer = null;

        const startOtpTimer = (seconds) => {
            if (otpTimer) clearInterval(otpTimer);
            otpCountdown.style.display = 'block';
            sendOtpBtn.style.display = 'none';

            let timeLeft = seconds;
            otpCountdown.textContent = `${timeLeft}s`;

            otpTimer = setInterval(() => {
                timeLeft--;
                otpCountdown.textContent = `${timeLeft}s`;
                if (timeLeft <= 0) {
                    clearInterval(otpTimer);
                    otpCountdown.style.display = 'none';
                    sendOtpBtn.style.display = 'block';
                    sendOtpBtn.textContent = 'Resend';
                }
            }, 1000);
        };

        const triggerSendOtp = async () => {
            if (otpTimer) return; // Don't send if timer is running

            const email = regEmail.value.trim();
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            if (emailRegex.test(email)) {
                try {
                    sendOtpBtn.disabled = true;
                    sendOtpBtn.textContent = 'Sending...';
                    await api('/api/auth/send-otp', {
                        method: 'POST',
                        body: { email }
                    });
                    showToast('OTP sent to your email!', 'success');
                    startOtpTimer(60); // 60 seconds timer
                } catch (err) {
                    showToast(err.message || 'Failed to send OTP', 'error');
                } finally {
                    sendOtpBtn.disabled = false;
                }
            }
        };

        regEmail?.addEventListener('input', () => {
            if (regEmail.value.trim().includes('@')) {
                sendOtpBtn.style.display = 'block';
            } else {
                sendOtpBtn.style.display = 'none';
            }
        });

        regEmail?.addEventListener('blur', triggerSendOtp);
        sendOtpBtn?.addEventListener('click', triggerSendOtp);

        window.handleRegister = async (e) => {
            if (e) e.preventDefault();
            const btn = $('#registerFormInner button[type="submit"]');
            const errEl = $('#regError');
            const username = $('#regUsername').value.trim();
            const email = $('#regEmail').value.trim();
            const password = $('#regPassword').value.trim();
            const otp = $('#regOTP').value.trim();

            errEl.classList.add('hidden');
            if (!username || !email || !password || !otp) {
                errEl.textContent = 'Please fill in all fields including OTP';
                errEl.classList.remove('hidden');
                return;
            }

            // Username validation
            const usernameRegex = /^[a-zA-Z]{3,}$/;
            if (!usernameRegex.test(username)) {
                errEl.textContent = 'Username must be at least 3 characters long';
                errEl.classList.remove('hidden');
                return;
            }

            // Email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                errEl.textContent = 'Please enter a valid email address';
                errEl.classList.remove('hidden');
                return;
            }

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Creating Account...';

            try {
                const data = await api('/api/auth/register', {
                    method: 'POST',
                    body: { username, email, password, otp }
                });

                // Show success toast and switch to login view
                showToast(`Your account has been created successfully! Please sign in.`, 'success');
                window.switchAuth('login');
                $('#registerFormInner').reset();

            } catch (err) {
                errEl.textContent = err.message || 'Registration failed';
                errEl.classList.remove('hidden');
            } finally {
                btn.disabled = false;
                btn.innerHTML = 'Register';
            }
        };
        $('#loginFormInner')?.addEventListener('submit', window.handleLogin);
        $('#registerFormInner')?.addEventListener('submit', window.handleRegister);

        // -------- FORGOT PASSWORD --------
        const forgotPasswordForm = $('#forgotPasswordForm');
        const loginFormInner = $('#loginFormInner');
        const forgotEmailInput = $('#forgotEmail');
        const resetOTPInput = $('#resetOTP');
        const resetNewPasswordInput = $('#resetNewPassword');
        const resetConfirmPasswordInput = $('#resetConfirmPassword');
        const resetOtpWrapper = $('#resetOtpWrapper');
        const resetPasswordWrapper = $('#resetPasswordWrapper');
        const resetConfirmPasswordWrapper = $('#resetConfirmPasswordWrapper');
        const forgotSubmitBtn = $('#forgotSubmitBtn');
        const forgotError = $('#forgotError');
        const forgotStepDesc = $('#forgotStepDesc');
        const resetSuccessModal = $('#resetSuccessModal');
        const resetSuccessOkBtn = $('#resetSuccessOkBtn');

        const updateInputState = (input) => {
            if (!input) return;
            const wrapper = input.closest('.field-wrapper');
            if (wrapper) {
                if (input.value.trim() !== '') {
                    wrapper.classList.add('has-value');
                } else {
                    wrapper.classList.remove('has-value');
                }
            }
        };

        // Initialize state for all inputs and add listeners
        $$('.field-wrapper input').forEach(input => {
            updateInputState(input);
            input.addEventListener('input', () => updateInputState(input));
            input.addEventListener('blur', () => updateInputState(input));
            input.addEventListener('change', () => updateInputState(input));
        });

        $('#forgotPasswordTrigger')?.addEventListener('click', (e) => {
            e.preventDefault();
            loginFormInner.classList.add('hidden');
            forgotPasswordForm.classList.remove('hidden');
            $('#welcomeSignIn')?.classList.add('hidden');
            // Ensure inputs in the newly shown form have correct state
            setTimeout(() => {
                forgotPasswordForm.querySelectorAll('input').forEach(updateInputState);
            }, 50);

            // Re-init password tools to catch newly visible eye icons
            if (typeof initPasswordTools === 'function') initPasswordTools();
        });

        // ... intermediate listeners ...
        // Real-time email validation for forgot password
        forgotEmailInput?.addEventListener('input', () => {
            updateInputState(forgotEmailInput);
            const email = forgotEmailInput.value.trim();
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            const warning = $('#forgotEmailWarning');
            if (email && !emailRegex.test(email)) {
                warning?.classList.remove('hidden');
            } else {
                warning?.classList.add('hidden');
            }
        });

        // Real-time password strength for reset
        resetNewPasswordInput?.addEventListener('input', () => {
            updateInputState(resetNewPasswordInput);
            const pass = resetNewPasswordInput.value;
            const warning = $('#resetPasswordWarning');
            if (pass && pass.length < 6) {
                warning?.classList.remove('hidden');
                warning.textContent = 'Minimum 6 characters required';
            } else {
                warning?.classList.add('hidden');
            }
        });

        $('#backToLogin')?.addEventListener('click', (e) => {
            e.preventDefault();
            forgotPasswordForm.classList.add('hidden');
            loginFormInner.classList.remove('hidden');
            $('#welcomeSignIn')?.classList.remove('hidden');
            // Reset state
            forgotEmailInput.disabled = false;
            resetOtpWrapper.classList.add('hidden');
            resetPasswordWrapper.classList.add('hidden');
            resetConfirmPasswordWrapper.classList.add('hidden');
            forgotSubmitBtn.textContent = 'Send OTP';
            forgotError.classList.add('hidden');
            if (forgotStepDesc) forgotStepDesc.textContent = 'Enter your email to receive a secure reset OTP.';
            forgotPasswordForm.reset();
            // Clear has-value classes
            forgotPasswordForm.querySelectorAll('.field-wrapper').forEach(w => w.classList.remove('has-value'));

            // Clear timer
            if (resetOtpTimerInterval) {
                clearInterval(resetOtpTimerInterval);
                resetOtpTimerInterval = null;
            }
            resetOtpTimerEl?.classList.add('hidden');
            resendResetOtpBtn?.classList.add('hidden');
        });

        // OTP Timer for Reset
        let resetOtpTimerInterval = null;
        const resetOtpTimerEl = $('#resetOtpTimer');
        const resendResetOtpBtn = $('#resendResetOtp');

        const startResetOtpTimer = (seconds) => {
            if (resetOtpTimerInterval) clearInterval(resetOtpTimerInterval);
            resendResetOtpBtn.classList.add('hidden');
            resetOtpTimerEl.classList.remove('hidden');

            let timeLeft = seconds;
            resetOtpTimerEl.textContent = `${timeLeft}s`;

            resetOtpTimerInterval = setInterval(() => {
                timeLeft--;
                resetOtpTimerEl.textContent = `${timeLeft}s`;
                if (timeLeft <= 0) {
                    clearInterval(resetOtpTimerInterval);
                    resetOtpTimerEl.classList.add('hidden');
                    resendResetOtpBtn.classList.remove('hidden');
                }
            }, 1000);
        };

        resendResetOtpBtn?.addEventListener('click', async () => {
            const email = forgotEmailInput.value.trim();
            resendResetOtpBtn.disabled = true;
            resendResetOtpBtn.textContent = 'Sending...';
            try {
                await api('/api/auth/forgot-password', {
                    method: 'POST',
                    body: { email }
                });
                showToast('New OTP sent!', 'success');
                startResetOtpTimer(60);
            } catch (err) {
                showToast(err.message || 'Failed to resend OTP', 'error');
            } finally {
                resendResetOtpBtn.disabled = false;
                resendResetOtpBtn.textContent = 'Resend';
            }
        });

        forgotPasswordForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = forgotEmailInput.value.trim();
            const otp = resetOTPInput.value.trim();
            const password = resetNewPasswordInput.value.trim();
            const confirmPassword = resetConfirmPasswordInput.value.trim();

            forgotError.classList.add('hidden');

            // Phase 1: Send OTP
            if (resetOtpWrapper.classList.contains('hidden') && resetPasswordWrapper.classList.contains('hidden')) {
                if (!email) {
                    forgotEmailInput.reportValidity();
                    return;
                }
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(email)) {
                    showToast('Please enter a valid email address', 'error');
                    return;
                }
                forgotSubmitBtn.disabled = true;
                forgotSubmitBtn.innerHTML = '<span class="spinner"></span> Sending...';
                try {
                    await api('/api/auth/forgot-password', {
                        method: 'POST',
                        body: { email }
                    });
                    showToast('Reset OTP sent to your email', 'success');
                    forgotEmailInput.disabled = true;
                    resetOtpWrapper.classList.remove('hidden');
                    resetPasswordWrapper.classList.add('hidden');
                    resetConfirmPasswordWrapper.classList.add('hidden');
                    forgotSubmitBtn.textContent = 'Verify OTP';
                    if (forgotStepDesc) {
                        forgotStepDesc.innerHTML = `We've sent a 6-digit code to <strong style="color:var(--primary)">${email}</strong>.`;
                    }
                    startResetOtpTimer(60);
                    resetOTPInput.focus();
                } catch (err) {
                    forgotError.textContent = err.message || 'Failed to send OTP';
                    forgotError.classList.remove('hidden');
                    showToast(err.message || 'Failed to send OTP', 'error');
                } finally {
                    forgotSubmitBtn.disabled = false;
                }
            }
            // Phase 2: Verify OTP
            else if (resetPasswordWrapper.classList.contains('hidden')) {
                if (!otp) {
                    resetOTPInput.reportValidity();
                    return;
                }
                forgotSubmitBtn.disabled = true;
                forgotSubmitBtn.innerHTML = '<span class="spinner"></span> Verifying...';
                try {
                    await api('/api/auth/verify-reset-otp', {
                        method: 'POST',
                        body: { email, otp }
                    });
                    showToast('OTP verified successfully', 'success');
                    resetOtpWrapper.classList.add('hidden'); // Hide OTP after verification
                    if (resetOtpTimerInterval) clearInterval(resetOtpTimerInterval);
                    resetOtpTimerEl.classList.add('hidden');
                    resendResetOtpBtn.classList.add('hidden');

                    resetPasswordWrapper.classList.remove('hidden');
                    resetConfirmPasswordWrapper.classList.remove('hidden');
                    forgotSubmitBtn.textContent = 'Reset Password';
                    if (forgotStepDesc) {
                        forgotStepDesc.textContent = 'Almost there! Choose a strong new password to secure your account.';
                    }
                    resetNewPasswordInput.focus();
                } catch (err) {
                    forgotError.textContent = err.message || 'Invalid OTP';
                    forgotError.classList.remove('hidden');
                    showToast(err.message || 'Invalid OTP', 'error');
                } finally {
                    forgotSubmitBtn.disabled = false;
                }
            }
            // Phase 3: Final Reset Password
            else {
                if (!password) {
                    resetNewPasswordInput.reportValidity();
                    return;
                }
                if (!confirmPassword) {
                    resetConfirmPasswordInput.reportValidity();
                    return;
                }
                if (password !== confirmPassword) {
                    showToast('Passwords do not match', 'error');
                    return;
                }
                if (password.length < 6) {
                    showToast('Password must be at least 6 characters', 'error');
                    return;
                }

                forgotSubmitBtn.disabled = true;
                forgotSubmitBtn.innerHTML = '<span class="spinner"></span> Resetting...';
                try {
                    await api('/api/auth/reset-password', {
                        method: 'POST',
                        body: { email, otp, password }
                    });

                    // Show success modal instead of immediate redirect
                    resetSuccessModal?.classList.remove('hidden');

                    // Add listener for OK button
                    resetSuccessOkBtn?.addEventListener('click', () => {
                        resetSuccessModal?.classList.add('hidden');
                        $('#backToLogin').click();
                    }, { once: true });

                } catch (err) {
                    forgotError.textContent = err.message || 'Reset failed';
                    forgotError.classList.remove('hidden');
                    showToast(err.message || 'Reset failed', 'error');
                } finally {
                    forgotSubmitBtn.disabled = false;
                }
            }
        });

        // Real-time matching validation
        const validateMatching = () => {
            const warning = $('#resetPasswordWarning');
            if (resetNewPasswordInput.value && resetConfirmPasswordInput.value) {
                if (resetNewPasswordInput.value !== resetConfirmPasswordInput.value) {
                    warning?.classList.remove('hidden');
                    warning.style.color = 'var(--danger)';
                    warning.textContent = 'Passwords do not match';
                } else if (resetNewPasswordInput.value.length < 6) {
                    warning?.classList.remove('hidden');
                    warning.style.color = 'var(--danger)';
                    warning.textContent = 'Minimum 6 characters required';
                } else {
                    warning?.classList.add('hidden');
                }
            }
        };
        resetConfirmPasswordInput?.addEventListener('input', () => {
            updateInputState(resetConfirmPasswordInput);
            validateMatching();
        });
        resetNewPasswordInput?.addEventListener('input', validateMatching);
    }


    function enterApp() {
        showView('mainView');
        const greeting = $('#userGreeting');
        if (greeting && state.user) greeting.textContent = `Hi, ${state.user.username}`;

        sessionStorage.setItem('hasVisited', '1');
        showPage('dashboard');
        loadDashboard();
    }

    function logout() {
        state.token = null;
        state.user = null;
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('user');
        sessionStorage.removeItem('hasVisited'); // Clear so next login starts fresh
        showView('authView');
    }

    /* ===== Navigation ===== */
    function initNav() {
        $$('.nav-link').forEach(link => {
            link.addEventListener('click', e => {
                e.preventDefault();
                const view = link.dataset.view;
                showPage(view);
                if (view === 'dashboard') loadDashboard();
                if (view === 'coding') loadCodingProblems();
            });
        });
        $('#logoutBtn')?.addEventListener('click', logout);
        $('#generateReportBtn')?.addEventListener('click', generateReport);
    }

    /* ===== Dashboard ===== */
    let radarChart = null;
    let lineChart = null;

    async function loadDashboard() {
        try {
            const data = await api('/api/dashboard/stats');
            const r = data.report;

            if (r) {
                if (r.marks) {
                    $('#statResume').textContent = r.marks.resume;
                    $('#statQuiz').textContent = r.marks.quiz;
                    $('#statCoding').textContent = r.marks.coding;
                    $('#statInterview').textContent = r.marks.interview;
                    $('#statFinal').textContent = r.marks.total;
                } else {
                    // Fallback to percentage if marks not available
                    $('#statQuiz').textContent = `${(r.quiz_score || 0).toFixed(0)}%`;
                    $('#statCoding').textContent = `${(r.coding_score || 0).toFixed(0)}%`;
                    $('#statInterview').textContent = `${(r.interview_score || 0).toFixed(0)}%`;
                    $('#statFinal').textContent = `${(r.final_score || 0).toFixed(0)}%`;
                }

                const bar = $('#readinessBar');
                if (bar) bar.style.width = `${r.final_score || 0}%`;
                const txt = $('#readinessText');
                if (txt) txt.textContent = `Your interview readiness score: ${(r.final_score || 0).toFixed(1)}%`;

                // Skill gaps
                const gapList = $('#skillGapsList');
                if (gapList && r.analysis && r.analysis.length) {
                    gapList.innerHTML = r.analysis.map(g => `
                        <li>
                            <div class="gap-item">
                                <span class="gap-category">${g.category}</span>
                                <span class="gap-status status-${g.status.toLowerCase()}">${g.status}</span>
                                <p class="gap-suggestion">${g.suggestion}</p>
                            </div>
                        </li>
                    `).join('');
                }

                // Radar chart
                renderRadar(r);

                // Actionable Guidance
                const readinessText = $('#readinessText');
                if (readinessText) {
                    if (r.final_score > 80) readinessText.innerHTML = `<span style="color:var(--accent)">Excellent! You're ready for top-tier interviews.</span> Focus on niche system design.`;
                    else if (r.final_score > 60) readinessText.innerHTML = `Good progress! <a href="#" onclick="showPage('coding')">Practice more Coding</a> to reach 80%.`;
                    else readinessText.innerHTML = `Let's keep growing. <a href="#" onclick="showPage('resume')">Update your Resume</a> or <a href="#" onclick="showPage('quiz')">Take a Quiz</a>.`;
                }
            }

            // Skills
            if (data.skills && data.skills.length) {
                const el = $('#dashboardSkills');
                if (el) el.innerHTML = data.skills.map(s => `<span class="tag">${s}</span>`).join('');
            }

            // Line chart with history
            if (data.quiz_history) renderLine(data.quiz_history);

        } catch {
            // silently fail — user may not have data yet
        }
    }

    async function generateReport() {
        const btn = $('#generateReportBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Generating...';

        try {
            const data = await api('/api/dashboard/stats');
            const r = data.report;
            if (!r) throw new Error('No assessment data found. Please complete all sections.');

            const reportWindow = window.open('', '_blank');
            const html = `
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Interview Readiness Report - ${state.user.username}</title>
                    <style>
                        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #333; line-height: 1.6; }
                        .header { text-align: center; margin-bottom: 40px; border-bottom: 2px solid #6366f1; padding-bottom: 20px; }
                        .header h1 { color: #6366f1; margin: 0; }
                        .section { margin-bottom: 30px; background: #f9f9fb; padding: 20px; border-radius: 12px; }
                        .section h3 { margin-top: 0; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; }
                        .marks-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
                        .mark-item { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
                        .mark-val { font-size: 24px; font-weight: bold; color: #6366f1; }
                        .total-score { text-align: center; font-size: 32px; font-weight: 800; color: #10b981; margin: 20px 0; }
                        .analysis-item { margin-bottom: 15px; }
                        .status-strong { color: #10b981; font-weight: 600; }
                        .status-moderate { color: #f59e0b; font-weight: 600; }
                        .status-weak { color: #ef4444; font-weight: 600; }
                        @media print { .no-print { display: none; } }
                        .btn-print { background: #6366f1; color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }
                    </style>
                </head>
                <body>
                    <div class="no-print" style="margin-bottom: 20px;">
                        <button class="btn-print" onclick="window.print()">Print Report</button>
                    </div>
                    <div class="header">
                        <h1>Skill Mind AI | Interview Readiness Report</h1>
                        <p>Candidate: ${state.user.username} | Date: ${new Date().toLocaleDateString()}</p>
                    </div>

                    <div class="section">
                        <h3>Overall Performance</h3>
                        <div class="total-score">
                            Readiness Score: ${r.final_score.toFixed(1)}/100
                        </div>
                        <div class="marks-grid">
                            <div class="mark-item">
                                <strong>Resume Marks</strong>
                                <div class="mark-val">${r.marks?.resume || 0}/10</div>
                            </div>
                            <div class="mark-item">
                                <strong>Quiz Marks</strong>
                                <div class="mark-val">${r.marks?.quiz || 0}/30</div>
                            </div>
                            <div class="mark-item">
                                <strong>Coding Marks</strong>
                                <div class="mark-val">${r.marks?.coding || 0}/30</div>
                            </div>
                            <div class="mark-item">
                                <strong>Interview Marks</strong>
                                <div class="mark-val">${r.marks?.interview || 0}/30</div>
                            </div>
                        </div>
                    </div>

                    <div class="section">
                        <h3>Detailed Analysis & Recommendations</h3>
                        ${r.analysis.map(a => `
                            <div class="analysis-item">
                                <strong>${a.category}:</strong> <span class="status-${a.status.toLowerCase()}">${a.status}</span>
                                <p style="margin: 5px 0 0 0;">${a.suggestion}</p>
                            </div>
                        `).join('')}
                    </div>

                    <div class="section">
                        <h3>Skills Profile</h3>
                        <p>${data.skills && data.skills.length ? data.skills.join(', ') : 'No skills extracted yet.'}</p>
                    </div>

                    <div class="section">
                        <h3>Recommended Job Vacancies in India 🇮🇳</h3>
                        ${data.job_recommendations && data.job_recommendations.length ? data.job_recommendations.map(j => `
                            <div class="mark-item" style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong style="color: #6366f1; font-size: 1.1rem;">${j.role}</strong><br>
                                    <span style="color: #64748b;">${j.company} | ${j.location}</span>
                                </div>
                                <a href="${j.link}" target="_blank" style="background: #10b981; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 0.9rem; font-weight: 600;">Apply Now</a>
                            </div>
                        `).join('') : '<p>Complete assessment to see recommendations.</p>'}
                    </div>

                    <footer style="text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 50px;">
                        Generated by Skill Mind AI - Your Intelligent Interview Copilot
                    </footer>
                </body>
                </html>
            `;
            reportWindow.document.write(html);
            reportWindow.document.close();
            showToast('Report generated successfully!', 'success');
        } catch (err) {
            showToast(err.message || 'Failed to generate report', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Generate Report';
        }
    }

    function renderRadar(r) {
        const ctx = document.getElementById('radarChart');
        if (!ctx) return;
        if (radarChart) radarChart.destroy();

        radarChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Quiz', 'Coding', 'Interview', 'Resume'],
                datasets: [{
                    label: 'Score',
                    data: [r.quiz_score || 0, r.coding_score || 0, r.interview_score || 0, r.resume_strength || 0],
                    backgroundColor: 'rgba(99, 102, 241, 0.15)',
                    borderColor: '#6366f1',
                    borderWidth: 2,
                    pointBackgroundColor: '#6366f1',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: { color: '#64748b', backdropColor: 'transparent', stepSize: 25 },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        angleLines: { color: 'rgba(255,255,255,0.05)' },
                        pointLabels: { color: '#94a3b8', font: { size: 12, weight: 600 } }
                    }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    function renderLine(history) {
        const ctx = document.getElementById('lineChart');
        if (!ctx || !history.length) return;
        if (lineChart) lineChart.destroy();

        lineChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: history.map((_, i) => `Attempt ${i + 1}`),
                datasets: [{
                    label: 'Quiz Score',
                    data: history.map(h => h.score),
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#6366f1',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, max: 100, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    x: { ticks: { color: '#64748b' }, grid: { display: false } }
                },
                plugins: { legend: { labels: { color: '#94a3b8' } } }
            }
        });
    }

    /* ===== Resume Upload ===== */
    function initResume() {
        const dropZone = $('#resumeDropZone');
        const fileInput = $('#resumeFileInput');
        const fileNameEl = $('#resumeFileName');
        const statusEl = $('#resumeUploadStatus');
        const skillsPreview = $('#resumeSkillsPreview');
        const jdTextArea = $('#jdTextArea');

        if (!dropZone || !fileInput) return;

        // Restore JD if exists
        if (state.activeJD) jdTextArea.value = state.activeJD;

        // Restore skills preview if exists
        if (state.activeResumeSkills.length) {
            skillsPreview.innerHTML = state.activeResumeSkills.map(s => `<span class="tag">${s}</span>`).join('');
        }

        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', e => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                // Do NOT set fileInput.files here as it triggers a 'change' event
                // in some browsers AND we are already calling handleUpload.
                const file = e.dataTransfer.files[0];
                handleUpload(file);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files[0]) {
                handleUpload(fileInput.files[0]);
                // Clear the input so selecting the same file again triggers 'change'
                fileInput.value = '';
            }
        });

        async function handleUpload(file) {
            fileNameEl.textContent = `Selected: ${file.name}`;
            statusEl.classList.remove('hidden', 'success', 'error');
            statusEl.innerHTML = '<span class="spinner"></span> Analyzing Resume...';
            statusEl.classList.add('success');
            statusEl.classList.remove('hidden');

            const formData = new FormData();
            formData.append('file', file);
            formData.append('label', 'resume1'); // Default single label

            try {
                const data = await api('/api/resume/upload', { method: 'POST', body: formData });
                statusEl.innerHTML = `✅ Analyzed: ${file.name}`;
                statusEl.className = 'upload-status success';

                state.activeResumeSkills = data.skills || [];
                sessionStorage.setItem('activeResumeSkills', JSON.stringify(state.activeResumeSkills));

                if (skillsPreview) {
                    skillsPreview.innerHTML = state.activeResumeSkills.map(s => `<span class="tag">${s}</span>`).join('');
                }

                // Render Advanced Analysis
                if (data.resume_score !== undefined) {
                    $('#resumeAnalysisResult').classList.remove('hidden');
                    // $('#resAnalysisScore').textContent = Math.round(data.resume_score); // Replaced by updateCircularStrength
                    updateCircularStrength(Math.round(data.resume_score));
                    $('#resAnalysisScoreLabel').textContent = `Resume Strength: ${Math.round(data.resume_score)}/100`;

                    // Render Breakdown
                    const breakdown = data.score_breakdown || {};
                    const breakdownEl = $('#resAnalysisBreakdown');
                    breakdownEl.innerHTML = Object.entries(breakdown).map(([key, val]) => `
                        <div class="breakdown-item">
                            <div style="display:flex; justify-content:space-between; margin-bottom: 5px;">
                                <span style="font-size: 0.85rem; font-weight: 600; text-transform: capitalize;">${key}</span>
                                <span style="font-size: 0.8rem; color: var(--primary);">${Math.round(val)}%</span>
                            </div>
                            <div style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden;">
                                <div style="width: ${val}%; height: 100%; background: var(--primary-gradient); transition: width 0.8s ease;"></div>
                            </div>
                        </div>
                    `).join('');

                    // Store entities for tab switching
                    state.currentEntities = data.structured_data || {};
                    renderEntities('tech');

                    // Render Radar Chart
                    renderSkillRadar(data.technical_skills || []);

                    // Render Recommendations
                    renderRecommendations(data.recommendations || []);
                }

                showToast('Resume uploaded and analyzed!', 'success');
                enforceFlow();
            } catch (err) {
                statusEl.innerHTML = `❌ ${err.message || 'Upload failed'}`;
                statusEl.className = 'upload-status error';
            }
        }

        // Tab Switching Logic
        document.querySelectorAll('.btn-tab').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.btn-tab').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderEntities(btn.dataset.tab);
            });
        });

        function renderEntities(type) {
            const container = $('#entityContent');
            const entities = state.currentEntities || {};
            let html = '';

            if (type === 'tech') {
                const tech = Array.isArray(entities.technical_skills) ? entities.technical_skills : [];
                html = tech.length ? tech.map(s => `
                    <div class="entity-item" style="margin-bottom: 1.2rem; border-left: 2px solid var(--primary); padding-left: 1rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                            <strong style="color: #fff; font-size: 1rem;">${s.name || s}</strong>
                            <span style="font-size: 0.8rem; color: var(--primary); font-weight:700;">${s.confidence ? Math.round(s.confidence * 100) : 85}% Confidence</span>
                        </div>
                        <p style="font-size: 0.85rem; color: var(--text-muted); line-height:1.4; margin:0;">${s.reasoning || 'Heuristic skill extraction identified this core competency.'}</p>
                        <div style="height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; margin-top: 8px; overflow: hidden;">
                            <div style="width: ${s.confidence ? s.confidence * 100 : 85}%; height: 100%; background: var(--primary-gradient);"></div>
                        </div>
                    </div>
                `).join('') : '<p style="color: var(--text-dim);">No technical skills extracted.</p>';
            } else if (type === 'edu') {
                const edu = Array.isArray(entities.education) ? entities.education : (entities.education ? [entities.education] : []);
                html = edu.length ? edu.map(e => `
                    <div class="entity-item" style="margin-bottom: 1rem; border-left: 2px solid var(--primary); padding-left: 1rem;">
                        <div style="font-weight: 700; color: #fff;">${e.degree || 'Degree Unknown'}</div>
                        <div style="font-size: 0.9rem; color: var(--text-muted);">${e.institution || 'Institution Unknown'}</div>
                        ${e.year ? `<div style="font-size: 0.8rem; color: var(--primary);">${e.year}</div>` : ''}
                    </div>
                `).join('') : '<p style="color: var(--text-dim);">No educational data found.</p>';
            } else if (type === 'exp') {
                const exp = Array.isArray(entities.experience) ? entities.experience : (entities.roles ? entities.roles : (entities.experience ? (entities.experience.roles || []) : []));
                html = exp.length ? exp.map(e => `
                    <div class="entity-item" style="margin-bottom: 1rem; border-left: 2px solid var(--accent); padding-left: 1rem;">
                        <div style="font-weight: 700; color: #fff;">${e.title || 'Role Unknown'}</div>
                        <div style="font-size: 0.9rem; color: var(--text-muted);">${e.company || 'Company Unknown'}</div>
                        ${e.duration ? `<div style="font-size: 0.8rem; color: var(--accent);">${e.duration}</div>` : ''}
                    </div>
                `).join('') : '<p style="color: var(--text-dim);">No professional experience data found.</p>';
            } else if (type === 'proj') {
                const proj = Array.isArray(entities.projects) ? entities.projects : (entities.projects ? [entities.projects] : []);
                html = proj.length ? proj.map(p => `
                    <div class="entity-item" style="margin-bottom: 1rem; border-left: 2px solid var(--warning); padding-left: 1rem;">
                        <div style="font-weight: 700; color: #fff;">${p.name || 'Project Name Unknown'}</div>
                        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 5px;">${p.description || ''}</p>
                        ${p.technologies ? `<div style="margin-top: 5px;">${p.technologies.slice(0, 5).map(t => `<span class="tag xsmall-tag" style="font-size:10px; padding:2px 6px;">${t}</span>`).join('')}</div>` : ''}
                    </div>
                `).join('') : '<p style="color: var(--text-dim);">No project data found.</p>';
            }
            container.innerHTML = html;
        }

        $('#runCompareBtn')?.addEventListener('click', async () => {
            const jd = jdTextArea.value.trim();
            if (!jd) return showToast('Please paste a job description', 'warning');

            const btn = $('#runCompareBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Analyzing Resume & JD...';

            try {
                const data = await api('/api/resume/compare', {
                    method: 'POST',
                    body: { jd }
                });

                state.activeJD = jd;
                state.activeJDSkills = data.comparison[0].matching_skills.concat(data.comparison[0].missing_skills);
                sessionStorage.setItem('activeJD', jd);
                sessionStorage.setItem('activeJDSkills', JSON.stringify(state.activeJDSkills));

                // Show report
                $('#comparisonResult').classList.remove('hidden');
                $('#comparisonContent').innerHTML = `
                    <div class="comp-box" style="grid-column: 1 / -1;">
                        <div class="comp-header">
                            <div>
                                <strong style="font-size: 1.1rem; color: var(--primary);">Alignment Report</strong>
                                <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">Assessments are now tailored to this JD.</p>
                            </div>
                        </div>
                        <div class="comp-grid">
                            <div class="comp-section">
                                <h4>Matching Skills</h4>
                                <div class="comp-tags">
                                    ${data.comparison[0].matching_skills.length ? data.comparison[0].matching_skills.map(s => `<span class="comp-tag comp-match">${typeof s === 'object' ? s.skill : s}</span>`).join('') : '<span class="placeholder-text">None</span>'}
                                </div>
                            </div>
                            <div class="comp-section">
                                <h4>Missing Skills</h4>
                                <div class="comp-tags">
                                    ${data.comparison[0].missing_skills.length ? data.comparison[0].missing_skills.map(s => `<span class="comp-tag comp-missing">${typeof s === 'object' ? s.skill : s}</span>`).join('') : '<span class="placeholder-text">None</span>'}
                                </div>
                            </div>
                        </div>
                        ${data.comparison[0].insights ? `
                        <div class="comp-section" style="margin-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 1rem;">
                            <h4 style="margin-bottom: 0.5rem; color: var(--accent);">AI Insights & Fitment</h4>
                            <p style="font-size: 0.9rem; color: var(--text-muted); line-height: 1.5;">${data.comparison[0].insights}</p>
                        </div>
                        ` : ''}
                    </div>
                `;

                // Update Match Breakdown
                const bd = data.comparison[0].breakdown || {};
                const overallScore = Math.round(data.comparison[0].match_score);
                animateValue('mainMatchScore', 0, overallScore, 1000);

                const categories = [
                    { id: 'tech', key: 'technical' },
                    { id: 'exp', key: 'experience' },
                    { id: 'edu', key: 'education' },
                    { id: 'soft', key: 'soft_skills' }
                ];

                categories.forEach(cat => {
                    const score = Math.round(bd[cat.key] || 0);
                    animateValue(`${cat.id}MatchScore`, 0, score, 800);
                    const bar = document.getElementById(`${cat.id}MatchBar`);
                    if (bar) bar.style.width = score + '%';
                });

                // Render Visuals
                renderMatchMeter(data.comparison[0].match_score);
                renderSkillRadarDual(data.comparison[0].matching_skills, data.comparison[0].missing_skills);
                renderSkillMatrix(data.comparison[0].matching_skills, data.comparison[0].missing_skills);
                renderRecommendations(data.comparison[0].recommendations || []);
                renderXAI(data.comparison[0].explanation || []);

                showToast('Advanced JD Analysis Complete!', 'success');
            } catch (err) {
                showToast(err.message || 'Analysis failed', 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Compare & Sync Assessments';
            }
        });

        function renderSkillRadar(skills) {
            const ctx = document.getElementById('skillRadarChart');
            if (!ctx) return;

            // Destroy existing chart if any
            if (state.charts.radar) state.charts.radar.destroy();

            const labels = skills.slice(0, 6).map(s => s.skill);
            const values = skills.slice(0, 6).map(s => (s.confidence || 0.8) * 100);

            state.charts.radar = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: labels.length ? labels : ['Skill A', 'Skill B', 'Skill C'],
                    datasets: [{
                        label: 'Confidence Index (%)',
                        data: values.length ? values : [0, 0, 0],
                        backgroundColor: 'rgba(0, 212, 255, 0.2)',
                        borderColor: '#00d4ff',
                        pointBackgroundColor: '#00d4ff',
                        borderWidth: 2
                    }]
                },
                options: {
                    scales: {
                        r: {
                            angleLines: { color: 'rgba(255,255,255,0.1)' },
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            pointLabels: { color: '#888' },
                            ticks: { display: false, stepSize: 20 },
                            suggestedMin: 0,
                            suggestedMax: 100
                        }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }

        function renderRecommendations(recs) {
            const container = document.getElementById('recommendationsList');
            if (!container) return;

            container.innerHTML = recs.map(r => `
                <div class="rec-item" style="background: rgba(255,255,255,0.02); padding: 1rem; border-radius: 12px; border: 1px solid var(--glass-border); margin-bottom: 0.8rem; display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1;">
                        <span style="display: block; font-weight: 600; color: #fff;">${r.text || r}</span>
                    </div>
                    ${r.projected_increase ? `
                        <div style="text-align: right; margin-left:1rem;">
                            <span style="display: block; font-size: 0.7rem; color: var(--accent); font-weight: 800; text-transform: uppercase;">BOOST</span>
                            <span style="font-size: 1.1rem; font-weight: 800; color: var(--accent);">+${r.projected_increase}%</span>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        }

        function renderMatchMeter(score) {
            const ctx = document.getElementById('matchMeterChart');
            if (!ctx) return;

            if (state.charts.meter) state.charts.meter.destroy();

            state.charts.meter = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Match', 'Gap'],
                    datasets: [{
                        data: [score, 100 - score],
                        backgroundColor: ['#00d4ff', 'rgba(255,255,255,0.05)'],
                        borderWidth: 0,
                        circumference: 180,
                        rotation: 270,
                        cutout: '80%'
                    }]
                },
                options: {
                    aspectRatio: 1.5,
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false }
                    }
                }
            });
        }

        function renderXAI(explanation) {
            const list = $('#xaiList');
            if (!list) return;

            if (!explanation.length) {
                list.innerHTML = '<p style="color:var(--text-dim);">Detailed explainability data loading...</p>';
                return;
            }

            list.innerHTML = explanation.map(ex => `
                <div class="xai-item" style="padding: 10px; border-radius: 8px; background: ${ex.type === 'contributor' ? 'rgba(0,255,0,0.05)' : 'rgba(255,0,0,0.05)'}; border-left: 3px solid ${ex.type === 'contributor' ? '#4ade80' : '#f87171'};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:#fff;">${ex.skill}</strong>
                        <span style="font-size: 0.8rem; font-weight:700; color: ${ex.type === 'contributor' ? '#4ade80' : '#f87171'};">
                            ${ex.impact > 0 ? '+' : ''}${ex.impact}%
                        </span>
                    </div>
                    <p style="font-size: 0.8rem; color: var(--text-muted); margin-top:4px;">${ex.reason}</p>
                </div>
            `).join('');
        }

        function renderRecommendations(recs) {
            const section = $('#aiSuggestionsSection');
            const content = $('#aiSuggestionsContent');
            if (!section || !content) return;

            if (!recs || !recs.length) {
                section.classList.add('hidden');
                return;
            }

            section.classList.remove('hidden');
            content.innerHTML = recs.map(r => `
                <div class="rec-card" style="padding: 1rem; border-radius: 12px; background: rgba(255,255,255,0.03); border: 1px solid var(--glass-border);">
                    <div style="font-weight:700; color:var(--accent); margin-bottom:5px;">${r.skill}</div>
                    <div style="font-size:0.8rem; color:#fff; margin-bottom:8px;">${r.action}</div>
                    <div style="display:flex; justify-content:space-between; font-size: 0.75rem;">
                        <span style="color:var(--text-muted);">${r.platform}</span>
                        <span style="color:#4ade80; font-weight:700;">+${r.boost}% Boost</span>
                    </div>
                </div>
            `).join('');
        }

        function renderSkillBarChart(matching, missing) {
            const ctx = document.getElementById('skillBarChart');
            if (!ctx) return;

            if (state.charts.bar) state.charts.bar.destroy();

            const labels = [...matching.map(s => typeof s === 'object' ? s.skill : s), ...missing.map(s => typeof s === 'object' ? s.skill : s)].slice(0, 10);
            const dataValues = labels.map(l => matching.some(s => (typeof s === 'object' ? s.skill : s) === l) ? 100 : 20);

            state.charts.bar = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Skill Proficiency/Match',
                        data: dataValues,
                        backgroundColor: dataValues.map(v => v === 100 ? '#00d4ff' : 'rgba(255,100,100,0.1)'),
                        borderRadius: 5
                    }]
                },
                options: {
                    indexAxis: 'y',
                    scales: {
                        x: { display: false, max: 100 },
                        y: { ticks: { color: '#888' }, grid: { display: false } }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }

        function renderSkillRadarDual(matching, missing) {
            const ctx = document.getElementById('skillRadarChartDual');
            if (!ctx) return;

            if (state.charts.radar) state.charts.radar.destroy();

            const labels = [...matching.map(s => s.skill || s), ...missing.map(s => s.skill || s)].slice(0, 8);

            // Resume values (Matches are 90-100%, missing are 10-20%)
            const resumeData = labels.map(l => matching.some(s => (s.skill || s) === l) ? 95 : 15);
            // JD values (Requirements are always 100% target)
            const jdData = labels.map(() => 100);

            state.charts.radar = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Your Profile',
                            data: resumeData,
                            backgroundColor: 'rgba(0, 212, 255, 0.2)',
                            borderColor: '#00d4ff',
                            pointBackgroundColor: '#00d4ff',
                        },
                        {
                            label: 'Job Requirements',
                            data: jdData,
                            backgroundColor: 'rgba(168, 85, 247, 0.1)',
                            borderColor: '#a855f7',
                            borderDash: [5, 5],
                            pointBackgroundColor: '#a855f7',
                        }
                    ]
                },
                options: {
                    scales: {
                        r: {
                            min: 0,
                            max: 100,
                            ticks: { display: false },
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            angleLines: { color: 'rgba(255,255,255,0.05)' }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#fff', font: { size: 10 } } }
                    }
                }
            });
        }

        function renderSkillMatrix(matching, missing) {
            const tbody = document.getElementById('skillMatrixBody');
            if (!tbody) return;

            const rows = [];

            matching.forEach(s => {
                rows.push(`
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 1rem; color: #fff; font-weight: 600;">${s.skill || s}</td>
                        <td style="padding: 1rem; text-align: center;"><i class="fas fa-check-circle" style="color: #4ade80;"></i></td>
                        <td style="padding: 1rem; text-align: center; color: var(--text-muted);">${(s.weight || 0.5).toFixed(1)}</td>
                        <td style="padding: 1rem; text-align: center;"><span style="color: #4ade80;">Matched</span></td>
                    </tr>
                `);
            });

            missing.forEach(s => {
                const priorityColor = s.priority === 'High' ? '#f87171' : (s.priority === 'Medium' ? '#fbbf24' : '#60a5fa');
                rows.push(`
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 1rem; color: rgba(255,255,255,0.7);">${s.skill || s}</td>
                        <td style="padding: 1rem; text-align: center;"><i class="fas fa-times-circle" style="color: #f87171;"></i></td>
                        <td style="padding: 1rem; text-align: center; color: var(--text-muted);">${(s.weight || 0.5).toFixed(1)}</td>
                        <td style="padding: 1rem; text-align: center;"><span style="background: ${priorityColor}22; color: ${priorityColor}; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 700;">${s.priority || 'Low'}</span></td>
                    </tr>
                `);
            });

            tbody.innerHTML = rows.slice(0, 10).join('');
        }
    }

    async function handleJDComparison() {
        const jd = $('#jdInput').value.trim();
        const btn = $('#compareBtn');
        const resultWrap = $('#comparisonResult');
        const contentEl = $('#comparisonContent');

        if (!jd) {
            showToast('Please paste a job description first', 'warning');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Comparing...';

        try {
            const data = await api('/api/resume/compare', {
                method: 'POST',
                body: { jd }
            });

            resultWrap.classList.remove('hidden');
            contentEl.innerHTML = data.comparison.map(c => `
                <div class="comp-box">
                    <div class="comp-header">
                        <strong>${c.label === 'resume1' ? 'Resume 1' : 'Resume 2'}</strong>
                        <span class="comp-score">${c.match_score}% Match</span>
                    </div>
                    <div class="comp-sections">
                        <div class="comp-section">
                            <h4>Matching Skills</h4>
                            <div class="comp-tags">
                                ${c.matching_skills.length ? c.matching_skills.map(s => `<span class="comp-tag comp-match">${s}</span>`).join('') : '<span class="placeholder-text">None</span>'}
                            </div>
                        </div>
                        <div class="comp-section">
                            <h4>Missing Skills</h4>
                            <div class="comp-tags">
                                ${c.missing_skills.length ? c.missing_skills.map(s => `<span class="comp-tag comp-missing">${s}</span>`).join('') : '<span class="placeholder-text">None</span>'}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');

            showToast('Comparison report generated!', 'success');
        } catch (err) {
            showToast(err.message || 'Comparison failed', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Compare with Resumes';
        }
    }

    async function loadResumeOptions(resumes) {
        const select = $('#resumeSelect');
        if (!select) return;

        try {
            if (!resumes) {
                const data = await api('/api/resume/list');
                resumes = data.resumes;
            }

            select.innerHTML = '<option value="">Latest Overall</option>';
            resumes.forEach(r => {
                select.innerHTML += `<option value="${r.id}">${r.label === 'resume1' ? 'Resume 1' : 'Resume 2'} (${r.filename})</option>`;
            });
        } catch { }
    }

    /* ===== Quiz ===== */
    function initQuiz() {
        $('#startQuizBtn')?.addEventListener('click', startQuiz);
        $('#nextQuestionBtn')?.addEventListener('click', nextQuestion);
        $('#skipQuestionBtn')?.addEventListener('click', () => {
            state.quizResponses.push({ question: state.quizQuestions[state.quizIndex]?.question || '', answer: '' });
            state.quizIndex++;
            renderQuestion();
        });
        $('#retakeQuizBtn')?.addEventListener('click', () => {
            $('#quizResult').classList.add('hidden');
            $('#quizStart').classList.remove('hidden');
        });
    }

    async function startQuiz() {
        $('#quizStart').classList.add('hidden');
        $('#quizActive').classList.remove('hidden');
        $('#quizResult').classList.add('hidden');

        try {
            const data = await api(`/api/quiz/generate`, {
                method: 'POST',
                body: { jd: state.activeJD }
            });
            state.quizQuestions = data.questions || [];
            state.quizIndex = 0;
            state.quizResponses = [];
            renderQuestion();
            showToast('Quiz started! Contextualized to JD.', 'info');
        } catch (err) {
            alert(err.message || 'Failed to generate quiz. Sync a JD first.');
            $('#quizActive').classList.add('hidden');
            // ... (rest of logic handles reversal)
        }
    }

    function renderQuestion() {
        if (state.quizIndex >= state.quizQuestions.length) {
            submitQuiz();
            return;
        }

        const q = state.quizQuestions[state.quizIndex];
        $('#questionCounter').textContent = `Question ${state.quizIndex + 1} / ${state.quizQuestions.length}`;
        $('#questionSkill').textContent = q.skill;
        $('#questionText').textContent = q.question;
        $('#answerInput').value = '';
        $('#answerInput').focus();

        const pct = ((state.quizIndex) / state.quizQuestions.length) * 100;
        $('#quizProgressBar').style.width = `${pct}%`;

        startQuizTimer();
    }

    let quizTimerInterval = null;
    function startQuizTimer() {
        clearInterval(quizTimerInterval);
        let timeLeft = 90;
        const display = $('#quizTimer');
        const ring = $('.timer-ring');

        display.textContent = `${timeLeft}s`;
        display.style.color = 'var(--warning)';

        quizTimerInterval = setInterval(() => {
            timeLeft--;
            display.textContent = `${timeLeft}s`;

            if (timeLeft <= 10) {
                display.style.color = 'var(--danger)';
            }

            if (timeLeft <= 0) {
                clearInterval(quizTimerInterval);
                showToast('Time up for this question!', 'warning');
                nextQuestion();
            }
        }, 1000);
    }

    function nextQuestion() {
        clearInterval(quizTimerInterval);
        const answer = $('#answerInput').value.trim();
        state.quizResponses.push({
            question: state.quizQuestions[state.quizIndex]?.question || '',
            answer
        });
        state.quizIndex++;
        renderQuestion();
    }

    async function submitQuiz() {
        $('#quizActive').classList.add('hidden');
        $('#quizProgressBar').style.width = '100%';

        try {
            const data = await api('/api/quiz/submit', {
                method: 'POST',
                body: { responses: state.quizResponses }
            });

            const totalMarks = data.total_marks || 0;
            const maxMarks = data.max_marks || 30;
            const score = data.score || 0;
            $('#quizScoreDisplay').textContent = `${totalMarks}/${maxMarks}`;
            if (score >= 80) {
                $('#quizFeedback').textContent = `Excellent! You scored ${totalMarks}/${maxMarks} marks (${score.toFixed(0)}%). Strong technical knowledge!`;
            } else if (score >= 50) {
                $('#quizFeedback').textContent = `Good effort! You scored ${totalMarks}/${maxMarks} marks (${score.toFixed(0)}%). Some areas need more practice.`;
            } else {
                $('#quizFeedback').textContent = `You scored ${totalMarks}/${maxMarks} marks (${score.toFixed(0)}%). Keep studying! Focus on the fundamentals.`;
            }
            $('#quizResult').classList.remove('hidden');
            sessionStorage.setItem('quiz_completed', '1');
            enforceFlow();
        } catch {
            alert('Failed to submit quiz.');
            $('#quizStart').classList.remove('hidden');
        }
    }

    /* ===== Coding ===== */
    function initCoding() {
        $('#startCodingBtn')?.addEventListener('click', startCodingAssessment);
        $('#resetCodeBtn')?.addEventListener('click', () => {
            const p = state.codingChallenges[state.codingIndex];
            if (p) {
                $('#codeEditor').value = p.starter_code;
                $('#codeOutput').classList.add('hidden');
            }
        });

        $('#runCodeBtn')?.addEventListener('click', () => submitCodeForReview(false));
        $('#submitCodeBtn')?.addEventListener('click', () => submitCodeForReview(true));
        $('#retakeCodingBtn')?.addEventListener('click', () => {
            $('#codingResult').classList.add('hidden');
            $('#codingStart').classList.remove('hidden');
        });
    }

    async function startCodingAssessment() {
        $('#codingStart').classList.add('hidden');
        $('#codingActive').classList.remove('hidden');

        try {
            const data = await api('/api/coding/challenge-set', {
                method: 'POST',
                body: { jd: state.activeJD }
            });
            state.codingChallenges = data.challenges || [];
            state.codingIndex = 0;
            state.codingSubmissions = [];
            state.codingTotalMarks = 0;

            if (state.codingChallenges.length === 0) {
                throw new Error("No challenges found.");
            }

            renderProblem();
        } catch (err) {
            alert('Failed to load coding challenges.');
            $('#codingStart').classList.remove('hidden');
            $('#codingActive').classList.add('hidden');
        }
    }

    function renderProblem() {
        const p = state.codingChallenges[state.codingIndex];
        if (!p) return;

        // Update progress UI
        const currentNum = state.codingIndex + 1;
        const totalNum = state.codingChallenges.length;
        $('#codingProgress').textContent = `Question ${currentNum} / ${totalNum}`;
        $('#codingProgressBar').style.width = `${((currentNum - 1) / totalNum) * 100}%`;
        $('#codingMarksTracker').textContent = `Marks: ${state.codingTotalMarks}/30`;
        $('#codingQuestionLabel').textContent = `Q${currentNum}`;

        // Update problem content
        $('#currentProblemTitle').textContent = p.title;
        const diff = $('#currentProblemDifficulty');
        diff.textContent = p.difficulty;
        diff.className = `badge badge-${p.difficulty}`;

        $('#codingProblem').innerHTML = `<p>${p.description}</p>`;
        if (p.examples && p.examples.length) {
            $('#codingProblem').innerHTML += `
                <div style="margin-top:1rem;">
                    <strong>Example:</strong>
                    <pre><code>Input:  ${p.examples[0].input}\nOutput: ${p.examples[0].output}</code></pre>
                </div>
            `;
        }

        const hintsWrap = $('#codingHintsWrap');
        const hintsList = $('#codingHints');
        if (p.hints && p.hints.length) {
            hintsWrap.classList.remove('hidden');
            hintsList.innerHTML = p.hints.map(h => `<li>${h}</li>`).join('');
        } else {
            hintsWrap.classList.add('hidden');
        }

        $('#codeEditor').value = p.starter_code;
        $('#codeOutput').classList.add('hidden');
        $('#codeOutputText').innerHTML = '';

        // Scroll to top
        $('#codeEditor').scrollTop = 0;
    }

    async function submitCodeForReview(isNext) {
        const code = $('#codeEditor').value;
        const outputEl = $('#codeOutputText');
        const outputWrap = $('#codeOutput');
        const p = state.codingChallenges[state.codingIndex];

        outputWrap.classList.remove('hidden');
        outputEl.innerHTML = '<span class="spinner"></span> Evaluating...';

        try {
            const data = await api('/api/coding/submit', {
                method: 'POST',
                body: { code, problem_id: p.id }
            });

            const marks = data.marks || 0;

            let html = `<div style="margin-bottom:1rem;">
                <span style="font-weight:700;">Syntax:</span> ${data.is_valid ? '<span style="color:var(--accent)">✅ Valid</span>' : '<span style="color:var(--danger)">❌ ' + data.syntax_message + '</span>'}<br>
                <span style="font-weight:700;">Quality Score:</span> ${data.quality_report?.score}/100<br>
                <span style="font-weight:700;">Test Pass Rate:</span> ${data.test_score}%<br>
                <span style="font-weight:700; color:var(--accent);">Marks Earned:</span> ${marks} / 5
            </div>`;

            if (data.test_results && data.test_results.length) {
                html += `<div style="border-top: 1px solid var(--glass-border); padding-top:1rem;">
                    <h5 style="margin-bottom:0.5rem;">Test Cases:</h5>
                    <div style="display:flex; flex-direction:column; gap:0.5rem;">`;

                data.test_results.slice(0, 3).forEach(tc => {
                    const color = tc.passed ? 'var(--accent)' : 'var(--danger)';
                    html += `
                        <div style="font-size:0.85rem; padding:0.5rem; background:rgba(255,255,255,0.02); border-left:3px solid ${color};">
                            <div style="display:flex; justify-content:space-between;">
                                <strong>Test ${tc.test}</strong>
                                <span style="color:${color}; font-weight:700;">${tc.passed ? 'PASSED' : 'FAILED'}</span>
                            </div>
                        </div>
                    `;
                });
                if (data.test_results.length > 3) html += `<p style="font-size:0.75rem; color:var(--text-dim);">+ ${data.test_results.length - 3} more tests...</p>`;
                html += `</div></div>`;
            }

            outputEl.innerHTML = html;

            if (isNext) {
                state.codingSubmissions.push({ problem_id: p.id, code, marks });
                state.codingTotalMarks += marks;

                if (state.codingIndex < state.codingChallenges.length - 1) {
                    state.codingIndex++;
                    setTimeout(() => {
                        renderProblem();
                        showToast(`Problem ${state.codingIndex} submitted.`, 'success');
                    }, 1000);
                } else {
                    finishCodingAssessment();
                }
            } else {
                showToast('Draft tests completed.', 'info');
            }
        } catch (err) {
            outputEl.textContent = `Error: ${err.message || 'Submission failed'}`;
        }
    }

    async function finishCodingAssessment() {
        $('#codingActive').classList.add('hidden');
        $('#codingProgressBar').style.width = '100%';

        try {
            const data = await api('/api/coding/submit-all', {
                method: 'POST',
                body: { submissions: state.codingSubmissions }
            });

            const marksTotal = data.total_marks || state.codingTotalMarks;
            $('#codingScoreDisplay').textContent = `${marksTotal}/30`;

            const pct = data.score_pct || (marksTotal / 30 * 100);

            if (pct >= 80) {
                $('#codingFeedback').textContent = 'Stunning! You are a coding wizard. Ready for high-profile engineering roles.';
            } else if (pct >= 50) {
                $('#codingFeedback').textContent = 'Strong implementation. You have a solid grasp of algorithmic thinking.';
            } else {
                $('#codingFeedback').textContent = 'Keep practicing! Focus on common algorithms and clean code structure.';
            }

            let resultHtml = '<div class="marks-grid" style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:1rem;">';
            (data.results || []).forEach((r, idx) => {
                resultHtml += `<div class="mark-item" style="background:var(--glass); padding:10px; border-radius:8px;">
                    <strong>Q${idx + 1}:</strong> ${r.problem_title} <br>
                    <span style="color:var(--accent)">${r.marks}/5 marks</span>
                </div>`;
            });
            resultHtml += '</div>';
            $('#codingResultDetails').innerHTML = resultHtml;

            $('#codingResult').classList.remove('hidden');
            sessionStorage.setItem('coding_completed', '1');
            enforceFlow();
            showToast('Coding Assessment Finalized!', 'success');

            loadDashboard();
        } catch (err) {
            alert('Failed to conclude assessment.');
            $('#codingStart').classList.remove('hidden');
        }
    }

    /* ===== Interview ===== */
    function initInterview() {
        $('#startInterviewBtn')?.addEventListener('click', startInterview);
        $('#sendMsgBtn')?.addEventListener('click', sendMessage);
        $('#chatInput')?.addEventListener('keypress', e => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    async function startInterview() {
        state.interviewActive = true;

        // Clear welcome and show chat
        const msgs = $('#chatMessages');
        msgs.innerHTML = '';
        $('#chatInputWrap').classList.remove('hidden');

        try {
            const data = await api('/api/interview/start', {
                method: 'POST',
                body: { jd: state.activeJD }
            });
            appendMessage('ai', data.message);
            updateSentiment('NEUTRAL');
        } catch (err) {
            appendMessage('ai', 'Failed to start interview. Please try again.');
        }
    }

    async function sendMessage() {
        const input = $('#chatInput');
        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        appendMessage('user', message);

        try {
            const data = await api('/api/interview/respond', {
                method: 'POST',
                body: { message }
            });

            appendMessage('ai', data.message);
            updateSentiment(data.sentiment, data.sentiment_score);

            if (data.is_complete) {
                await endInterview();
            }
        } catch (err) {
            appendMessage('ai', 'Sorry, something went wrong. Please try again.');
        }
    }

    function resetInterviewUI() {
        const msgs = $('#chatMessages');
        msgs.innerHTML = `
            <div class="chat-welcome">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="1.5">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                <h3>AI Interview Room</h3>
                <p>Click "Start Interview" to begin your AI-powered HR interview session.</p>
                <button class="btn-primary" id="startInterviewBtn">Start Interview</button>
            </div>
        `;
        msgs.querySelector('#startInterviewBtn').onclick = startInterview;
        $('#chatInputWrap').classList.add('hidden');
        $('#chatInput').disabled = false;
        $('#chatInput').placeholder = 'Type your response...';
        updateSentiment('NEUTRAL');
    }

    async function endInterview() {
        try {
            const data = await api('/api/interview/end', {
                method: 'POST'
            });
            appendMessage('ai', `\n🎯 ${data.message}\n${data.feedback}`);
            state.interviewActive = false;
            $('#chatInput').disabled = true;
            $('#chatInput').placeholder = 'Interview completed';

            // Add a New Interview button at bottom of chat
            const btn = document.createElement('button');
            btn.className = 'btn-secondary';
            btn.style.margin = '1rem auto';
            btn.style.display = 'block';
            btn.textContent = 'Start New Session';
            btn.onclick = resetInterviewUI;
            $('#chatMessages').appendChild(btn);
            $('#chatMessages').scrollTop = $('#chatMessages').scrollHeight;

            sessionStorage.setItem('interview_completed', '1');
            enforceFlow();
            showToast('Interview completed and saved!', 'success');
        } catch {
            // ignore
        }
    }

    socket.on('analysis_progress', (data) => {
        const steps = {
            'extract': 'Extracting Resume Entities...',
            'embedding': 'Generating Embeddings...',
            'similarity': 'Calculating Similarity...',
            'gap': 'Analyzing Skill Gaps...',
            'recommendation': 'Generating Recommendations...',
            'xai': 'Analyzing Match Reasoning...',
            'normalization': 'Normalizing Skill Taxonomy...',
            'finalizing': 'Finalizing Intelligent Report...'
        };
        const message = steps[data.step] || data.message;
        updateStatus(message, 'info');
    });
    function appendMessage(role, text) {
        const msgs = $('#chatMessages');
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role}`;
        bubble.textContent = text;
        msgs.appendChild(bubble);
        msgs.scrollTop = msgs.scrollHeight;
    }

    function updateSentiment(label, score) {
        const emoji = $('#sentimentEmoji');
        const labelEl = $('#sentimentLabel');
        if (!emoji || !labelEl) return;

        const map = {
            'POSITIVE': { emoji: '😊', text: 'Positive' },
            'NEGATIVE': { emoji: '😟', text: 'Needs Work' },
            'NEUTRAL': { emoji: '😐', text: 'Neutral' }
        };
        const s = map[label] || map['NEUTRAL'];
        emoji.textContent = s.emoji;
        labelEl.textContent = s.text;
    }

    /* ===== Scoring / Report ===== */
    function initScoring() {
        $('#generateReportBtn')?.addEventListener('click', async () => {
            const btn = $('#generateReportBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Generating...';

            try {
                const data = await api('/api/scoring/generate-report', { method: 'POST' });

                // Update dashboard immediately
                if (data.marks) {
                    $('#statResume').textContent = data.marks.resume;
                    $('#statQuiz').textContent = data.marks.quiz;
                    $('#statCoding').textContent = data.marks.coding;
                    $('#statInterview').textContent = data.marks.interview;
                    $('#statFinal').textContent = data.marks.total;
                } else {
                    $('#statQuiz').textContent = `${(data.quiz_score || 0).toFixed(0)}%`;
                    $('#statCoding').textContent = `${(data.coding_score || 0).toFixed(0)}%`;
                    $('#statInterview').textContent = `${(data.interview_score || 0).toFixed(0)}%`;
                    $('#statFinal').textContent = `${(data.final_score || 0).toFixed(0)}%`;
                }

                const bar = $('#readinessBar');
                if (bar) bar.style.width = `${data.final_score || 0}%`;
                const txt = $('#readinessText');
                if (txt) txt.textContent = `Your interview readiness score: ${(data.final_score || 0).toFixed(1)}%`;

                if (data.analysis && data.analysis.length) {
                    const gapList = $('#skillGapsList');
                    if (gapList) {
                        gapList.innerHTML = data.analysis.map(g => `
                            <li>
                                <div class="gap-item">
                                    <span class="gap-category">${g.category}</span>
                                    <span class="gap-status status-${g.status.toLowerCase()}">${g.status}</span>
                                    <p class="gap-suggestion">${g.suggestion}</p>
                                </div>
                            </li>
                        `).join('');
                    }
                }

                renderRadar(data);
                showToast('Report generated successfully!', 'success');

                // Auto-navigate to top of dashboard
                setTimeout(() => {
                    showPage('dashboard');
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }, 1000);
            } catch (err) {
                alert(err.message || 'Failed to generate report. Complete some assessments first.');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Generate Report';
            }
        });
    }

    /* ===== Init ===== */
    document.addEventListener('DOMContentLoaded', () => {
        initAuth();
        initNav();
        initResume();
        initQuiz();
        initCoding();
        initInterview();
        initScoring();
    });
})();
