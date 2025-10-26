'use client';

import { useState } from 'react';
import { Lock, Shield, TrendingUp, Eye, EyeOff } from 'lucide-react';
import { validatePasskey, createAuthSession } from '@/lib/auth';

interface LoginScreenProps {
  onLogin: () => void;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [passkey, setPasskey] = useState('');
  const [showPasskey, setShowPasskey] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Validate passkey against backend API
      const isValid = await validatePasskey(passkey);

      if (isValid) {
        // Create local session
        createAuthSession();
        onLogin();
      } else {
        setError('Invalid passkey. Please try again.');
        setPasskey('');
      }
    } catch (err) {
      setError('Connection error. Please ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated background effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-blue-500/10 rounded-full blur-3xl animate-pulse-slow" />
        <div
          className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow"
          style={{ animationDelay: '1s' }}
        />
      </div>

      {/* Login Card */}
      <div className="relative z-10 w-full max-w-md">
        {/* Logo/Brand */}
        <div className="text-center mb-8 animate-slide-in-up">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-cyan-500 via-blue-500 to-indigo-600 rounded-2xl shadow-2xl shadow-cyan-500/50 mb-4 animate-pulse-glow">
            <TrendingUp className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent mb-2">
            Trading Bot Pro
          </h1>
          <p className="text-slate-400 text-sm">Secure Access Required</p>
        </div>

        {/* Login Form */}
        <div
          className="bg-slate-900/50 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-800/50 p-8 animate-slide-in-up"
          style={{ animationDelay: '0.1s' }}
        >
          <div className="flex items-center justify-center mb-6">
            <Shield className="w-6 h-6 text-cyan-400 mr-2" />
            <h2 className="text-xl font-semibold text-slate-200">Secure Login</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Passkey Input */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Passkey
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Lock className="w-5 h-5 text-slate-500" />
                </div>
                <input
                  type={showPasskey ? 'text' : 'password'}
                  value={passkey}
                  onChange={(e) => setPasskey(e.target.value)}
                  placeholder="Enter your passkey"
                  className="w-full pl-12 pr-12 py-3.5 bg-slate-800/50 border border-slate-700/50 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                  required
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowPasskey(!showPasskey)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPasskey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 animate-shake">
                <p className="text-red-400 text-sm text-center">{error}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !passkey}
              className="w-full bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-600 hover:from-cyan-600 hover:via-blue-600 hover:to-indigo-700 text-white font-semibold py-3.5 rounded-xl shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Authenticating...
                </span>
              ) : (
                'Access Dashboard'
              )}
            </button>
          </form>

          {/* Security Info */}
          <div className="mt-6 pt-6 border-t border-slate-800">
            <div className="flex items-start space-x-3 text-xs text-slate-500">
              <Shield className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <p>
                Passkey is validated against backend database. Default passkey is{' '}
                <code className="text-cyan-400 bg-slate-800 px-1 py-0.5 rounded">
                  admin123
                </code>
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          className="text-center mt-8 text-slate-500 text-sm animate-slide-in-up"
          style={{ animationDelay: '0.2s' }}
        >
          <p>Powered by TastyTrade API | Secured Access</p>
        </div>
      </div>
    </div>
  );
}
