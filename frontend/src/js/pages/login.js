import { authService } from '../auth.js';
import { AuthGuard } from '../authGuard.js';

// Redirect if already authenticated
AuthGuard.redirectIfAuthenticated();

const form = document.getElementById('loginForm');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const loginButton = document.getElementById('loginButton');
const forgotPassword = document.getElementById('forgotPassword');
const alertContainer = document.getElementById('alertContainer');
const alertMessage = document.getElementById('alertMessage');

function showAlert(message, type = 'error') {
    alertContainer.classList.remove('hidden');
    alertMessage.textContent = message;
    alertMessage.className = `rounded-md p-4 text-sm ${
        type === 'error' 
            ? 'bg-red-50 text-red-800' 
            : 'bg-green-50 text-green-800'
    }`;
}

function hideAlert() {
    alertContainer.classList.add('hidden');
}

async function handleLogin(e) {
    e.preventDefault();
    hideAlert();
    
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    
    if (!email || !password) {
        showAlert('이메일과 비밀번호를 입력해주세요.');
        return;
    }
    
    loginButton.disabled = true;
    loginButton.textContent = '로그인 중...';
    
    try {
        const result = await authService.signIn(email, password);
        
        if (result.success) {
            showAlert('로그인 성공! 잠시 후 이동합니다...', 'success');
            
            // Redirect based on user role
            const redirectUrl = await AuthGuard.getRedirectUrl();
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, 1000);
        } else {
            showAlert(result.error || '로그인에 실패했습니다.');
            loginButton.disabled = false;
            loginButton.textContent = '로그인';
        }
    } catch (error) {
        console.error('Login error:', error);
        showAlert(error.message || '로그인 중 오류가 발생했습니다.');
        loginButton.disabled = false;
        loginButton.textContent = '로그인';
    }
}

async function handleForgotPassword(e) {
    e.preventDefault();
    const email = emailInput.value.trim();
    
    if (!email) {
        showAlert('비밀번호 재설정을 위해 이메일을 입력해주세요.');
        return;
    }
    
    try {
        await authService.resetPassword(email);
        showAlert('비밀번호 재설정 이메일을 발송했습니다. 이메일을 확인해주세요.', 'success');
    } catch (error) {
        console.error('Password reset error:', error);
        showAlert(error.message || '비밀번호 재설정 중 오류가 발생했습니다.');
    }
}

// Event listeners
form.addEventListener('submit', handleLogin);
forgotPassword.addEventListener('click', handleForgotPassword);

// Auto-focus email input
emailInput.focus();