'use client';

import { useState, useEffect } from 'react';
import { isAuthenticated } from '@/lib/auth';
import LoginScreen from '@/components/LoginScreen';
import AdminPanel from '@/components/AdminPanel';
import Header from '@/components/Header';
import StatsCards from '@/components/StatsCards';
import TickerManagement from '@/components/TickerManagement';
import Positions from '@/components/Positions';
import TradeHistory from '@/components/TradeHistory';

export default function Home() {
  const [authenticated, setAuthenticated] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check authentication on mount
    setAuthenticated(isAuthenticated());
    setLoading(false);
  }, []);

  const handleLogin = () => {
    setAuthenticated(true);
  };

  const handleLogout = () => {
    setAuthenticated(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-pulse-glow">
          <div className="w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (!authenticated) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 relative">
      {/* Grid pattern background */}
      <div className="absolute inset-0 grid-pattern opacity-50" />
      
      {/* Animated gradient orbs */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-cyan-500/5 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-blue-500/5 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />
      </div>

      {/* Content */}
      <div className="relative z-10">
        <Header onAdminClick={() => setShowAdmin(true)} onLogout={handleLogout} />
        
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Stats Cards */}
          <div className="animate-slide-in-up">
            <StatsCards />
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 gap-6 animate-slide-in-up" style={{ animationDelay: '0.1s' }}>
            {/* Ticker Management */}
            <TickerManagement />

            {/* Positions */}
            <Positions />

            {/* Trade History */}
            <TradeHistory />
          </div>

          {/* Footer */}
          <footer className="mt-12 pb-8 text-center animate-slide-in-up" style={{ animationDelay: '0.2s' }}>
            <div className="inline-block px-6 py-3 bg-slate-900/50 backdrop-blur-sm rounded-xl border border-slate-800/50">
              <p className="text-sm text-slate-500 mb-1">
                ⚠️ <strong className="text-slate-400">Risk Warning:</strong> Options trading involves significant risk. Always use paper trading to test strategies.
              </p>
              <p className="text-xs text-slate-600">
                Built with Next.js & TastyTrade API | Secured Access | © {new Date().getFullYear()}
              </p>
            </div>
          </footer>
        </main>
      </div>

      {/* Admin Panel Modal */}
      <AdminPanel isOpen={showAdmin} onClose={() => setShowAdmin(false)} />
    </div>
  );
}
