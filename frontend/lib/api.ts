import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface Ticker {
  symbol: string;
  enabled: boolean;
  threshold: number;
  positions?: number;
  pnl?: number;
}

export interface Position {
  id: string;
  symbol: string;
  option_type: 'CALL' | 'PUT';
  strike: number;
  entry_price: number;
  current_price: number;
  quantity: number;
  pnl: number;
  pnl_percent: number;
  entry_time: string;
}

export interface Trade {
  id: string;
  symbol: string;
  option_type: 'CALL' | 'PUT';
  strike: number;
  action: 'BUY' | 'SELL';
  price: number;
  quantity: number;
  timestamp: string;
  status: 'OPEN' | 'CLOSED';
  pnl?: number;
}

export interface BotStatus {
  running: boolean;
  market_open: boolean;
  today_pnl: number;
  total_pnl: number;
  positions_count: number;
  trades_count: number;
  uptime?: string;
}

export interface Stats {
  today_pnl: number;
  total_pnl: number;
  win_rate: number;
  total_trades: number;
  open_positions: number;
}

// API Functions
export const apiService = {
  // Bot Control
  async getBotStatus(): Promise<BotStatus> {
    const response = await api.get('/api/bot/status');
    return response.data;
  },

  async startBot(): Promise<void> {
    await api.post('/api/bot/start');
  },

  async stopBot(): Promise<void> {
    await api.post('/api/bot/stop');
  },

  // Ticker Management
  async getTickers(): Promise<Ticker[]> {
    const response = await api.get('/api/tickers');
    return response.data;
  },

  async addTicker(ticker: Omit<Ticker, 'positions' | 'pnl'>): Promise<void> {
    await api.post('/api/tickers', ticker);
  },

  async updateTicker(symbol: string, updates: Partial<Ticker>): Promise<void> {
    await api.put(`/api/tickers/${symbol}`, updates);
  },

  async deleteTicker(symbol: string): Promise<void> {
    await api.delete(`/api/tickers/${symbol}`);
  },

  async toggleTicker(symbol: string, enabled: boolean): Promise<void> {
    await api.patch(`/api/tickers/${symbol}/toggle`, { enabled });
  },

  // Positions
  async getPositions(): Promise<Position[]> {
    const response = await api.get('/api/positions');
    return response.data;
  },

  async closePosition(positionId: string): Promise<void> {
    await api.post(`/api/positions/${positionId}/close`);
  },

  // Trades
  async getTrades(filter?: 'all' | 'open' | 'closed'): Promise<Trade[]> {
    const response = await api.get('/api/trades', {
      params: { filter },
    });
    return response.data;
  },

  // Statistics
  async getStats(): Promise<Stats> {
    const response = await api.get('/api/stats');
    return response.data;
  },
};

export default api;

