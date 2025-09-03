import { createClient } from '@supabase/supabase-js';
import { SUPABASE_CONFIG } from './config.js';

// Initialize Supabase client
const supabase = createClient(
    SUPABASE_CONFIG.url,
    SUPABASE_CONFIG.anonKey
);

export class AuthService {
    constructor() {
        this.user = null;
        this.session = null;
        this.initializeAuth();
    }

    async initializeAuth() {
        // Check for existing session
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
            this.session = session;
            this.user = session.user;
        }

        // Listen for auth changes
        supabase.auth.onAuthStateChange((event, session) => {
            this.session = session;
            this.user = session?.user || null;
            
            // Emit custom event for UI updates
            window.dispatchEvent(new CustomEvent('authStateChanged', {
                detail: { event, session, user: this.user }
            }));
        });
    }

    async signUp(email, password, fullName = '') {
        try {
            const { data, error } = await supabase.auth.signUp({
                email,
                password,
                options: {
                    data: { full_name: fullName }
                }
            });

            if (error) throw error;
            
            return { 
                success: true, 
                message: '회원가입이 완료되었습니다. 이메일을 확인해주세요.',
                data 
            };
        } catch (error) {
            return { 
                success: false, 
                error: error.message 
            };
        }
    }

    async signIn(email, password) {
        try {
            const { data, error } = await supabase.auth.signInWithPassword({
                email,
                password
            });

            if (error) throw error;

            // Get user profile
            const profile = await this.getUserProfile();
            
            return { 
                success: true, 
                data: { ...data, profile }
            };
        } catch (error) {
            return { 
                success: false, 
                error: error.message 
            };
        }
    }

    async signOut() {
        try {
            const { error } = await supabase.auth.signOut();
            if (error) throw error;
            
            // Clear local state
            this.user = null;
            this.session = null;
            
            // Redirect to login
            window.location.href = '/login.html';
            
            return { success: true };
        } catch (error) {
            return { 
                success: false, 
                error: error.message 
            };
        }
    }

    async resetPassword(email) {
        try {
            const { error } = await supabase.auth.resetPasswordForEmail(email, {
                redirectTo: `${window.location.origin}/auth/reset-password`
            });

            if (error) throw error;
            
            return { 
                success: true, 
                message: '비밀번호 재설정 링크를 이메일로 전송했습니다.' 
            };
        } catch (error) {
            return { 
                success: false, 
                error: error.message 
            };
        }
    }

    async updatePassword(newPassword) {
        try {
            const { error } = await supabase.auth.updateUser({
                password: newPassword
            });

            if (error) throw error;
            
            return { 
                success: true, 
                message: '비밀번호가 변경되었습니다.' 
            };
        } catch (error) {
            return { 
                success: false, 
                error: error.message 
            };
        }
    }

    async getUserProfile() {
        if (!this.user) return null;

        try {
            const { data, error } = await supabase
                .from('user_profiles')
                .select('*')
                .eq('id', this.user.id)
                .single();

            if (error) {
                // If profile doesn't exist, create it
                if (error.code === 'PGRST116') {
                    return await this.createUserProfile();
                }
                throw error;
            }
            return data;
        } catch (error) {
            console.error('Error fetching profile:', error);
            // Return a default profile structure
            return {
                id: this.user.id,
                email: this.user.email,
                role: 'user',
                full_name: null
            };
        }
    }
    
    async createUserProfile() {
        if (!this.user) return null;
        
        try {
            const profileData = {
                id: this.user.id,
                email: this.user.email,
                role: 'user',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            };
            
            const { data, error } = await supabase
                .from('user_profiles')
                .insert(profileData)
                .select()
                .single();
                
            if (error) throw error;
            
            console.log('User profile created:', data);
            return data;
        } catch (error) {
            console.error('Error creating profile:', error);
            return {
                id: this.user.id,
                email: this.user.email,
                role: 'user',
                full_name: null
            };
        }
    }

    async updateProfile(updates) {
        if (!this.user) return { success: false, error: 'Not authenticated' };

        try {
            const { data, error } = await supabase
                .from('user_profiles')
                .update(updates)
                .eq('id', this.user.id)
                .select()
                .single();

            if (error) throw error;
            
            return { success: true, data };
        } catch (error) {
            return { 
                success: false, 
                error: error.message 
            };
        }
    }

    getSession() {
        return this.session;
    }

    getUser() {
        return this.user;
    }

    isAuthenticated() {
        return !!this.session;
    }

    async isAdmin() {
        const profile = await this.getUserProfile();
        return profile?.role === 'admin';
    }

    // Get auth headers for API calls
    getAuthHeaders() {
        if (!this.session) return {};
        
        return {
            'Authorization': `Bearer ${this.session.access_token}`
        };
    }
    
    // Setup session timeout monitoring
    setupSessionTimeout() {
        // Check session validity every 5 minutes
        setInterval(async () => {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) {
                window.location.href = '/login.html';
            }
        }, 5 * 60 * 1000);
    }
    
    async refreshSession() {
        const { data: { session }, error } = await supabase.auth.refreshSession();
        if (error) {
            await this.signOut();
        }
        return session;
    }
}

// Export singleton instance
export const authService = new AuthService();