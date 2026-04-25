(() => {
    'use strict';
    console.log(">>> SKILLMIND FRONTEND RELOADED v2.5 (Dark Theme Enforced) <<<");

    // Dynamic API discovery: prefers localhost if currently on localhost, or uses 127.0.0.1 as default
    const API = window.location.hostname === 'localhost' ? 'http://localhost:5000' : 'http://127.0.0.1:5000';
    const socket = io('http://127.0.0.1:5000'); // Initialize Socket.IO connection to backend
    let monacoEditor;

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
        lastReport: null,
        resumeErrors: [], // New
        qualityMetrics: {}, // New
        selectedOption: null, // New for MCQs
        codingTimerInterval: null,
        codingTimeLeft: 600 // 10 minutes in seconds
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

    let globalRedirectTimer = null;
    function startRedirectTimer(buttonId, targetPage, text, seconds) {
        const btn = $(`#${buttonId}`);
        if (!btn) return;

        let timeLeft = seconds;
        if (globalRedirectTimer) clearInterval(globalRedirectTimer);

        const originalText = btn.textContent;
        const updateText = () => {
            btn.textContent = `${text} (${timeLeft}s)`;
        };

        updateText();
        globalRedirectTimer = setInterval(() => {
            timeLeft--;
            updateText();
            if (timeLeft <= 0) {
                clearInterval(globalRedirectTimer);
                showPage(targetPage);
            }
        }, 1000);
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
                signOut();
            }
            if (res.status === 422) {
                showToast('Authentication error. Please sign out and sign in again to refresh your session.', 'error');
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
        console.log('--- showPage:', pageId, '---');
        state.activePage = pageId;
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

        // Hide main navbar if interview and make it full height
        const navbar = $('.navbar');
        const interviewContainer = $('#interviewPage');
        if (pageId === 'interview') {
            console.log('showPage: Hiding navbar (interview mode)');
            if (navbar) {
                navbar.classList.add('hidden');
                navbar.style.display = 'none';
            } else {
                console.warn('showPage: Navbar element NOT found');
            }
            if (interviewContainer) interviewContainer.classList.add('full-height');
            document.body.classList.add('is-interview');
        } else {
            console.log('showPage: Showing navbar (standard mode)');
            if (navbar) {
                navbar.classList.remove('hidden');
                navbar.style.display = '';
            }
            if (interviewContainer) interviewContainer.classList.remove('full-height');
            document.body.classList.remove('is-interview');
        }

        // Manage Hardware Access (Commented out as React handles it now)
        /* 
        if (pageId === 'interview') {
            initHardware();
        } else {
            stopHardware();
        }
        */

        // Interview page: Init native interview module
        if (pageId === 'interview') {
            const token = state.token || sessionStorage.getItem('token');
            let userId = state.user?.id;
            if (!userId && sessionStorage.getItem('user')) {
                try { userId = JSON.parse(sessionStorage.getItem('user')).id; } catch (e) {}
            }
            if (token && userId && typeof Interview !== 'undefined') {
                Interview.init(token, userId);
                console.log('showPage: Interview module initialized for user', userId);
            }
        }

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

        // Navigation Links
        const navQuiz = $('.nav-link[data-view="quiz"]');
        const navCoding = $('.nav-link[data-view="coding"]');
        const navInterview = $('.nav-link[data-view="interview"]');

        if (navQuiz) navQuiz.classList.toggle('locked', !hasResume);
        if (navCoding) navCoding.classList.toggle('locked', !hasResume);
        if (navInterview) navInterview.classList.toggle('locked', !hasResume);

        // Resume & JD Inputs
        const jdArea = $('#jdTextArea');
        const compBtn = $('#runCompareBtn');

        if (jdArea) {
            if (hasResume) {
                jdArea.disabled = false;
                jdArea.removeAttribute('disabled');
                jdArea.placeholder = "Paste the job description here...";
            } else {
                jdArea.disabled = true;
                jdArea.setAttribute('disabled', 'true');
                jdArea.placeholder = "Please upload a resume first to enable this section...";
            }
        }

        if (compBtn) {
            if (hasResume) {
                compBtn.disabled = false;
                compBtn.removeAttribute('disabled');
            } else {
                compBtn.disabled = true;
                compBtn.setAttribute('disabled', 'true');
            }
        }
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
            const field = $('#regUsername');
            field?.addEventListener('input', () => {
                if (/\d/.test(field.value)) {
                    showToast('Only letters are allowed in the username!', 'warning');
                    field.value = field.value.replace(/\d/g, '');
                }
            });
        };
        initUsernameTools();
        initPasswordTools();

        // -------- LOGIN --------
        window.handleLogin = async (e) => {
            if (e) e.preventDefault();
            const btn = $('#loginFormInner button[type="submit"]');
            const errEl = $('#loginError');
            const email = $('#loginEmail').value.trim();
            const password = $('#loginPassword').value.trim();

            errEl.classList.add('hidden');
            if (!email || !password) {
                errEl.textContent = 'Please enter both email and password';
                errEl.classList.remove('hidden');
                return;
            }

            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                errEl.textContent = 'Please enter a valid email address';
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
                    body: { email, password }
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
        const regOtpIcon = $('#regOtpIcon');
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
                    otpTimer = null; // Fix: Allow resending after timer expires
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
                if (regOtpIcon) regOtpIcon.style.opacity = '0';
            } else {
                sendOtpBtn.style.display = 'none';
                if (regOtpIcon) regOtpIcon.style.opacity = '1';
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

        // -------- REAL-TIME OTP VALIDATION --------
        const setupOtpValidation = (inputEl, statusEl, emailSourceEl, onValid) => {
            if (!inputEl || !statusEl) return;

            inputEl.addEventListener('input', async () => {
                const val = inputEl.value.trim();
                const email = emailSourceEl?.value.trim();

                // Enforce numeric only and max 6 digits
                const sanitized = val.replace(/\D/g, '').substring(0, 6);
                if (val !== sanitized) {
                    inputEl.value = sanitized;
                }

                // Clear status if empty or too short
                if (sanitized.length < 6) {
                    statusEl.className = 'otp-status-icon';
                    return;
                }
                
                if (sanitized.length === 6 && email) {
                    try {
                        const res = await api('/api/auth/verify-otp-instant', {
                            method: 'POST',
                            body: { email, otp: sanitized }
                        });
                        
                        if (res.valid) {
                            statusEl.className = 'otp-status-icon valid';
                            if (onValid) onValid(); // Stop the timer if valid
                        } else {
                            statusEl.className = 'otp-status-icon invalid';
                        }
                    } catch (err) {
                        statusEl.className = 'otp-status-icon invalid';
                    }
                }
            });
        };

        setupOtpValidation($('#regOTP'), $('#regOtpStatus'), $('#regEmail'), () => {
            if (otpTimer) {
                clearInterval(otpTimer);
                otpTimer = null;
                $('#otpCountdown').style.display = 'none';
            }
        });
        
        setupOtpValidation($('#resetOTP'), $('#resetOtpStatus'), $('#forgotEmail'), () => {
            if (resetOtpTimerInterval) {
                clearInterval(resetOtpTimerInterval);
                resetOtpTimerInterval = null;
                $('#resetOtpTimer').classList.add('hidden');
            }
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
                    resetOtpTimerInterval = null; // Fix: Allow resending after timer expires
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
        console.log('SkillMind AI: Entering App...');
        showView('mainView');
        const greeting = $('#userGreeting');
        if (greeting && state.user) greeting.textContent = `Hi, ${state.user.username}`;

        sessionStorage.setItem('hasVisited', '1');
        showPage('dashboard');
        loadDashboard();

        // Failsafe: Aggressively hide navbar if in interview
        setInterval(() => {
            if (state.activePage === 'interview') {
                const nav = $('.navbar');
                if (nav && (nav.style.display !== 'none' || !nav.classList.contains('hidden'))) {
                    console.log('Failsafe: Force-hiding navbar');
                    nav.style.display = 'none';
                    nav.classList.add('hidden');
                }
            }
        }, 800);
    }

    function signOut() {
        state.token = null;
        state.user = null;
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('user');
        sessionStorage.removeItem('hasVisited'); // Clear so next login starts fresh

        // Force close settings modal if open
        const modal = $('#unifiedSettingsModal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = ''; 
        }

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
                if (view === 'coding') {
                    $('#codingResult').classList.add('hidden');
                    $('#codingActive').classList.add('hidden');
                    $('#codingStart').classList.remove('hidden');
                }
            });
        });

        $('#generateReportBtn')?.addEventListener('click', unifiedReportHandler);
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
                if (bar) {
                    bar.style.width = `${r.final_score || 0}%`;
                    bar.dataset.pct = `${(r.final_score || 0).toFixed(1)}%`;
                }
                const txt = $('#readinessText');
                if (txt) txt.textContent = `Interview Readiness: ${r.readiness_level || 'Moderate'} (${(r.final_score || 0).toFixed(1)}%)`;

                // Skill gaps
                const gapList = $('#skillGapsList');
                if (gapList && r.analysis && r.analysis.length) {
                    gapList.innerHTML = r.analysis.map(g => `
                        <li>
                            <div class="gap-item">
                                <div class="gap-icon">
                                    <div class="bracket-tl"></div>
                                    <div class="bracket-br"></div>
                                </div>
                                <div class="gap-content">
                                    <span class="gap-category">${g.category}</span>
                                    <span class="gap-status status-${g.status.toLowerCase()}">${g.status}</span>
                                    <p class="gap-suggestion">${g.suggestion}</p>
                                </div>
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

            // Enhanced multi-module history chart
            if (data.quiz_history || data.coding_history || data.interview_history) {
                renderHistoryChart(data);
            }

        } catch (err) {
            console.warn('[Dashboard] Sync error:', err);
        }
    }

    // Single source of truth for generating both data-sync and printable summary
    async function unifiedReportHandler() {
        // Open window immediately to avoid popup blockers (browsers prefer synchronous calls)
        const reportWindow = window.open('', '_blank');
        
        const btn = $('#generateReportBtn');
        if (!btn) return;
        
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Syncing...';

        try {
            if (!reportWindow) {
                throw new Error('Popup blocked! Please allow popups for this site to view your report.');
            }

            // Show a loading message in the new window while we wait for the data
            reportWindow.document.write('<html><body style="font-family:sans-serif; display:flex; align-items:center; justify-content:center; height:100vh; color:#666;"><div><h2>Generating your premium report...</h2><p>Please wait a moment while we synchronize your latest data.</p></div></body></html>');

            // 1. Sync backend scores
            await api('/api/scoring/generate-report', { method: 'POST' });
            
            // 2. Fetch latest stats
            btn.innerHTML = '<span class="spinner"></span> Building Report...';
            const data = await api('/api/dashboard/stats');
            const r = data.report;
            if (!r) throw new Error('No assessment data found. Please complete all sections.');

            // 3. Update Dashboard Dashboard UI
            loadDashboard(); 

            // 4. Open printable report
            const html = `
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Interview Readiness Report - ${state.user.username}</title>
                    <style>
                        body { font-family: 'Plus Jakarta Sans', sans-serif; padding: 40px; color: #333; line-height: 1.6; background: #fff; }
                        .header { text-align: center; margin-bottom: 40px; border-bottom: 2px solid #6366f1; padding-bottom: 20px; }
                        .header h1 { color: #6366f1; margin: 0; font-size: 2.2rem; }
                        .section { margin-bottom: 30px; background: #f8fafc; padding: 25px; border-radius: 16px; border: 1px solid #e2e8f0; }
                        .section h3 { margin-top: 0; color: #1e293b; border-bottom: 1px solid #cbd5e1; padding-bottom: 12px; margin-bottom: 20px; }
                        .marks-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
                        .mark-item { background: white; padding: 18px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
                        .mark-label { font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
                        .mark-val { font-size: 1.8rem; font-weight: 800; color: #6366f1; margin-top: 5px; }
                        .total-score { text-align: center; font-size: 2rem; font-weight: 800; color: #10b981; margin: 25px 0; }
                        .status-badge { padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; }
                        .status-strong { background: #dcfce7; color: #166534; }
                        .status-moderate { background: #fef9c3; color: #854d0e; }
                        .status-weak { background: #fee2e2; color: #991b1b; }
                        @media print { .no-print { display: none; } }
                        .btn-print { background: #6366f1; color: white; padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-weight: 700; width: 100%; max-width: 200px; }
                    </style>
                </head>
                <body>
                    <div class="no-print" style="text-align: right; margin-bottom: 25px;">
                        <button class="btn-print" onclick="window.print()">Print Report PDF</button>
                    </div>
                    <div class="header">
                        <h1>Skill Mind AI</h1>
                        <p>Comprehensive Interview Readiness Report</p>
                        <p style="color: #64748b;">Candidate: <strong>${state.user.username}</strong> | Analysis Date: ${new Date().toLocaleDateString()}</p>
                    </div>

                    <div class="section">
                        <h3>Performance Summary</h3>
                        <div class="total-score">
                            Overall Readiness: ${Math.round(r.final_score)}%<br>
                            <span class="status-badge status-${(r.readiness_level || 'Moderate').toLowerCase().replace(' ', '')}">${r.readiness_level || 'Moderate'}</span>
                        </div>
                        <div class="marks-grid">
                            <div class="mark-item"><div class="mark-label">Resume Strength</div><div class="mark-val">${r.marks?.resume || 0}/10</div></div>
                            <div class="mark-item"><div class="mark-label">Technical Quiz</div><div class="mark-val">${r.marks?.quiz || 0}/30</div></div>
                            <div class="mark-item"><div class="mark-label">Coding Logic</div><div class="mark-val">${r.marks?.coding || 0}/30</div></div>
                            <div class="mark-item"><div class="mark-label">Interview Impact</div><div class="mark-val">${r.marks?.interview || 0}/30</div></div>
                        </div>
                    </div>

                    <div class="section">
                        <h3>Insights & Recommendations</h3>
                        ${(r.analysis || []).map(a => `
                            <div style="margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px dashed #e2e8f0;">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <strong style="color: #1e293b;">${a.category}</strong>
                                    <span class="status-badge status-${a.status.toLowerCase()}">${a.status}</span>
                                </div>
                                <p style="margin: 8px 0 0 0; color: #475569; font-size: 0.95rem;">${a.suggestion}</p>
                            </div>
                        `).join('')}
                    </div>

                    <div class="section">
                        <h3>Career Matching</h3>
                        <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 15px;">Based on your current skill profile, here are top matching opportunities:</p>
                        ${(data.job_recommendations || []).map(j => `
                            <div style="background:#fff; padding:12px; border-radius:8px; margin-bottom:10px; border:1px solid #e2e8f0;">
                                <strong style="color: #6366f1;">${j.role}</strong> — <span style="font-size:0.85rem; color:#64748b;">${j.company}</span>
                            </div>
                        `).join('')}
                    </div>

                    <footer style="text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 20px;">
                        &copy; ${new Date().getFullYear()} Skill Mind AI - Empowering Your Career Journey
                    </footer>
                </body>
                </html>
            `;
            reportWindow.document.open();
            reportWindow.document.write(html);
            reportWindow.document.close();
            showToast('Report synchronized and generated!', 'success');
        } catch (err) {
            console.error('[ReportGen] Error:', err);
            showToast(err.message || 'Error generating report.', 'error');
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

    function renderHistoryChart(data) {
        const ctx = document.getElementById('lineChart');
        if (!ctx) return;
        
        const qH = data.quiz_history || [];
        const cH = data.coding_history || [];
        const iH = data.interview_history || [];
        
        const maxLen = Math.max(qH.length, cH.length, iH.length);
        if (maxLen === 0) return;

        if (lineChart) lineChart.destroy();

        lineChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: maxLen}, (_, i) => `Attempt ${i + 1}`),
                datasets: [
                    {
                        label: 'Quiz',
                        data: qH.map(h => h.score),
                        borderColor: '#6366f1',
                        backgroundColor: 'transparent',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 4
                    },
                    {
                        label: 'Coding',
                        data: cH.map(h => h.score),
                        borderColor: '#ec4899',
                        backgroundColor: 'transparent',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 4
                    },
                    {
                        label: 'Interview',
                        data: iH.map(h => h.score),
                        borderColor: '#10b981',
                        backgroundColor: 'transparent',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8' }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        labels: { color: '#f8fafc', boxWidth: 12, padding: 15, font: { size: 10 } }
                    }
                }
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

        // Restore skills preview
        if (state.activeResumeSkills && state.activeResumeSkills.length) {
            skillsPreview.innerHTML = state.activeResumeSkills.map(s => `<span class="tag">${s}</span>`).join('');
        }

        // Ensure correct initial state for JD and comparisons
        enforceFlow();

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

            // Clear previous comparison results to avoid stale data
            const comparisonResult = $('#comparisonResult');
            if (comparisonResult) comparisonResult.classList.add('hidden');

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

                // Update UI state based on new resume data
                enforceFlow();

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
                    // Store entities for tab switching
                    state.currentEntities = {
                        tech: data.skills_categorized || {},
                        edu: data.education || [],
                        exp: data.experience || [],
                        proj: data.projects || [],
                        cert: data.certifications || []
                    };
                    renderEntities('tech');

                    // Render Radar Chart
                    renderSkillRadar(data.technical_skills || []);

                    // Render Recommendations
                    renderRecommendations(data.recommendations || []);

                    // Render Error Report
                    renderErrorReports(data.error_report || []);

                    // Render Quality Heatmap
                    renderQualityHeatmap(data.quality_report || {}, data.quality_score || 0);
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
                const cats = entities.tech || {};
                const allSkills = [];
                Object.entries(cats).forEach(([catName, skills]) => {
                    if (Array.isArray(skills)) {
                        skills.forEach(s => {
                            allSkills.push({ ...s, category: catName });
                        });
                    }
                });

                html = allSkills.length ? allSkills.map(s => `
                    <div class="entity-item" style="margin-bottom: 1.2rem; border-left: 2px solid var(--primary); padding-left: 1rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                            <strong style="color: #fff; font-size: 1rem;">${s.skill || s}</strong>
                            <span style="font-size: 0.7rem; color: var(--text-muted); text-transform: capitalize;">${s.category.replace('_', ' ')}</span>
                        </div>
                        <div style="height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; margin-top: 8px; overflow: hidden;">
                            <div style="width: ${s.confidence ? s.confidence * 100 : 85}%; height: 100%; background: var(--primary-gradient);"></div>
                        </div>
                    </div>
                `).join('') : '<p style="color: var(--text-dim);">No technical skills extracted.</p>';
            } else if (type === 'edu') {
                const edu = Array.isArray(entities.edu) ? entities.edu : [];
                html = edu.length ? edu.map(e => `
                    <div class="entity-item" style="margin-bottom: 1rem; border-left: 2px solid var(--primary); padding-left: 1rem;">
                        <div style="font-weight: 700; color: #fff;">${e.degree || 'Degree Unknown'}</div>
                        <div style="font-size: 0.9rem; color: var(--text-muted);">${e.institution || 'Institution Unknown'}</div>
                        ${e.year ? `<div style="font-size: 0.8rem; color: var(--primary);">${e.year}</div>` : ''}
                    </div>
                `).join('') : '<p style="color: var(--text-dim);">No educational data found.</p>';
            } else if (type === 'exp') {
                const exp = Array.isArray(entities.exp) ? entities.exp : [];
                html = exp.length ? exp.map(e => `
                    <div class="entity-item" style="margin-bottom: 1rem; border-left: 2px solid var(--accent); padding-left: 1rem;">
                        <div style="font-weight: 700; color: #fff;">${e.title || 'Role Unknown'}</div>
                        <div style="font-size: 0.9rem; color: var(--text-muted);">${e.company || 'Company Unknown'}</div>
                        ${e.duration ? `<div style="font-size: 0.8rem; color: var(--accent);">${e.duration}</div>` : ''}
                    </div>
                `).join('') : '<p style="color: var(--text-dim);">No professional experience data found.</p>';
            } else if (type === 'proj') {
                const proj = Array.isArray(entities.proj) ? entities.proj : [];
                html = proj.length ? proj.map(p => `
                    <div class="entity-item" style="margin-bottom: 1rem; border-left: 2px solid var(--warning); padding-left: 1rem;">
                        <div style="font-weight: 700; color: #fff;">${p.title || 'Project Name Unknown'}</div>
                        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 5px;">${p.role || ''}</p>
                        ${p.technologies ? `<div style="margin-top: 5px;">${p.technologies.slice(0, 5).map(t => `<span class="tag xsmall-tag" style="font-size:10px; padding:2px 6px;">${t}</span>`).join('')}</div>` : ''}
                    </div>
                `).join('') : '<p style="color: var(--text-dim);">No project data found.</p>';
            }
            container.innerHTML = html;
        }

        function renderErrorReports(errors) {
            const container = $('#resumeErrorReport');
            const content = $('#errorReportContent');
            if (!container || !content) return;

            if (!errors || errors.length === 0) {
                container.classList.add('hidden');
                return;
            }

            container.classList.remove('hidden');
            content.innerHTML = errors.map(err => `
                <div class="error-item" style="background: rgba(239, 68, 68, 0.05); border-left: 3px solid #ef4444; padding: 1rem; border-radius: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color: #fff; font-size: 0.95rem;">${err.type}: ${err.finding}</strong>
                        <span style="font-size: 0.75rem; background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 2px 8px; border-radius: 10px;">${err.location}</span>
                    </div>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 5px;">Suggestion: <span style="color: #10b981; font-weight: 600;">${err.suggestion}</span></p>
                </div>
            `).join('');
        }

        function renderQualityHeatmap(metrics, overall) {
            const section = $('#resumeHeatmapSection');
            const container = $('#resumeHeatmap');
            if (!section || !container) return;

            if (!metrics || Object.keys(metrics).length === 0) {
                section.classList.add('hidden');
                return;
            }

            section.classList.remove('hidden');
            container.innerHTML = Object.entries(metrics).map(([key, val]) => {
                const color = val > 80 ? '#10b981' : (val > 60 ? '#f59e0b' : '#ef4444');
                return `
                    <div class="heatmap-cell" style="background: rgba(255,255,255,0.02); border: 1px solid var(--glass-border); padding: 1rem; border-radius: 12px; text-align: center;">
                        <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px;">${key.replace('_', ' ')}</div>
                        <div style="font-size: 1.25rem; font-weight: 800; color: ${color};">${val}%</div>
                        <div style="height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; margin-top: 10px; overflow: hidden;">
                            <div style="width: ${val}%; height: 100%; background: ${color}; opacity: 0.6;"></div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        $('#runCompareBtn')?.addEventListener('click', async () => {
            const jdArea = $('#jdTextArea');
            if (!jdArea) return;

            const jd = jdArea.value.trim();
            if (!jd) return showToast('Please paste a job description', 'warning');
            if (jd.length < 30) return showToast('Please enter a more detailed job description (minimum 30 characters).', 'warning');

            const btn = $('#runCompareBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Analyzing Resume & JD...';

            try {
                const data = await api('/api/resume/compare', {
                    method: 'POST',
                    body: { jd }
                });

                console.log("Comparison Data Received:", data);
                if (!data || !data.comparison || data.comparison.length === 0) {
                    throw new Error("Invalid comparison data received from server.");
                }

                const comp = data.comparison[0];
                console.log("Primary Comparison Object:", comp);

                // Update Method Label
                const methodLabel = $('#compMethodLabel');
                if (methodLabel) methodLabel.textContent = `Method: ${comp.method || 'Keyword Similarity'}`;

                state.activeJD = jd;
                state.activeJDSkills = (comp.matching_skills || []).concat(comp.missing_skills || []);
                sessionStorage.setItem('activeJD', jd);
                sessionStorage.setItem('activeJDSkills', JSON.stringify(state.activeJDSkills));

                // Show report
                $('#comparisonResult').classList.remove('hidden');
                $('#comparisonContent').innerHTML = `
                    <div class="comp-box" style="grid-column: 1 / -1;">
                        <div class="comp-header" style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1.5rem;">
                            <div>
                                <strong style="font-size: 1.2rem; color: var(--primary);">JD Alignment Report</strong>
                                <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">Semantic analysis relative to the provided Job Description.</p>
                            </div>
                            <div style="display:flex; gap:1rem; text-align:right;">
                                <div>
                                    <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">Match Score</div>
                                    <div style="font-size: 1.5rem; font-weight: 800; color: var(--accent);">${Math.round(comp.match_score)}%</div>
                                </div>
                                <div style="border-left: 1px solid var(--glass-border); padding-left: 1rem;">
                                    <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">Profile Strength</div>
                                    <div style="font-size: 1.5rem; font-weight: 800; color: var(--primary);">${Math.round(comp.resume_score || 0)}%</div>
                                </div>
                            </div>
                        </div>
                        <div class="comp-grid">
                            <div class="comp-section">
                                <h4>Matching Skills</h4>
                                <div class="comp-tags">
                                    ${comp.matching_skills.length ? comp.matching_skills.map(s => `
                                        <div class="comp-tag-wrapper" style="margin-bottom:5px;">
                                            <span class="comp-tag comp-match">${typeof s === 'object' ? s.skill : s}</span>
                                            ${s.reason ? `<div style="font-size:10px; color:var(--text-dim); margin-left:5px;">${s.reason}</div>` : ''}
                                        </div>
                                    `).join('') : '<span class="placeholder-text">None</span>'}
                                </div>
                            </div>
                            <div class="comp-section">
                                <h4>Partial Matches</h4>
                                <div class="comp-tags">
                                    ${(comp.partial_skills || []).length ? comp.partial_skills.map(s => `
                                        <div class="comp-tag-wrapper" style="margin-bottom:5px;">
                                            <span class="comp-tag comp-partial" title="${s.gap || ''}">${s.skill || s}</span>
                                            ${s.gap ? `<div style="font-size:10px; color:var(--text-dim); margin-left:5px;">${s.gap}</div>` : ''}
                                        </div>
                                    `).join('') : '<span class="placeholder-text">None</span>'}
                                </div>
                            </div>
                            <div class="comp-section">
                                <h4>Missing Skills</h4>
                                <div class="comp-tags">
                                    ${comp.missing_skills.length ? comp.missing_skills.map(s => `
                                        <div class="comp-tag-wrapper" style="margin-bottom:5px;">
                                            <span class="comp-tag comp-missing">${typeof s === 'object' ? s.skill : s}</span>
                                            ${s.priority ? `<div style="font-size:10px; color:#ef4444; margin-left:5px;">Priority: ${s.priority}</div>` : ''}
                                        </div>
                                    `).join('') : '<span class="placeholder-text">None</span>'}
                                </div>
                            </div>
                        </div>
                        ${comp.insights ? `
                        <div class="comp-section" style="margin-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 1rem;">
                            <h4 style="margin-bottom: 0.5rem; color: var(--accent);">AI Insights & Fitment</h4>
                            <p style="font-size: 0.9rem; color: var(--text-muted); line-height: 1.5;">${comp.insights}</p>
                            ${comp.justification ? `<p style="font-size: 0.8rem; color: var(--text-dim); font-style: italic; margin-top: 5px;">Justification: ${comp.justification}</p>` : ''}
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
                    { id: 'proj', key: 'projects' },
                    { id: 'edu', key: 'education' },
                    { id: 'cert', key: 'certifications' }
                ];

                categories.forEach(cat => {
                    const score = Math.round(bd[cat.key] || 0);
                    animateValue(`${cat.id}MatchScore`, 0, score, 800);
                    const bar = document.getElementById(`${cat.id}MatchBar`);
                    if (bar) bar.style.width = score + '%';
                });

                // Render Visuals
                renderMatchMeter(data.comparison[0].match_score);
                renderSkillRadarDual(data.comparison[0].matching_skills, data.comparison[0].missing_skills, data.comparison[0].partial_skills || []);
                renderSkillMatrix(data.comparison[0].matching_skills, data.comparison[0].missing_skills, data.comparison[0].partial_skills || []);
                renderRecommendations(data.comparison[0].recommendations || []);

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
            const needle = document.getElementById('matchMeterNeedle');
            const valueDisplay = document.getElementById('matchMeterValue');
            if (!needle || !valueDisplay) return;

            // Animate the needle rotation: 0% -> -90deg, 100% -> 90deg
            const rotation = (score / 100 * 180) - 90;
            needle.style.setProperty('--rotation', `${rotation}deg`);

            // Animate the digital counter
            let start = 0;
            const duration = 1500;
            const startTimestamp = performance.now();

            const step = (timestamp) => {
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                const current = Math.floor(progress * score);
                valueDisplay.textContent = `${current}%`;
                if (progress < 1) {
                    window.requestAnimationFrame(step);
                } else {
                    valueDisplay.textContent = `${score}%`;
                }
            };
            window.requestAnimationFrame(step);
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

        function renderSkillRadarDual(matching, missing, partial) {
            const ctx = document.getElementById('skillRadarChartDual');
            if (!ctx) return;

            if (state.charts.radar) state.charts.radar.destroy();

            const labels = [...matching.map(s => s.skill || s), ...partial.map(s => s.skill || s), ...missing.map(s => s.skill || s)].slice(0, 10);

            // Resume values: Matches are 95%, Partial are 60%, missing are 15%
            const resumeData = labels.map(l => {
                if (matching.some(s => (s.skill || s) === l)) return 95;
                if (partial.some(s => (s.skill || s) === l)) return 60;
                return 15;
            });
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

        function renderXAI(explanation) {
            const container = $('#comparisonContent'); // Or a specific XAI element
            if (!container || !explanation || explanation.length === 0) return;

            const xaiHtml = `
                <div class="xai-explanation" style="grid-column: 1 / -1; background: rgba(16, 185, 129, 0.05); padding: 1.5rem; border-radius: 12px; border-left: 4px solid var(--accent); margin-top: 1rem;">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom: 10px;">
                        <i class="fas fa-brain" style="color: var(--accent);"></i>
                        <h4 style="margin:0; color: #fff;">AI Match Reasoning (XAI)</h4>
                    </div>
                    <ul style="padding-left: 1.2rem; display: flex; flex-direction: column; gap: 8px;">
                        ${explanation.map(exp => `
                            <li style="font-size: 0.9rem; color: var(--text-muted); line-height: 1.4;">
                                <strong style="color: var(--accent);">${exp.category || 'Logic'}:</strong> ${exp.reason || exp}
                                ${exp.impact ? ` <span style="font-size: 0.75rem; color: var(--text-dim);">[Impact: ${exp.impact}]</span>` : ''}
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', xaiHtml);
        }

        function renderSkillMatrix(matching, missing, partial) {
            const tbody = document.getElementById('skillMatrixBody');
            if (!tbody) return;

            const rows = [];

            matching.forEach(s => {
                rows.push(`
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 1rem; color: #fff; font-weight: 600;">${s.skill || s}</td>
                        <td style="padding: 1rem; text-align: center;"><i class="fas fa-check-circle" style="color: #4ade80;"></i></td>
                        <td style="padding: 1rem; text-align: center; color: var(--text-muted);">${(s.weight || 1.0).toFixed(1)}</td>
                        <td style="padding: 1rem; text-align: center;"><span style="color: #4ade80;">Matched</span></td>
                    </tr>
                `);
            });

            partial.forEach(s => {
                rows.push(`
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 1rem; color: #fff;">${s.skill || s}</td>
                        <td style="padding: 1rem; text-align: center;"><i class="fas fa-adjust" style="color: #fbbf24;"></i></td>
                        <td style="padding: 1rem; text-align: center; color: var(--text-muted);">${(s.weight || 0.7).toFixed(1)}</td>
                        <td style="padding: 1rem; text-align: center;"><span style="background: rgba(251, 191, 36, 0.15); color: #fbbf24; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 700;">Partial</span></td>
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

            tbody.innerHTML = rows.slice(0, 15).join('');
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
            state.quizResponses.push({
                question: state.quizQuestions[state.quizIndex]?.question || '',
                answer: '',
                correct_answer: state.quizQuestions[state.quizIndex]?.answer || ''
            });
            state.quizIndex++;
            renderQuestion();
        });
        $('#retakeQuizBtn')?.addEventListener('click', () => {
            $('#quizResult').classList.add('hidden');
            $('#quizStart').classList.remove('hidden');
        });

        // delegation for MCQ options
        $('#quizOptions')?.addEventListener('click', (e) => {
            const opt = e.target.closest('.quiz-option');
            if (!opt) return;

            $$('.quiz-option').forEach(el => el.classList.remove('selected'));
            opt.classList.add('selected');
            state.selectedOption = opt.dataset.value;

            // Enable submit button when an option is selected
            const nextBtn = $('#nextQuestionBtn');
            if (nextBtn) {
                nextBtn.disabled = false;
                nextBtn.style.opacity = "1";
                nextBtn.style.pointerEvents = "auto";
            }
        });

        // Add handler for text input validation
        $('#answerInput')?.addEventListener('input', (e) => {
            const nextBtn = $('#nextQuestionBtn');
            if (nextBtn) {
                const hasValue = e.target.value.trim().length > 0;
                nextBtn.disabled = !hasValue;
                nextBtn.style.opacity = hasValue ? "1" : "0.5";
                nextBtn.style.pointerEvents = hasValue ? "auto" : "none";
            }
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

        // Disable submit button by default for new question
        const nextBtn = $('#nextQuestionBtn');
        if (nextBtn) {
            nextBtn.disabled = true;
            nextBtn.style.opacity = "0.5";
            nextBtn.style.pointerEvents = "none";
        }

        const q = state.quizQuestions[state.quizIndex];
        $('#questionCounter').textContent = `Question ${state.quizIndex + 1} / ${state.quizQuestions.length}`;
        $('#questionSkill').textContent = q.skill;
        $('#questionText').textContent = q.question;

        // Handle MCQs
        const optionsContainer = $('#quizOptions');
        const textInput = $('#answerInput');
        state.selectedOption = null;

        if (q.options && q.options.length) {
            optionsContainer.classList.remove('hidden');
            textInput.classList.add('hidden');
            optionsContainer.innerHTML = q.options.map(opt => `
                <button class="quiz-option" data-value="${opt}">${opt}</button>
            `).join('');
        } else {
            optionsContainer.classList.add('hidden');
            textInput.classList.remove('hidden');
            textInput.value = '';
            textInput.focus();
        }

        const pct = ((state.quizIndex) / state.quizQuestions.length) * 100;
        $('#quizProgressBar').style.width = `${pct}%`;

        startQuizTimer();
    }

    let quizTimerInterval = null;
    function startQuizTimer() {
        clearInterval(quizTimerInterval);
        let timeLeft = 30;
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
                showToast('Time up! Moving to next question.', 'warning');
                nextQuestion(true); // Proceed even without selection
            }
        }, 1000);
    }

    function nextQuestion(force = false) {
        clearInterval(quizTimerInterval);
        const q = state.quizQuestions[state.quizIndex];
        if (!q) {
            console.warn("No more questions at index:", state.quizIndex);
            submitQuiz();
            return;
        }
        
        const textAnswer = $('#answerInput').value.trim();
        const finalAnswer = q.options ? state.selectedOption : textAnswer;

        if (!force && q.options && !state.selectedOption) {
            return showToast('Please select an option', 'warning');
        }

        state.quizResponses.push({
            question: q.question || '',
            answer: finalAnswer || '',
            correct_answer: q.answer || ''
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
            startRedirectTimer('gotoCodingBtn', 'coding', 'Go to Coding Assessment', 10);
        } catch {
            alert('Failed to submit quiz.');
            $('#quizStart').classList.remove('hidden');
        }
    }

    /* ===== Coding ===== */
    function initCoding() {
        $('#startCodingBtn')?.addEventListener('click', () => {
            loadMonacoEditor(() => {
                startCodingAssessment();
            });
        });
        $('#resetCodeBtn')?.addEventListener('click', () => {
            const p = state.codingChallenges[state.codingIndex];
            if (p && monacoEditor) {
                monacoEditor.setValue(p.starter_code);
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

    function getStarterCode(problem, language) {
        // 1. If the problem already has a specific starter code for THIS language (or it's the AI's choice), use it
        if (problem.starter_code && (problem.language === language || !problem.language)) {
            return problem.starter_code;
        }

        const titleSnake = problem.title.toLowerCase().replace(/\s+/g, '_');
        
        switch(language) {
            case 'javascript':
                return `function ${titleSnake}(...args) {\n    // Write your solution here\n    return null;\n}\n`;
            case 'java':
                return `public class Solution {\n    public Object ${titleSnake}(Object... args) {\n        // Write your solution here\n        return null;\n    }\n}\n`;
            case 'cpp':
                return `#include <iostream>\n#include <vector>\n#include <string>\n\nclass Solution {\npublic:\n    // Adjust return type and parameters as needed\n    void ${titleSnake}() {\n        // Write your solution here\n    }\n};\n`;
            case 'c':
                return `#include <stdio.h>\n#include <stdlib.h>\n\n// Adjust return type and parameters as needed\nvoid ${titleSnake}() {\n    // Write your solution here\n}\n`;
            case 'sql':
                return `-- Write your SQL query here\n-- Problem: ${problem.title}\n\nSELECT * FROM ... WHERE ...;\n`;
            case 'go':
                return `package main\n\nfunc ${titleSnake}() {\n    // Write your solution here\n}\n`;
            case 'python':
            default:
                return `def ${titleSnake}(*args):\n    # Write your solution here\n    pass\n`;
        }
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
            state.detectedLanguages = data.languages || ['python'];
            state.currentLanguage = 'python';

            // Populate language selector
            const langSelector = $('#codingLanguageSelector');
            if (langSelector) {
                const langMap = {
                    'python': 'Python 3',
                    'javascript': 'JavaScript',
                    'java': 'Java',
                    'cpp': 'C++',
                    'c': 'C (GCC)',
                    'sql': 'SQL Query',
                    'go': 'Go'
                };
                langSelector.innerHTML = state.detectedLanguages.map(l => 
                    `<option value="${l}">${langMap[l] || l}</option>`
                ).join('');
                langSelector.value = state.currentLanguage || 'python';
            }

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
    
    function startCodingTimer() {
        stopCodingTimer();
        state.codingTimeLeft = 600; 
        updateCodingTimerUI();
        
        state.codingTimerInterval = window.setInterval(() => {
            try {
                state.codingTimeLeft--;
                updateCodingTimerUI();
                
                if (state.codingTimeLeft <= 0) {
                    stopCodingTimer();
                    showToast('Time is up! Submitting your solution...', 'warning');
                    submitCodeForReview(true);
                } else if (state.codingTimeLeft === 60) {
                    showToast('1 minute remaining!', 'warning');
                    const container = $('#codingTimerContainer');
                    const timerText = $('#codingTimer');
                    if (container) container.style.borderColor = 'var(--danger)';
                    if (timerText) timerText.style.color = 'var(--danger)';
                }
            } catch (err) {
                console.error('Error in coding timer interval:', err);
            }
        }, 1000);
    }

    function stopCodingTimer() {
        if (state.codingTimerInterval) {
            window.clearInterval(state.codingTimerInterval);
            state.codingTimerInterval = null;
        }
        // Reset styles
        const container = $('#codingTimerContainer');
        const timerText = $('#codingTimer');
        if (container) container.style.borderColor = 'var(--glass-border)';
        if (timerText) timerText.style.color = '#fff';
    }

    function updateCodingTimerUI() {
        const minutes = Math.floor(state.codingTimeLeft / 60);
        const seconds = state.codingTimeLeft % 60;
        const display = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        const timerEl = $('#codingTimer');
        if (timerEl) timerEl.textContent = display;
    }

    function renderProblem() {
        const p = state.codingChallenges[state.codingIndex];
        if (!p) return;

        // Update progress UI
        const currentNum = state.codingIndex + 1;
        const totalNum = state.codingChallenges.length;
        $('#codingProgress').textContent = `Question ${currentNum} / ${totalNum}`;
        $('#codingMarksTracker').textContent = `Marks: ${state.codingTotalMarks}/30`;
        $('#codingQuestionLabel').textContent = `Q${currentNum}`;

        // Update problem header
        $('#currentProblemTitle').textContent = p.title;
        const diff = $('#currentProblemDifficulty');
        diff.textContent = p.difficulty || 'intermediate';
        diff.className = `badge badge-${p.difficulty || 'intermediate'}`;

        // Update content
        $('#codingProblem').innerHTML = `<p>${p.description}</p>`;

        // Populate Detail Boxes
        const inputFormat = $('#inputFormatDisplay');
        const outputFormat = $('#outputFormatDisplay');
        const constraintsList = $('#codingConstraints');

        if (inputFormat) inputFormat.textContent = p.input_format || "Input as arguments to the function";
        if (outputFormat) outputFormat.textContent = p.output_format || "Return the computed result";

        if (constraintsList) {
            if (p.constraints && p.constraints.length) {
                constraintsList.innerHTML = p.constraints.map(c => `<li>${c}</li>`).join('');
            } else {
                constraintsList.innerHTML = `<li>Standard memory and time limits apply</li><li>Optimize for performance</li>`;
            }
        }

        // Update Examples List
        const examplesList = $('#codingExamplesList');
        if (examplesList) {
            if (p.examples && p.examples.length) {
                examplesList.innerHTML = p.examples.map((ex, idx) => `
                    <div class="problem-example" style="background: rgba(255,255,255,0.03); padding: 0.8rem; border-radius: 8px; border-left: 3px solid var(--accent); margin-bottom: 0.8rem;">
                        <div style="font-size: 0.75rem; color: var(--accent); font-weight: 700; margin-bottom: 4px;">EXAMPLE ${idx + 1}</div>
                        <div style="font-size: 0.85rem; color: #fff;"><strong>Input:</strong> <code>${ex.input}</code></div>
                        <div style="font-size: 0.85rem; color: #fff;"><strong>Output:</strong> <code>${ex.output}</code></div>
                    </div>
                `).join('');
            } else {
                examplesList.innerHTML = '<p style="font-size: 0.85rem; color: var(--text-dim);">No examples provided.</p>';
            }
        }

        // Update Hints
        const hintsWrap = $('#codingHintsWrap');
        const hintsList = $('#codingHints');
        if (p.hints && p.hints.length) {
            hintsWrap?.classList.remove('hidden');
            if (hintsList) hintsList.innerHTML = p.hints.map(h => `<li>${h}</li>`).join('');
        } else {
            hintsWrap?.classList.add('hidden');
        }

        // Auto-select language for every question as per user request
        if (p.language) {
            state.currentLanguage = p.language;
            const langSelector = $('#codingLanguageSelector');
            if (langSelector) langSelector.value = p.language;
            console.log(`Auto-switched language to: ${p.language}`);
        }

        // Set Code in Editor
        if (monacoEditor) {
            monacoEditor.setValue(p.starter_code || getStarterCode(p, state.currentLanguage || 'python'));
            const langMapping = { 'python': 'python', 'javascript': 'javascript', 'java': 'java', 'cpp': 'cpp', 'c': 'c', 'sql': 'sql' };
            monaco.editor.setModelLanguage(monacoEditor.getModel(), langMapping[state.currentLanguage] || 'python');
        }
        $('#codeOutputText').textContent = "";

        // Start 10-minute timer for this question
        startCodingTimer();
    }

    async function submitCodeForReview(isNext) {
        const code = monacoEditor ? monacoEditor.getValue() : "";
        const outputEl = $('#codeOutputText');
        const outputWrap = $('#codeOutput');
        const p = state.codingChallenges[state.codingIndex];

        outputWrap.classList.remove('hidden');
        outputEl.innerHTML = '<span class="spinner"></span> Evaluating...';

        try {
            const data = await api('/api/coding/submit', {
                method: 'POST',
                body: { code, problem_id: p.id, language: state.currentLanguage || 'python' }
            });

            const marks = data.marks || 0;
            const testResults = data.test_results || [];

            // Build simplified Console Output
            let errorLines = [];
            if (!data.is_valid) {
                errorLines.push(data.syntax_message);
            } else {
                testResults.forEach(t => {
                    if (!t.passed) {
                        errorLines.push(t.error || "logical error");
                    }
                });
            }

            let html = `
                <div class="simple-console" style="color: #fff; font-family: 'Fira Code', monospace; font-size: 0.9rem; padding: 1.2rem;">
                    <div style="margin-bottom: 1.2rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.6rem;">
                        <div style="color: #64748b; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 0.4rem; font-weight: 800;">[OUTPUT]</div>
                        <pre style="margin: 0; color: #10b981; white-space: pre-wrap; font-size: 0.9rem; line-height: 1.5;">${
                            testResults.length > 0 ? 
                            (testResults[0].actual.includes('Runtime Error') ? `<span style="color: #ef4444;">${testResults[0].actual}</span>` : testResults[0].actual) : 
                            (data.syntax_message ? `<span style="color: #ef4444;">${data.syntax_message}</span>` : 'No output')
                        }</pre>
                    </div>
                    
                    <div style="display: flex; gap: 2rem; margin-bottom: 1.2rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.6rem;">
                        <div>
                            <div style="color: #64748b; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 0.4rem; font-weight: 800;">[MARK]</div>
                            <div style="font-size: 1.3rem; font-weight: 800; color: var(--primary);">${marks}/5</div>
                        </div>
                        <div>
                            <div style="color: #64748b; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 0.4rem; font-weight: 800;">[STATUS]</div>
                            <div style="font-size: 0.9rem; font-weight: 700; color: ${testResults.every(t => t.passed) ? '#10b981' : '#f59e0b'}">
                                ${testResults.every(t => t.passed) ? 'PASSED' : (data.is_valid ? 'FAILED' : 'ERROR')}
                            </div>
                        </div>
                    </div>

                    <div>
                        <div style="color: #64748b; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 0.4rem; font-weight: 800;">[ERRORS]</div>
                        <div style="margin-top: 0.5rem;">
                            ${errorLines.length > 0 ? 
                                errorLines.map(err => `<div style="color: #ef4444; margin-bottom: 0.4rem; display: flex; align-items: flex-start; gap: 0.6rem; font-size: 0.85rem;"><i class="fas fa-exclamation-triangle" style="margin-top: 3px;"></i><span style="line-height: 1.4;">${err}</span></div>`).join('') : 
                                '<div style="color: #10b981; display: flex; align-items: center; gap: 0.6rem; font-size: 0.85rem;"><i class="fas fa-check-circle"></i><span>All tests passed!</span></div>'
                            }
                        </div>
                    </div>
                </div>
            `;
            outputEl.innerHTML = html;
            outputWrap.scrollTop = 0;

            if (isNext) {
                state.codingSubmissions[state.codingIndex] = { problem_id: p.id, code, marks, language: state.currentLanguage };

                if (state.codingIndex < state.codingChallenges.length - 1) {
                    state.codingIndex++;
                    stopCodingTimer();
                    setTimeout(() => {
                        renderProblem();
                        showToast(`Problem ${state.codingIndex} submitted.`, 'success');
                    }, 1000);
                } else {
                    stopCodingTimer();
                    finishCodingAssessment();
                }
            } else {
                showToast(testResults.every(t => t.passed) ? "All test cases passed!" : "Evaluation complete.", 
                          testResults.every(t => t.passed) ? "success" : "info");
            }
        } catch (err) {
            outputEl.innerHTML = `<div style="color:#ef4444; padding:1rem;">Error: ${err.message || 'Submission failed'}</div>`;
            showToast("Evaluation failed", "error");
        }
    }

    async function finishCodingAssessment() {
        $('#codingActive').classList.add('hidden');
        const progressBar = $('#codingProgressBar');
        if (progressBar) progressBar.style.width = '100%';

        try {
            const data = await api('/api/coding/submit-all', {
                method: 'POST',
                body: { submissions: state.codingSubmissions.map(s => ({...s, language: state.currentLanguage})) }
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
            startRedirectTimer('gotoInterviewBtn', 'interview', 'Go to Personal Interview', 10);

            loadDashboard();
        } catch (err) {
            alert('Failed to conclude assessment.');
            $('#codingStart').classList.remove('hidden');
        }
    }

    /* ===== Scoring / Report ===== */
    function initScoring() {
        $('#generateReportBtn')?.addEventListener('click', unifiedReportHandler);
    }

    /* ===== Profile & Settings ===== */
    let profileData = null;

    function initProfile() {
        const unifiedModal = $('#unifiedSettingsModal');
        if (!unifiedModal) return;

        // Phone specific logic
        const updatePhoneRules = () => {
            const select = $('#profileCountryCode');
            const phoneInput = $('#profilePhone');
            if (select && phoneInput) {
                const opt = select.options[select.selectedIndex];
                const rawMaxLen = parseInt(opt.dataset.len) || 10;
                const format = opt.dataset.format || '10 digits';
                
                // Adjust maxlength to account for spaces (approx 1 space per 3-4 digits)
                const spaceCount = Math.floor(rawMaxLen / 3);
                phoneInput.maxLength = rawMaxLen + spaceCount;
                phoneInput.placeholder = `Enter ${format}`;
                
                // Initial format if loading data
                formatAndSetPhone(phoneInput);
            }
        };

        const formatAndSetPhone = (input) => {
            let val = input.value.replace(/\s/g, '').replace(/[^0-9]/g, '');
            let formatted = '';
            
            // Basic grouping logic (3-3-4 or 4-4 depending on length)
            if (val.length > 0) {
                if (val.length <= 8) {
                    // 4-4 pattern for shorter numbers
                    const parts = val.match(/.{1,4}/g);
                    formatted = parts.join(' ');
                } else {
                    // 3-3-4 pattern for longer numbers (like India/US)
                    const p1 = val.substring(0, 3);
                    const p2 = val.substring(3, 6);
                    const p3 = val.substring(6, 10);
                    if (p3) formatted = `${p1} ${p2} ${p3}`;
                    else if (p2) formatted = `${p1} ${p2}`;
                    else formatted = p1;
                }
            }
            input.value = formatted;
        };

        // Initialize single input listener
        const phoneInput = $('#profilePhone');
        if (phoneInput) {
            phoneInput.addEventListener('input', function(e) {
                // Save cursor position
                let cursor = this.selectionStart;
                const oldLen = this.value.length;
                
                formatAndSetPhone(this);
                
                // Adjust cursor position if a space was added
                const newLen = this.value.length;
                if (newLen > oldLen) cursor++;
                this.setSelectionRange(cursor, cursor);
            });
        }

        $('#profileCountryCode')?.addEventListener('change', updatePhoneRules);
        
        async function loadProfile() {
            try {
                const data = await api('/api/profile/');
                profileData = data;
                
                if (data.user) {
                    if ($('#profileFullName')) $('#profileFullName').value = data.user.full_name || '';
                    if ($('#profileEmail')) $('#profileEmail').value = data.user.email || '';
                    if ($('#profilePhone')) $('#profilePhone').value = data.user.phone || '';
                    if ($('#profileBio')) $('#profileBio').value = data.user.bio || '';
                    if ($('#profileDisplayName')) $('#profileDisplayName').textContent = data.user.full_name || data.user.username;
                    if ($('#profileDisplayUsername')) $('#profileDisplayUsername').textContent = `@${data.user.username}`;
                    
                    if (data.user.profile_photo) {
                        if ($('#profileAvatarPreview')) $('#profileAvatarPreview').src = data.user.profile_photo;
                        if ($('#navAvatarImg')) $('#navAvatarImg').src = data.user.profile_photo;
                    }
                    
                    const greeting = $('#userGreeting');
                    if (greeting) greeting.textContent = data.user.full_name || data.user.username;
                }

                updatePhoneRules();
                // Default render to resume history
                const activeTab = $('.btn-tab.active');
                if (activeTab) renderHistory(activeTab.dataset.historyTab || 'resume');
                else renderHistory('resume');

            } catch (err) {
                console.error('Error loading profile:', err);
            }
        }

        async function saveProfile() {
            const btn = $('#saveProfileBtn');
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Saving...';

            try {
                const payload = {
                    full_name: $('#profileFullName')?.value || '',
                    phone: $('#profilePhone')?.value || '',
                    bio: $('#profileBio')?.value || ''
                };
                await api('/api/profile/', {
                    method: 'PUT',
                    body: payload
                });
                
                if ($('#profileDisplayName')) $('#profileDisplayName').textContent = payload.full_name || payload.username;
                if ($('#navAvatarImg')) $('#navAvatarImg').nextElementSibling.textContent = 'Profile';

                // Success Popup Logic
                const popup = $('#successPopupOverlay');
                if (popup) {
                    popup.classList.add('show');
                    
                    // Close settings modal QUICKLY (0.3s)
                    setTimeout(() => {
                        closeSettingsModal();
                    }, 300);

                    // Hide success popup message LATER (2.0s)
                    setTimeout(() => {
                        popup.classList.remove('show');
                    }, 2000);
                }

            } catch (err) {
                showToast('Failed to update profile', 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        }

        const closeSettingsModal = () => {
            const unifiedModal = $('#unifiedSettingsModal');
            if (unifiedModal) {
                unifiedModal.classList.add('hidden');
                document.body.style.overflow = '';
            }
        };

        // Event Listeners for Profile & Settings
        $('#profileFormInner')?.addEventListener('submit', (e) => {
            e.preventDefault();
            saveProfile();
        });

        $('#avatarUploadInput')?.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = async (event) => {
                const base64 = event.target.result;
                try {
                    await api('/api/profile/', {
                        method: 'PUT',
                        body: { profile_photo: base64 }
                    });
                    if ($('#profileAvatarPreview')) $('#profileAvatarPreview').src = base64;
                    if ($('#navAvatarImg')) $('#navAvatarImg').src = base64;
                    showToast('Photo updated!', 'success');
                } catch (err) {
                    showToast('Failed to upload photo', 'error');
                }
            };
            reader.readAsDataURL(file);
        });

        // Trigger avatar upload via click
        $('#profileAvatarPreview')?.parentElement.addEventListener('click', () => {
            $('#avatarUploadInput')?.click();
        });

        // Open Modal from Nav
        $('#navProfileLink')?.addEventListener('click', (e) => {
            e.preventDefault();
            unifiedModal.classList.remove('hidden');
            loadProfile();
            document.body.style.overflow = 'hidden';
        });

        // Close Modal
        $('#closeUnifiedSettings')?.addEventListener('click', closeSettingsModal);

        // Sidebar Navigation Handling
        const settingsButtons = $$('.sidebar-item[data-settings-tab]');
        console.log(`initProfile: Found ${settingsButtons.length} settings sidebar buttons`);
        
        settingsButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.settingsTab;
                console.log(`Settings Tab Clicked: ${tab}`);
                
                settingsButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                $$('.settings-section').forEach(s => s.classList.add('hidden'));
                const target = $(`#${tab}Section`);
                if (target) {
                    target.classList.remove('hidden');
                    console.log(`Showing section: #${tab}Section`);
                } else {
                    console.error(`Missing section: #${tab}Section`);
                }
            });
        });

        // Initialize Support Chat
        initSupportChat();

        // History Setup
        $$('.history-tabs-container .btn-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                $$('.history-tabs-container .btn-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                renderHistory(tab.dataset.historyTab);
            });
        });

        $('#historySort')?.addEventListener('change', () => {
            const active = $('.history-tabs-container .btn-tab.active');
            if (active) renderHistory(active.dataset.historyTab);
        });

        // Interactive Sign Out Button Animation
        const signOutButtonStates = {
            'default': {
              '--figure-duration': '100ms',
              '--transform-figure': 'none',
              '--walking-duration': '100ms',
              '--transform-arm1': 'none',
              '--transform-wrist1': 'none',
              '--transform-arm2': 'none',
              '--transform-wrist2': 'none',
              '--transform-leg1': 'none',
              '--transform-calf1': 'none',
              '--transform-leg2': 'none',
              '--transform-calf2': 'none'
            },
            'hover': {
              '--figure-duration': '100ms',
              '--transform-figure': 'translateX(1.5px)',
              '--walking-duration': '100ms',
              '--transform-arm1': 'rotate(-5deg)',
              '--transform-wrist1': 'rotate(-15deg)',
              '--transform-arm2': 'rotate(5deg)',
              '--transform-wrist2': 'rotate(6deg)',
              '--transform-leg1': 'rotate(-10deg)',
              '--transform-calf1': 'rotate(5deg)',
              '--transform-leg2': 'rotate(20deg)',
              '--transform-calf2': 'rotate(-20deg)'
            },
            'walking1': {
              '--figure-duration': '300ms',
              '--transform-figure': 'translateX(11px)',
              '--walking-duration': '300ms',
              '--transform-arm1': 'translateX(-4px) translateY(-2px) rotate(120deg)',
              '--transform-wrist1': 'rotate(-5deg)',
              '--transform-arm2': 'translateX(4px) rotate(-110deg)',
              '--transform-wrist2': 'rotate(-5deg)',
              '--transform-leg1': 'translateX(-3px) rotate(80deg)',
              '--transform-calf1': 'rotate(-30deg)',
              '--transform-leg2': 'translateX(4px) rotate(-60deg)',
              '--transform-calf2': 'rotate(20deg)'
            },
            'walking2': {
              '--figure-duration': '400ms',
              '--transform-figure': 'translateX(17px)',
              '--walking-duration': '300ms',
              '--transform-arm1': 'rotate(60deg)',
              '--transform-wrist1': 'rotate(-15deg)',
              '--transform-arm2': 'rotate(-45deg)',
              '--transform-wrist2': 'rotate(6deg)',
              '--transform-leg1': 'rotate(-5deg)',
              '--transform-calf1': 'rotate(10deg)',
              '--transform-leg2': 'rotate(10deg)',
              '--transform-calf2': 'rotate(-20deg)'
            },
            'falling1': {
              '--figure-duration': '1600ms',
              '--walking-duration': '400ms',
              '--transform-arm1': 'rotate(-60deg)',
              '--transform-wrist1': 'none',
              '--transform-arm2': 'rotate(30deg)',
              '--transform-wrist2': 'rotate(120deg)',
              '--transform-leg1': 'rotate(-30deg)',
              '--transform-calf1': 'rotate(-20deg)',
              '--transform-leg2': 'rotate(20deg)'
            },
            'falling2': {
              '--walking-duration': '300ms',
              '--transform-arm1': 'rotate(-100deg)',
              '--transform-arm2': 'rotate(-60deg)',
              '--transform-wrist2': 'rotate(60deg)',
              '--transform-leg1': 'rotate(80deg)',
              '--transform-calf1': 'rotate(20deg)',
              '--transform-leg2': 'rotate(-60deg)'
            },
            'falling3': {
              '--walking-duration': '500ms',
              '--transform-arm1': 'rotate(-30deg)',
              '--transform-wrist1': 'rotate(40deg)',
              '--transform-arm2': 'rotate(50deg)',
              '--transform-wrist2': 'none',
              '--transform-leg1': 'rotate(-30deg)',
              '--transform-leg2': 'rotate(20deg)',
              '--transform-calf2': 'none'
            }
        };

        const updateButtonState = (button, s) => {
            if (signOutButtonStates[s]) {
                button.state = s;
                for (let key in signOutButtonStates[s]) {
                    button.style.setProperty(key, signOutButtonStates[s][key]);
                }
            }
        };

        const btnSignOut = $('#sidebarSignOut');
        if (btnSignOut) {
            btnSignOut.state = 'default';
            
            btnSignOut.addEventListener('mouseenter', () => {
                if (btnSignOut.state === 'default') updateButtonState(btnSignOut, 'hover');
            });
            btnSignOut.addEventListener('mouseleave', () => {
                if (btnSignOut.state === 'hover') updateButtonState(btnSignOut, 'default');
            });
            
            btnSignOut.addEventListener('click', () => {
                if (btnSignOut.state === 'default' || btnSignOut.state === 'hover') {
                    btnSignOut.classList.add('clicked');
                    updateButtonState(btnSignOut, 'walking1');
                    
                    setTimeout(() => {
                        btnSignOut.classList.add('door-slammed');
                        updateButtonState(btnSignOut, 'walking2');
                        
                        setTimeout(() => {
                            btnSignOut.classList.add('falling');
                            updateButtonState(btnSignOut, 'falling1');
                            
                            setTimeout(() => {
                                updateButtonState(btnSignOut, 'falling2');
                                
                                setTimeout(() => {
                                    updateButtonState(btnSignOut, 'falling3');
                                    
                                    setTimeout(() => {
                                        // Execute actual sign out functionality AFTER animation completes
                                        signOut();
                                    }, 1000);
                                    
                                }, parseInt(signOutButtonStates['falling2']['--walking-duration']));
                            }, parseInt(signOutButtonStates['falling1']['--walking-duration']));
                        }, parseInt(signOutButtonStates['walking2']['--figure-duration']));
                    }, parseInt(signOutButtonStates['walking1']['--figure-duration']));
                }
            });
        }
    }

    function renderHistory(type) {
        if (!profileData || !profileData.history) return;
        const list = $('#historyList');
        if (!list) return;
        list.innerHTML = '';
        
        const sortVal = $('#historySort')?.value || 'date-desc';
        
        const history = [...(profileData.history[type] || [])].sort((a, b) => {
            if (sortVal === 'date-desc') return new Date(b.date) - new Date(a.date);
            if (sortVal === 'date-asc') return new Date(a.date) - new Date(b.date);
            if (sortVal === 'score-desc') return b.score - a.score;
            if (sortVal === 'score-asc') return a.score - b.score;
            return 0;
        });

        if (history.length === 0) {
            list.innerHTML = `<p class="placeholder-text">No ${type} history found.</p>`;
            return;
        }

        history.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item';
            div.style = 'display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-radius: 12px; background: rgba(255,255,255,0.03); margin-bottom: 0.8rem; border: 1px solid rgba(255,255,255,0.05);';
            const date = new Date(item.date).toLocaleDateString();
            
            if (type === 'quizzes') {
                div.innerHTML = `
                    <div class="history-item-left">
                        <span class="history-item-title">${item.skill} Quiz</span>
                        <span class="history-item-sub">Completed on ${date}</span>
                    </div>
                    <div class="history-item-right">
                        <span class="history-score">${Math.round(item.score)}/30</span>
                        <div class="history-date">Points</div>
                    </div>
                `;
            } else if (type === 'coding') {
                div.innerHTML = `
                    <div class="history-item-left">
                        <span class="history-item-title">Coding Challenge</span>
                        <span class="history-item-sub">${item.problem}</span>
                    </div>
                    <div class="history-item-right">
                        <span class="history-score">${Math.round(item.score)}/30</span>
                        <div class="history-date">${date}</div>
                    </div>
                `;
            } else if (type === 'resume') {
                div.innerHTML = `
                    <div class="history-item-left">
                        <span class="history-item-title">Resume Analysis</span>
                        <span class="history-item-sub">${item.filename || 'Uploaded Resume'}</span>
                    </div>
                    <div class="history-item-right">
                        <span class="history-score">${Math.round(item.score)}/100</span>
                        <div class="history-date">${date}</div>
                    </div>
                `;
            } else if (type === 'interview') {
                div.innerHTML = `
                    <div class="history-item-left">
                        <span class="history-item-title">AI Interview</span>
                        <span class="history-item-sub">Completed Evaluation</span>
                    </div>
                    <div class="history-item-right">
                        <span class="history-score">${Math.round(item.score)}/30</span>
                        <div class="history-date">${date}</div>
                    </div>
                `;
            }
            list.appendChild(div);
        });
    }

    function initSupportChat() {
        const chatInput = $('#supportChatInput');
        const sendBtn = $('#sendSupportChat');
        const messagesContainer = $('#supportChatMessages');
        let supportChatHistory = []; // Track conversation history for ARIA assistant

        if (!chatInput || !sendBtn || !messagesContainer) return;

        const sendMessage = async () => {
            const text = chatInput.value.trim();
            if (!text) return;

            // Add User Message
            appendChatMessage('user', text);
            chatInput.value = '';
            chatInput.focus();

            // Show Typing Indicator
            const typingId = showTypingIndicator();
            
            try {
                // Use the standard api() helper
                const data = await api('/api/support/chat', {
                    method: 'POST',
                    body: { 
                        message: text,
                        history: supportChatHistory // Send history for conversational context
                    }
                });

                removeTypingIndicator(typingId);
                
                if (data && data.response) {
                    appendChatMessage('ai', data.response);
                    // Update history (keep last 10 messages to avoid large payloads)
                    supportChatHistory.push({ role: 'user', content: text });
                    supportChatHistory.push({ role: 'assistant', content: data.response });
                    if (supportChatHistory.length > 10) supportChatHistory = supportChatHistory.slice(-10);
                } else {
                    appendChatMessage('ai', "I'm sorry, I'm having trouble processing that right now. Please try again.");
                }
            } catch (err) {
                console.error('Chat error:', err);
                removeTypingIndicator(typingId);
                appendChatMessage('ai', "Sorry, I can't connect to the support service right now. Please check your connection.");
            }
        };

        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        function appendChatMessage(sender, text) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${sender}-message`;
            msgDiv.innerHTML = `<div class="message-bubble">${text}</div>`;
            messagesContainer.appendChild(msgDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function showTypingIndicator() {
            const id = 'typing-' + Date.now();
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message ai-message';
            typingDiv.id = id;
            typingDiv.innerHTML = `
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            `;
            messagesContainer.appendChild(typingDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            return id;
        }

        function removeTypingIndicator(id) {
            const el = document.getElementById(id);
            if (el) el.remove();
        }
    }

    /* ===== Init ===== */
    document.addEventListener('DOMContentLoaded', () => {
        initAuth();
        initNav();
        initResume();
        initQuiz();
        initCoding();
        initScoring();

        initProfile();
    });

    function loadMonacoEditor(callback) {
        if (typeof monaco !== 'undefined') {
            if (callback) callback();
            return;
        }

        const loader = document.createElement('script');
        loader.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js';
        loader.onload = () => {
            require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' }});
            require(['vs/editor/editor.main'], function() {
                // Define Night Owl theme like image2
                monaco.editor.defineTheme('night-owl', {
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: 'comment', foreground: '637777', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'c792ea' },
                        { token: 'string', foreground: 'ecc48d' },
                        { token: 'function', foreground: '82aaff' },
                        { token: 'number', foreground: 'f78c6c' },
                        { token: 'operator', foreground: '89ddff' },
                        { token: 'type', foreground: 'ffcb6b' },
                    ],
                    colors: {
                        'editor.background': '#011627',
                        'editor.foreground': '#d6deeb',
                        'editorCursor.foreground': '#7e57c2',
                        'editor.lineHighlightBackground': '#010e17',
                        'editorLineNumber.foreground': '#4b6479',
                        'editor.selectionBackground': '#1d3b53',
                        'editorIndentGuide.background': '#0b2942',
                    }
                });

                const editorDiv = $('#codeEditor');
                if (editorDiv) {
                    monacoEditor = monaco.editor.create(editorDiv, {
                        value: "",
                        language: 'python',
                        theme: 'night-owl',
                        fontSize: 15,
                        fontFamily: "'Fira Code', monospace",
                        fontLigatures: true,
                        automaticLayout: true,
                        minimap: { enabled: false },
                        scrollBeyondLastLine: false,
                        padding: { top: 20 },
                        roundedSelection: true,
                        cursorSmoothCaretAnimation: "on"
                    });

                    // Sync language change
                    $('#codingLanguageSelector')?.addEventListener('change', (e) => {
                        const langMapping = {
                            'python': 'python',
                            'javascript': 'javascript',
                            'java': 'java',
                            'cpp': 'cpp',
                            'c': 'c',
                            'sql': 'sql',
                            'go': 'go'
                        };
                        const lang = langMapping[e.target.value] || 'python';
                        monaco.editor.setModelLanguage(monacoEditor.getModel(), lang);
                        state.currentLanguage = e.target.value;
                    });
                }
                if (callback) callback();
            });
        };
        document.head.appendChild(loader);
    }

    // --- Export to Global Scope for inline onclick handlers ---
    window.showPage = showPage;
    window.startQuiz = startQuiz;
    window.startCoding = startCodingAssessment;
})();
