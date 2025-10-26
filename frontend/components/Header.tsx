'use client';

import { useState, useEffect } from 'react';
import { Activity, Power, TrendingUp, AlertCircle, Settings, LogOut, Shield } from 'lucide-react';
import { apiService, BotStatus } from '@/lib/api';
import { logout } from '@/lib/auth';

interface HeaderProps {
  onAdminClick: () => void;
  onLogout: () => void;
}

export default function Header({ onAdminClick, onLogout }: HeaderProps) {
  const [status, setStatus] = useState<BotStatus>({
    running: false,
    market_open: false,
    today_pnl: 0,
    total_pnl: 0,
    positions_count: 0,
    trades_count: 0,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const data = await apiService.getBotStatus();
      setStatus(data);
    } catch (error) {
      console.error('Failed to fetch status:', error);
    }
  };

  const toggleBot = async () => {
    setLoading(true);
    try {
      if (status.running) {
        await apiService.stopBot();
      } else {
        await apiService.startBot();
      }
      await fetchStatus();
    } catch (error) {
      console.error('Failed to toggle bot:', error);
      alert('Failed to toggle bot. Check console for details.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    onLogout();
  };

  return (
    <header className="bg-slate-900/50 backdrop-blur-xl border-b border-slate-800/50 sticky top-0 z-40 animate-slide-in-down">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          {/* Logo and Title */}
          <div className="flex items-center space-x-4">
            <div className="bg-gradient-to-br from-cyan-500 via-blue-500 to-indigo-600 p-2.5 rounded-xl shadow-lg shadow-cyan-500/30 animate-pulse-glow">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent">
                Trading Bot Pro
              </h1>
              <p className="text-xs text-slate-500">TastyTrade Platform</p>
            </div>
          </div>

          {/* Center - Status Info */}
          <div className="hidden md:flex items-center space-x-4">
            {/* Market Status */}
            <div className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700/50">
              <div className={`w-2 h-2 rounded-full ${status.market_open ? 'bg-emerald-500 animate-pulse shadow-lg shadow-emerald-500/50' : 'bg-red-500'}`} />
              <span className="text-sm font-medium text-slate-300">
                {status.market_open ? 'Market Open' : 'Market Closed'}
              </span>
            </div>

            {/* Bot Status */}
            <div className={`flex items-center space-x-2 px-4 py-2 rounded-xl border ${
              status.running 
                ? 'bg-emerald-500/10 border-emerald-500/30 animate-pulse-glow' 
                : 'bg-slate-800/50 border-slate-700/50'
            }`}>
              <Activity className={`w-4 h-4 ${status.running ? 'text-emerald-400 animate-pulse' : 'text-slate-500'}`} />
              <span className={`font-semibold text-sm ${status.running ? 'text-emerald-400' : 'text-slate-500'}`}>
                {status.running ? 'ACTIVE' : 'INACTIVE'}
              </span>
            </div>
          </div>

          {/* Right - Controls */}
          <div className="flex items-center space-x-3">
            {/* Admin Button */}
            <button
              onClick={onAdminClick}
              className="p-2.5 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded-xl transition-all"
              title="Admin Settings"
            >
              <Settings className="w-5 h-5" />
            </button>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="p-2.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-xl transition-all"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>

            {/* Start/Stop Button */}
            <button
              onClick={toggleBot}
              disabled={loading}
              className={`flex items-center space-x-2 px-6 py-2.5 rounded-xl font-semibold transition-all duration-200 ${
                status.running
                  ? 'bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700 shadow-lg shadow-red-500/30'
                  : 'bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 shadow-lg shadow-emerald-500/30'
              } text-white disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <Power className="w-4 h-4" />
              <span className="hidden sm:inline">{loading ? 'Processing...' : status.running ? 'STOP' : 'START'}</span>
            </button>
          </div>
        </div>

        {/* Warning Banner */}
        {!status.market_open && status.running && (
          <div className="pb-4 animate-slide-in-up">
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-3 flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0" />
              <span className="text-sm text-yellow-300">
                Bot is running but market is closed. No trades will be executed until market opens.
              </span>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
