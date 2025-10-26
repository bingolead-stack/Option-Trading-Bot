// Authentication and Security Layer

const PASSKEY_STORAGE_KEY = 'trading_bot_passkey';
const AUTH_STORAGE_KEY = 'trading_bot_authenticated';
const SESSION_DURATION = 24 * 60 * 60 * 1000; // 24 hours

// Default admin passkey (should be changed on first login)
const DEFAULT_PASSKEY = 'admin123';

export interface AuthSession {
  authenticated: boolean;
  timestamp: number;
  expiresAt: number;
}

// Get stored passkey (encrypted in production)
export const getStoredPasskey = (): string => {
  if (typeof window === 'undefined') return DEFAULT_PASSKEY;
  return localStorage.getItem(PASSKEY_STORAGE_KEY) || DEFAULT_PASSKEY;
};

// Set new passkey (admin only)
export const setPasskey = (newPasskey: string): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(PASSKEY_STORAGE_KEY, newPasskey);
};

// Validate passkey
export const validatePasskey = (inputPasskey: string): boolean => {
  const storedPasskey = getStoredPasskey();
  return inputPasskey === storedPasskey;
};

// Create authentication session
export const createAuthSession = (): void => {
  if (typeof window === 'undefined') return;
  const now = Date.now();
  const session: AuthSession = {
    authenticated: true,
    timestamp: now,
    expiresAt: now + SESSION_DURATION,
  };
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
};

// Check if authenticated
export const isAuthenticated = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  const sessionData = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!sessionData) return false;
  
  try {
    const session: AuthSession = JSON.parse(sessionData);
    const now = Date.now();
    
    // Check if session is expired
    if (now > session.expiresAt) {
      logout();
      return false;
    }
    
    return session.authenticated;
  } catch {
    return false;
  }
};

// Logout
export const logout = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(AUTH_STORAGE_KEY);
};

// Get session info
export const getSessionInfo = (): AuthSession | null => {
  if (typeof window === 'undefined') return null;
  
  const sessionData = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!sessionData) return null;
  
  try {
    return JSON.parse(sessionData);
  } catch {
    return null;
  }
};

// Check if passkey is default (needs to be changed)
export const isDefaultPasskey = (): boolean => {
  return getStoredPasskey() === DEFAULT_PASSKEY;
};

