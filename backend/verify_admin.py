#!/usr/bin/env python3
"""
Verify admin access
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.supabase_client import SupabaseManager

def verify_admin():
    """Verify admin user exists and has correct role"""
    print("\n✅ Verifying Admin User...")
    
    try:
        supabase = SupabaseManager()
        
        # Check users table
        result = supabase.client.table('users')\
            .select('*')\
            .eq('email', 'test.user@gmail.com')\
            .execute()
        
        if result.data:
            user = result.data[0]
            print(f"\n✅ Admin User Confirmed:")
            print(f"   Email: {user['email']}")
            print(f"   Role: {user['role']}")
            print(f"   Name: {user.get('name', 'N/A')}")
            print(f"   Created: {user.get('created_at', 'N/A')}")
            
            if user['role'] == 'admin':
                print(f"\n🎉 User has ADMIN access!")
            else:
                print(f"\n⚠️  User role is '{user['role']}', not admin")
        else:
            print("❌ User not found in users table")
            
        # Check all users with admin role
        print("\n📋 All Admin Users:")
        admins = supabase.client.table('users')\
            .select('email, role')\
            .eq('role', 'admin')\
            .execute()
        
        if admins.data:
            for admin in admins.data:
                print(f"   - {admin['email']} ({admin['role']})")
        else:
            print("   No admin users found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_admin()