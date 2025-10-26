# Options Trading Bot - Frontend

**Professional dark-themed, secure trading dashboard with passkey authentication.**

🎉 **NEW**: Dark theme + Security layer! See [WHATS_NEW.md](../WHATS_NEW.md) for details.

## 🎨 Features

- **Real-time Dashboard**: Live updates of bot status, P&L, and market conditions
- **Ticker Management**: Add, edit, enable/disable tickers with custom thresholds
- **Position Tracking**: Monitor open positions with live P&L updates
- **Trade History**: Complete trade log with filtering options
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Modern UI**: Built with Tailwind CSS for a professional look

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ installed
- Backend server running on `http://localhost:5000`

### Installation

1. **Install dependencies**:
```bash
cd frontend
npm install
```

2. **Configure environment** (optional):
```bash
cp .env.local.example .env.local
# Edit .env.local if your backend is not on localhost:5000
```

3. **Start development server**:
```bash
npm start
```

4. **Open browser**:
```
http://localhost:3000
```

## 📁 Project Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with fonts and metadata
│   ├── page.tsx            # Main dashboard page
│   └── globals.css         # Global styles and Tailwind
├── components/
│   ├── Header.tsx          # Top navigation with bot controls
│   ├── StatsCards.tsx      # P&L and statistics cards
│   ├── TickerManagement.tsx # Add/edit/remove tickers
│   ├── Positions.tsx       # Open positions display
│   └── TradeHistory.tsx    # Trade history table
├── lib/
│   └── api.ts              # API client and TypeScript types
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
```

## 🎯 Usage

### Adding a Ticker

1. Click **"Add Ticker"** button
2. Enter symbol (e.g., `SPY`, `QQQ`, `AAPL`)
3. Set threshold percentage (e.g., `0.5` for 0.5%)
4. Check "Enable immediately" if you want it active
5. Click **"Add Ticker"**

### Managing Tickers

- **Toggle On/Off**: Click the power button next to ticker symbol
- **Edit**: Click the edit icon to modify threshold
- **Delete**: Click the trash icon to remove ticker

### Monitoring Trades

- **Open Positions**: View all active positions with live P&L
- **Trade History**: Filter trades by All/Open/Closed
- **Close Position**: Click X button to manually close a position

### Bot Control

- **Start Bot**: Click green "Start Bot" button in header
- **Stop Bot**: Click red "Stop Bot" button when running
- **Status**: Watch for "Running" indicator and market status

## 🛠️ Development

### Available Scripts

```bash
# Development server with hot reload
npm run dev

# Production build
npm run build

# Start production server
npm run production

# Lint code
npm run lint
```

### Environment Variables

Create `.env.local` file:

```env
# API URL (default: http://localhost:5000)
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## 🎨 Customization

### Colors

Edit `tailwind.config.js` to customize the color scheme:

```js
theme: {
  extend: {
    colors: {
      primary: { ... },
      success: { ... },
      danger: { ... },
    }
  }
}
```

### Styling

The app uses Tailwind CSS utility classes. Custom styles are in:
- `app/globals.css` - Global styles and custom components
- Component files - Component-specific styles

## 📊 API Integration

The frontend communicates with the backend via REST API:

### Endpoints Used

```
GET  /api/bot/status          - Bot status and stats
POST /api/bot/start           - Start trading bot
POST /api/bot/stop            - Stop trading bot

GET  /api/tickers             - List all tickers
POST /api/tickers             - Add new ticker
PUT  /api/tickers/:symbol     - Update ticker
DELETE /api/tickers/:symbol   - Delete ticker
PATCH /api/tickers/:symbol/toggle - Toggle ticker on/off

GET  /api/positions           - Get open positions
POST /api/positions/:id/close - Close position

GET  /api/trades              - Get trade history
GET  /api/stats               - Get trading statistics
```

### TypeScript Types

All API types are defined in `lib/api.ts`:

```typescript
interface Ticker { ... }
interface Position { ... }
interface Trade { ... }
interface BotStatus { ... }
interface Stats { ... }
```

## 🔄 Real-time Updates

The dashboard automatically refreshes data:

- **Bot Status**: Every 5 seconds
- **Stats Cards**: Every 10 seconds
- **Tickers**: Every 10 seconds
- **Positions**: Every 5 seconds
- **Trades**: Every 15 seconds

## 📱 Responsive Design

The UI is fully responsive:

- **Desktop**: Full layout with all features
- **Tablet**: Optimized grid layout
- **Mobile**: Stacked layout, touch-friendly controls

## 🐛 Troubleshooting

### Backend Connection Failed

**Problem**: "Failed to fetch" errors in console

**Solution**:
1. Ensure backend is running: `cd backend && python run.py`
2. Check API URL in `.env.local`
3. Verify CORS is enabled in backend

### No Data Showing

**Problem**: Empty dashboard even though bot is running

**Solution**:
1. Check browser console for errors (F12)
2. Verify backend API endpoints are working
3. Check network tab for failed requests
4. Ensure market is open for live trading

### Styling Issues

**Problem**: Styles not loading properly

**Solution**:
```bash
# Rebuild Tailwind CSS
npm run build

# Clear Next.js cache
rm -rf .next
npm run dev
```

## 🚀 Production Deployment

### Build for Production

```bash
npm run build
npm start
```

### Environment Setup

For production, set:

```env
NEXT_PUBLIC_API_URL=https://your-backend-api.com
NODE_ENV=production
```

### Deployment Options

- **Vercel**: `vercel deploy` (recommended for Next.js)
- **Netlify**: Connect GitHub repo
- **Docker**: Create Dockerfile with Node.js
- **Self-hosted**: Build and run with PM2 or systemd

## 📄 License

Part of the Options Trading Bot project.

## 🤝 Support

For issues or questions:
1. Check the main project README
2. Review backend logs
3. Check browser console for errors
4. Ensure all dependencies are installed

---

**Happy Trading! 📈**

