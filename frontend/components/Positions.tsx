'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, X, Briefcase } from 'lucide-react';
import { apiService, Position } from '@/lib/api';

export default function Positions() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchPositions = async () => {
    try {
      const data = await apiService.getPositions();
      setPositions(data);
    } catch (error) {
      console.error('Failed to fetch positions:', error);
    }
  };

  const handleClosePosition = async (positionId: string) => {
    if (!confirm('Are you sure you want to close this position?')) return;
    setLoading(positionId);
    try {
      await apiService.closePosition(positionId);
      await fetchPositions();
    } catch (error) {
      console.error('Failed to close position:', error);
      alert('Failed to close position.');
    } finally {
      setLoading(null);
    }
  };

  const formatCurrency = (value: number) => {
    return `$${value.toFixed(2)}`;
  };

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const formatPnL = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}$${value.toFixed(2)}`;
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className="card-dark">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-500/20 rounded-xl">
            <Briefcase className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">Open Positions</h2>
            <p className="text-xs text-slate-500">{positions.length} active position{positions.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
      </div>

      {positions.length === 0 ? (
        <div className="text-center py-16 bg-slate-800/30 rounded-2xl border border-slate-800/50">
          <div className="w-16 h-16 mx-auto mb-4 bg-slate-800 rounded-full flex items-center justify-center">
            <Briefcase className="w-8 h-8 text-slate-600" />
          </div>
          <p className="text-lg mb-2 text-slate-400">No open positions</p>
          <p className="text-sm text-slate-600">Positions will appear here once trades are executed</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar">
          {positions.map((position) => (
            <div
              key={position.id}
              className={`p-5 rounded-2xl transition-all relative overflow-hidden ${
                position.pnl >= 0
                  ? 'position-profit border border-emerald-500/30 hover:border-emerald-500/50'
                  : 'position-loss border border-red-500/30 hover:border-red-500/50'
              }`}
            >
              {/* Glow effect */}
              <div className={`absolute inset-0 ${position.pnl >= 0 ? 'bg-emerald-500/5' : 'bg-red-500/5'}`} />
              
              <div className="relative z-10 flex items-center justify-between">
                {/* Position Info */}
                <div className="flex items-center space-x-4">
                  {/* Symbol and Type */}
                  <div className="flex items-center space-x-2">
                    <div className="bg-gradient-to-br from-cyan-500 to-blue-600 text-white px-4 py-2 rounded-xl font-bold shadow-lg">
                      {position.symbol}
                    </div>
                    <div className={`px-4 py-2 rounded-xl font-semibold text-sm shadow-lg ${
                      position.option_type === 'CALL'
                        ? 'bg-gradient-to-r from-emerald-500 to-green-600 text-white'
                        : 'bg-gradient-to-r from-red-500 to-rose-600 text-white'
                    }`}>
                      {position.option_type}
                    </div>
                  </div>

                  {/* Details */}
                  <div className="flex items-center space-x-5 text-sm">
                    <div>
                      <span className="text-slate-500">Strike:</span>
                      <span className="ml-2 font-semibold text-slate-300">
                        ${position.strike}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-slate-500">Entry:</span>
                      <span className="font-semibold text-slate-300">
                        {formatCurrency(position.entry_price)}
                      </span>
                      <span className="text-slate-600">→</span>
                      <span className="text-slate-500">Current:</span>
                      <span className="font-semibold text-cyan-400">
                        {formatCurrency(position.current_price)}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Qty:</span>
                      <span className="ml-2 font-semibold text-slate-300">
                        {position.quantity}
                      </span>
                    </div>
                  </div>

                  {/* P&L */}
                  <div className="flex items-center space-x-3 px-4 py-2 rounded-xl bg-slate-900/50">
                    {position.pnl >= 0 ? (
                      <TrendingUp className="w-6 h-6 text-emerald-400" />
                    ) : (
                      <TrendingDown className="w-6 h-6 text-red-400" />
                    )}
                    <div>
                      <div className={`text-xl font-bold ${
                        position.pnl >= 0 ? 'glow-text-green' : 'glow-text-red'
                      }`}>
                        {formatPnL(position.pnl)}
                      </div>
                      <div className={`text-xs font-semibold ${
                        position.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {formatPercent(position.pnl_percent)}
                      </div>
                    </div>
                  </div>

                  {/* Time */}
                  <div className="text-xs text-slate-500">
                    {formatTime(position.entry_time)}
                  </div>
                </div>

                {/* Close Button */}
                <button
                  onClick={() => handleClosePosition(position.id)}
                  disabled={loading === position.id}
                  className="p-2.5 text-red-400 hover:bg-red-500/10 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-transparent hover:border-red-500/30"
                  title="Close Position"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
