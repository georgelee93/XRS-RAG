import { authService } from './auth.js';

export class AuthGuard {
    static async requireAuth(requiredRole = null) {
        // Wait for auth to initialize
        await new Promise(resolve => {
            if (authService.getUser()) {
                resolve();
            } else {
                const checkAuth = setInterval(() => {
                    if (authService.initializeAuth.completed) {
                        clearInterval(checkAuth);
                        resolve();
                    }
                }, 100);
                
                // Timeout after 5 seconds
                setTimeout(() => {
                    clearInterval(checkAuth);
                    resolve();
                }, 5000);
            }
        });

        // Check if authenticated
        if (!authService.isAuthenticated()) {
            window.location.href = '/login.html';
            return false;
        }

        // Check role if required
        if (requiredRole === 'admin') {
            const isAdmin = await authService.isAdmin();
            if (!isAdmin) {
                // Redirect regular users to chat page instead of unauthorized page
                window.location.href = '/chat.html';
                return false;
            }
        }

        return true;
    }

    static setupLogoutButton() {
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async () => {
                await authService.signOut();
            });
        }
    }

    static async updateUIForAuth() {
        const user = authService.getUser();
        const profile = await authService.getUserProfile();
        
        // Update user name display
        const userNameElement = document.getElementById('userName');
        if (userNameElement) {
            userNameElement.textContent = profile?.full_name || user?.email || '';
        }

        // Show/hide admin features
        const adminElements = document.querySelectorAll('.admin-only');
        const isAdmin = await authService.isAdmin();
        adminElements.forEach(el => {
            el.style.display = isAdmin ? 'block' : 'none';
        });
        
        // Hide/show navigation items based on role
        const adminNavItems = document.querySelectorAll('.admin-nav-item');
        adminNavItems.forEach(el => {
            el.style.display = isAdmin ? 'block' : 'none';
        });
    }
    
    static async getRedirectUrl() {
        // Determine where to redirect based on user role
        const isAdmin = await authService.isAdmin();
        return isAdmin ? '/admin.html' : '/chat.html';
    }
    
    static async redirectIfAuthenticated() {
        // If user is already authenticated, redirect to appropriate page
        if (authService.isAuthenticated()) {
            const redirectUrl = await this.getRedirectUrl();
            window.location.href = redirectUrl;
        }
    }
}

// Auto-check auth on module load
authService.initializeAuth.completed = false;
authService.initializeAuth().then(() => {
    authService.initializeAuth.completed = true;
});