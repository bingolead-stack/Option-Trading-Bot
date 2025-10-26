// Authentication and Security Layer - Backend API Integration

import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Session storage key
const AUTH_STORAGE_KEY = 'trading_bot_authenticated';

/**
 * Validate passkey against backend API
 */
export async function validatePasskey(passkey: string): Promise<boolean> {
  try {
    const response = await api.post('/api/auth/validate', { passkey });
    return response.data.valid === true;
  } catch (error) {
    console.error('Passkey validation error:', error);
    return false;
  }
}

/**
 * Change passkey (requires current passkey)
 */
export async function changePasskey(
  currentPasskey: string,
  newPasskey: string
): Promise<{ success: boolean; error?: string }> {
  try {
    await api.post('/api/auth/change-passkey', {
      current_passkey: currentPasskey,
      new_passkey: newPasskey,
    });
    return { success: true };
  } catch (error: any) {
    const errorMessage =
      error.response?.data?.detail || 'Failed to change passkey';
    return { success: false, error: errorMessage };
  }
}

/**
 * Create authentication session in localStorage
 */
export function createAuthSession(): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(AUTH_STORAGE_KEY, 'true');
}

/**
 * Check if user is authenticated (localStorage)
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(AUTH_STORAGE_KEY) === 'true';
}

/**
 * Logout - clear authentication
 */
export function logout(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(AUTH_STORAGE_KEY);
}
