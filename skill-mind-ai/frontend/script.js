(() => {
    'use strict';

    const API = 'http://127.0.0.1:5000';  // Updated to point to backend port
    const socket = io('http://127.0.0.1:5000'); // Initialize Socket.IO connection to backend

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
            if (res.status === 422) {
                showToast('Authentication error. Please logout and login again to refresh your session.', 'error');
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
                if (view === 'coding') {
                    $('#codingResult').classList.add('hidden');
                    $('#codingActive').classList.add('hidden');
                    $('#codingStart').classList.remove('hidden');
                }
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
                if (txt) txt.textContent = `Interview Readiness: ${r.readiness_level || 'Moderate'} (${(r.final_score || 0).toFixed(1)}%)`;

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
                            Readiness Level: ${r.readiness_level || 'Moderate'}<br>
                            <span style="font-size: 18px; color: #64748b;">(Score: ${r.final_score.toFixed(1)}/100)</span>
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

        // Language change handler
        $('#codingLanguageSelector')?.addEventListener('change', (e) => {
            const lang = e.target.value;
            const p = state.codingChallenges[state.codingIndex];
            if (p) {
                // Warning if editor has content
                const currentCode = $('#codeEditor').value.trim();
                const isDirty = currentCode && !currentCode.includes('Write your solution here');
                
                if (isDirty) {
                    if (!confirm('Changing language will reset your current code for this question. Proceed?')) {
                        e.target.value = state.currentLanguage || 'python';
                        return;
                    }
                }
                
                state.currentLanguage = lang;
                $('#codeEditor').value = getStarterCode(p, lang);
            }
        });
    }

    function getStarterCode(problem, language) {
        const titleSnake = problem.title.toLowerCase().replace(/\s+/g, '_');
        
        switch(language) {
            case 'javascript':
                return `function ${titleSnake}(...args) {\n    // Write your solution here\n    return null;\n}\n`;
            case 'java':
                return `public class Solution {\n    public Object ${titleSnake}(Object... args) {\n        // Write your solution here\n        return null;\n    }\n}\n`;
            case 'cpp':
                return `#include <iostream>\n#include <vector>\n\nclass Solution {\npublic:\n    void ${titleSnake}() {\n        // Write your solution here\n    }\n};\n`;
            case 'go':
                return `package main\n\nfunc ${titleSnake}() {\n    // Write your solution here\n}\n`;
            default:
                return problem.starter_code || `def ${titleSnake}(*args):\n    # Write your solution here\n    pass\n`;
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
                    'go': 'Go'
                };
                langSelector.innerHTML = state.detectedLanguages.map(l => 
                    `<option value="${l}">${langMap[l] || l}</option>`
                ).join('');
                langSelector.value = 'python';
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

        // Set Code in Editor
        $('#codeEditor').value = getStarterCode(p, state.currentLanguage || 'python');
        $('#codeOutputText').textContent = "";

        // Scroll to top
        $('#codeEditor').scrollTop = 0;

        // Start 10-minute timer for this question
        startCodingTimer();
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
                    stopCodingTimer(); // Stop before rendering next
                    setTimeout(() => {
                        renderProblem();
                        showToast(`Problem ${state.codingIndex} submitted.`, 'success');
                    }, 1000);
                } else {
                    stopCodingTimer();
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
        const progressBar = $('#codingProgressBar');
        if (progressBar) progressBar.style.width = '100%';

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

    /* ===== Scoring / Report ===== */
    function initScoring() {
        $('#generateReportBtn')?.addEventListener('click', async () => {
            const btn = $('#generateReportBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Generating...';

            try {
                const data = await api('/api/scoring/generate-report', { method: 'POST' });
                showToast('Report generated!', 'success');
                loadDashboard();
                showPage('dashboard');
            } catch (err) {
                alert(err.message || 'Error generating report.');
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
        initScoring();
    });
})();
