'use client';

import { useEffect, useState } from 'react';
import { DollarSign, TrendingUp, Activity, BarChart3, Target } from 'lucide-react';
import { apiService, Stats } from '@/lib/api';

export default function StatsCards() {
  const [stats, setStats] = useState<Stats>({
    today_pnl: 0,
    total_pnl: 0,
    win_rate: 0,
    total_trades: 0,
    open_positions: 0,
  });

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const data = await apiService.getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const formatCurrency = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}$${value.toFixed(2)}`;
  };

  const formatPercent = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      {/* Today P&L */}
      <div className="stat-card-dark group relative">
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-slate-400">Today P&L</h3>
            <div className={`p-2.5 rounded-xl ${stats.today_pnl >= 0 ? 'bg-emerald-500/20' : 'bg-red-500/20'}`}>
              <DollarSign className={`w-5 h-5 ${stats.today_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`} />
            </div>
          </div>
          <p className={`text-3xl font-bold ${stats.today_pnl >= 0 ? 'glow-text-green' : 'glow-text-red'}`}>
            {formatCurrency(stats.today_pnl)}
          </p>
          <div className="mt-2 text-xs text-slate-500">
            Daily Performance
          </div>
        </div>
      </div>

      {/* Total P&L */}
      <div className="stat-card-dark group relative">
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-slate-400">Total P&L</h3>
            <div className={`p-2.5 rounded-xl ${stats.total_pnl >= 0 ? 'bg-emerald-500/20' : 'bg-red-500/20'}`}>
              <TrendingUp className={`w-5 h-5 ${stats.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`} />
            </div>
          </div>
          <p className={`text-3xl font-bold ${stats.total_pnl >= 0 ? 'glow-text-green' : 'glow-text-red'}`}>
            {formatCurrency(stats.total_pnl)}
          </p>
          <div className="mt-2 text-xs text-slate-500">
            All-Time Total
          </div>
        </div>
      </div>

      {/* Open Positions */}
      <div className="stat-card-dark group relative">
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-slate-400">Active</h3>
            <div className="p-2.5 rounded-xl bg-cyan-500/20">
              <Activity className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <p className="text-3xl font-bold glow-text-cyan">{stats.open_positions}</p>
          <div className="mt-2 text-xs text-slate-500">
            Open Positions
          </div>
        </div>
      </div>

      {/* Total Trades */}
      <div className="stat-card-dark group relative">
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-slate-400">Volume</h3>
            <div className="p-2.5 rounded-xl bg-indigo-500/20">
              <BarChart3 className="w-5 h-5 text-indigo-400" />
            </div>
          </div>
          <p className="text-3xl font-bold text-indigo-400">{stats.total_trades}</p>
          <div className="mt-2 text-xs text-slate-500">
            Total Trades
          </div>
        </div>
      </div>

      {/* Win Rate */}
      <div className="stat-card-dark group relative">
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-slate-400">Win Rate</h3>
            <div className={`p-2.5 rounded-xl ${stats.win_rate >= 50 ? 'bg-emerald-500/20' : 'bg-yellow-500/20'}`}>
              <Target className={`w-5 h-5 ${stats.win_rate >= 50 ? 'text-emerald-400' : 'text-yellow-400'}`} />
            </div>
          </div>
          <p className={`text-3xl font-bold ${stats.win_rate >= 50 ? 'text-emerald-400' : 'text-yellow-400'}`}>
            {formatPercent(stats.win_rate)}
          </p>
          <div className="mt-2 text-xs text-slate-500">
            Success Rate
          </div>
        </div>
        {/* Progress bar */}
        <div className="mt-3 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-1000 ${stats.win_rate >= 50 ? 'bg-gradient-to-r from-emerald-500 to-green-600' : 'bg-gradient-to-r from-yellow-500 to-orange-600'}`}
            style={{ width: `${Math.min(stats.win_rate, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
