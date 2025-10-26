'use client';

import { useState, useEffect } from 'react';
import { Shield, Key, X, Check, AlertTriangle } from 'lucide-react';
import { getStoredPasskey, setPasskey, isDefaultPasskey } from '@/lib/auth';

interface AdminPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AdminPanel({ isOpen, onClose }: AdminPanelProps) {
  const [currentPasskey, setCurrentPasskey] = useState('');
  const [newPasskey, setNewPasskey] = useState('');
  const [confirmPasskey, setConfirmPasskey] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setShowWarning(isDefaultPasskey());
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Validate current passkey
    if (currentPasskey !== getStoredPasskey()) {
      setError('Current passkey is incorrect');
      return;
    }

    // Validate new passkey
    if (newPasskey.length < 6) {
      setError('New passkey must be at least 6 characters');
      return;
    }

    if (newPasskey !== confirmPasskey) {
      setError('New passkeys do not match');
      return;
    }

    // Update passkey
    setPasskey(newPasskey);
    setSuccess('Passkey updated successfully!');
    setCurrentPasskey('');
    setNewPasskey('');
    setConfirmPasskey('');
    setShowWarning(false);

    // Close after 2 seconds
    setTimeout(() => {
      onClose();
    }, 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-slide-in-up">
      <div className="bg-slate-900 rounded-2xl shadow-2xl border border-slate-800 max-w-md w-full relative overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-cyan-500/20 via-blue-500/20 to-indigo-600/20 border-b border-slate-800 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-slate-100">Admin Panel</h3>
                <p className="text-xs text-slate-400">Manage security settings</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-slate-400" />
            </button>
          </div>
        </div>

        {/* Warning for default passkey */}
        {showWarning && (
          <div className="m-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl flex items-start space-x-3 animate-pulse">
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-yellow-400 mb-1">Security Alert</h4>
              <p className="text-xs text-yellow-300/80">
                You're using the default passkey. Please change it immediately for security.
              </p>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Current Passkey */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Current Passkey
            </label>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type="password"
                value={currentPasskey}
                onChange={(e) => setCurrentPasskey(e.target.value)}
                className="w-full pl-11 pr-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                placeholder="Enter current passkey"
                required
              />
            </div>
          </div>

          <div className="border-t border-slate-800 pt-5">
            {/* New Passkey */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                New Passkey
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="password"
                  value={newPasskey}
                  onChange={(e) => setNewPasskey(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                  placeholder="Enter new passkey (min 6 chars)"
                  required
                  minLength={6}
                />
              </div>
            </div>

            {/* Confirm Passkey */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Confirm New Passkey
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="password"
                  value={confirmPasskey}
                  onChange={(e) => setConfirmPasskey(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                  placeholder="Confirm new passkey"
                  required
                  minLength={6}
                />
              </div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className="bg-emerald-500/10 border border-emerald-500/50 rounded-xl p-3 flex items-center space-x-2">
              <Check className="w-5 h-5 text-emerald-400" />
              <p className="text-emerald-400 text-sm">{success}</p>
            </div>
          )}

          {/* Buttons */}
          <div className="flex space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-semibold transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-3 bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-600 hover:from-cyan-600 hover:via-blue-600 hover:to-indigo-700 text-white rounded-xl font-semibold shadow-lg shadow-cyan-500/30 transition-all"
            >
              Update Passkey
            </button>
          </div>
        </form>

        {/* Footer */}
        <div className="bg-slate-900/50 border-t border-slate-800 p-4">
          <p className="text-xs text-slate-500 text-center">
            Keep your passkey secure. Never share it with anyone.
          </p>
        </div>
      </div>
    </div>
  );
}

