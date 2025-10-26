'use client';

import { useState, useEffect } from 'react';
import { Plus, Trash2, Power, Edit2, Save, X, TrendingUp } from 'lucide-react';
import { apiService, Ticker } from '@/lib/api';

export default function TickerManagement() {
  const [tickers, setTickers] = useState<Ticker[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingSymbol, setEditingSymbol] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    symbol: '',
    threshold: 0.5,
    enabled: true,
  });

  useEffect(() => {
    fetchTickers();
    const interval = setInterval(fetchTickers, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchTickers = async () => {
    try {
      const data = await apiService.getTickers();
      setTickers(data);
    } catch (error) {
      console.error('Failed to fetch tickers:', error);
    }
  };

  const handleAddTicker = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiService.addTicker({
        symbol: formData.symbol.toUpperCase(),
        threshold: formData.threshold,
        enabled: formData.enabled,
      });
      setFormData({ symbol: '', threshold: 0.5, enabled: true });
      setShowAddForm(false);
      await fetchTickers();
    } catch (error) {
      console.error('Failed to add ticker:', error);
      alert('Failed to add ticker. It may already exist or there was an error.');
    }
  };

  const handleDeleteTicker = async (symbol: string) => {
    if (!confirm(`Are you sure you want to delete ${symbol}?`)) return;
    try {
      await apiService.deleteTicker(symbol);
      await fetchTickers();
    } catch (error) {
      console.error('Failed to delete ticker:', error);
      alert('Failed to delete ticker.');
    }
  };

  const handleToggleTicker = async (symbol: string, enabled: boolean) => {
    try {
      await apiService.toggleTicker(symbol, !enabled);
      await fetchTickers();
    } catch (error) {
      console.error('Failed to toggle ticker:', error);
    }
  };

  const startEditing = (ticker: Ticker) => {
    setEditingSymbol(ticker.symbol);
    setFormData({
      symbol: ticker.symbol,
      threshold: ticker.threshold,
      enabled: ticker.enabled,
    });
  };

  const saveEdit = async (symbol: string) => {
    try {
      await apiService.updateTicker(symbol, {
        threshold: formData.threshold,
        enabled: formData.enabled,
      });
      setEditingSymbol(null);
      await fetchTickers();
    } catch (error) {
      console.error('Failed to update ticker:', error);
      alert('Failed to update ticker.');
    }
  };

  const cancelEdit = () => {
    setEditingSymbol(null);
    setFormData({ symbol: '', threshold: 0.5, enabled: true });
  };

  const formatCurrency = (value?: number) => {
    if (value === undefined) return '$0.00';
    const sign = value >= 0 ? '+' : '';
    return `${sign}$${value.toFixed(2)}`;
  };

  return (
    <div className="card-dark">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/20 rounded-xl">
            <TrendingUp className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">Ticker Management</h2>
            <p className="text-xs text-slate-500">Configure trading symbols</p>
          </div>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-semibold transition-all ${
            showAddForm
              ? 'bg-slate-800 text-slate-300 border border-slate-700'
              : 'bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-600 text-white shadow-lg shadow-cyan-500/30'
          }`}
        >
          {showAddForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          <span>{showAddForm ? 'Cancel' : 'Add Ticker'}</span>
        </button>
      </div>

      {/* Add Ticker Form */}
      {showAddForm && (
        <form onSubmit={handleAddTicker} className="mb-6 p-5 bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-indigo-600/10 border border-cyan-500/30 rounded-2xl animate-slide-in-up">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Symbol *
              </label>
              <input
                type="text"
                required
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                placeholder="SPY"
                className="input-dark w-full"
                maxLength={10}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Threshold (%) *
              </label>
              <input
                type="number"
                required
                step="0.1"
                min="0"
                max="100"
                value={formData.threshold}
                onChange={(e) => setFormData({ ...formData, threshold: parseFloat(e.target.value) })}
                className="input-dark w-full"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.enabled}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                  className="w-4 h-4 text-cyan-600 bg-slate-800 border-slate-700 rounded focus:ring-cyan-500"
                />
                <span className="text-sm font-medium text-slate-300">Enable immediately</span>
              </label>
            </div>
          </div>
          <button type="submit" className="btn-success-dark w-full">
            <Plus className="w-4 h-4 inline mr-2" />
            Add Ticker
          </button>
        </form>
      )}

      {/* Tickers List */}
      <div className="space-y-3">
        {tickers.length === 0 ? (
          <div className="text-center py-16 bg-slate-800/30 rounded-2xl border border-slate-800/50">
            <div className="w-16 h-16 mx-auto mb-4 bg-slate-800 rounded-full flex items-center justify-center">
              <TrendingUp className="w-8 h-8 text-slate-600" />
            </div>
            <p className="text-lg mb-2 text-slate-400">No tickers added yet</p>
            <p className="text-sm text-slate-600">Click "Add Ticker" to get started</p>
          </div>
        ) : (
          tickers.map((ticker) => (
            <div
              key={ticker.symbol}
              className={`p-5 rounded-2xl border-2 transition-all ${
                ticker.enabled
                  ? 'bg-gradient-to-r from-emerald-500/10 to-green-500/10 border-emerald-500/30 hover:border-emerald-500/50'
                  : 'bg-slate-800/30 border-slate-800/50'
              }`}
            >
              {editingSymbol === ticker.symbol ? (
                // Edit Mode
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Symbol</label>
                    <input
                      type="text"
                      disabled
                      value={ticker.symbol}
                      className="input-dark w-full opacity-50 cursor-not-allowed text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Threshold (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={formData.threshold}
                      onChange={(e) => setFormData({ ...formData, threshold: parseFloat(e.target.value) })}
                      className="input-dark w-full text-sm"
                    />
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.enabled}
                        onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                        className="w-4 h-4 text-cyan-600 bg-slate-800 border-slate-700 rounded"
                      />
                      <span className="text-sm font-medium text-slate-300">Enabled</span>
                    </label>
                  </div>
                  <div className="flex items-end space-x-2">
                    <button
                      onClick={() => saveEdit(ticker.symbol)}
                      className="btn-success-dark flex items-center space-x-1 flex-1"
                    >
                      <Save className="w-4 h-4" />
                      <span className="text-sm">Save</span>
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="btn-secondary-dark flex items-center space-x-1"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ) : (
                // View Mode
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-6">
                    {/* Symbol */}
                    <div className="flex items-center space-x-3">
                      <div className="bg-gradient-to-br from-cyan-500 to-blue-600 text-white px-5 py-2.5 rounded-xl font-bold text-lg shadow-lg">
                        {ticker.symbol}
                      </div>
                      <button
                        onClick={() => handleToggleTicker(ticker.symbol, ticker.enabled)}
                        className={`flex items-center space-x-2 px-4 py-2 rounded-full font-semibold text-sm transition-all shadow-lg ${
                          ticker.enabled
                            ? 'bg-gradient-to-r from-emerald-500 to-green-600 text-white shadow-emerald-500/30'
                            : 'bg-slate-800 text-slate-400 shadow-slate-900/50'
                        }`}
                      >
                        <Power className="w-3.5 h-3.5" />
                        <span>{ticker.enabled ? 'ON' : 'OFF'}</span>
                      </button>
                    </div>

                    {/* Stats */}
                    <div className="flex items-center space-x-6 text-sm">
                      <div>
                        <span className="text-slate-500">Threshold:</span>
                        <span className="ml-2 font-semibold text-cyan-400">{ticker.threshold}%</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Positions:</span>
                        <span className="ml-2 font-semibold text-indigo-400">{ticker.positions || 0}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">P&L:</span>
                        <span className={`ml-2 font-semibold ${(ticker.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {formatCurrency(ticker.pnl)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => startEditing(ticker)}
                      className="p-2.5 text-cyan-400 hover:bg-cyan-500/10 rounded-xl transition-colors border border-transparent hover:border-cyan-500/30"
                      title="Edit"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteTicker(ticker.symbol)}
                      className="p-2.5 text-red-400 hover:bg-red-500/10 rounded-xl transition-colors border border-transparent hover:border-red-500/30"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
