# Pokemon Showdown LLM Battle Arena Web Interface

A React-based web interface for viewing live Pokemon battles between LLMs with real-time leaderboard updates, styled like Pokemon Showdown's battle interface.

## Features

- **Live Battle Display**: Watch Pokemon battles in real-time with move delays (10-30s) for better viewing experience
- **Integrated Chat**: Local Pokemon Showdown chat panel beside the battle view
- **Battle Info Panel**: Control battle scheduling and view current status
- **Real-time Leaderboard**: See LLM rankings update live below the battle area
- **Automatic Scheduling**: 5-minute breaks between matches with countdown
- **Responsive Design**: Adapts to different screen sizes

## Layout

The interface follows Pokemon Showdown's familiar layout:
- **Top**: Header with title
- **Main Area**:
  - **Left**: Live battle display
  - **Right**: Integrated chat from local Pokemon Showdown
  - **Below Battle**: Battle scheduling controls and status
- **Bottom**: Full-width leaderboard with real-time updates

## Local Development

1. Install dependencies:
```bash
cd web
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Start the backend servers (in the parent directory):
```bash
python src/bot_vs_bot/run_bot_vs_bot.py --mode continuous --leaderboard
```

The web interface will be available at http://localhost:3000

## Deployment to Vercel

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Deploy:
```bash
vercel
```

3. Set environment variables in Vercel dashboard:
- `API_URL`: Your backend API URL
- `WEBSOCKET_URL`: Your websocket server URL

## Configuration

Update `vercel.json` with your actual backend URLs before deploying:

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-actual-backend.com/api/:path*"
    }
  ]
}
```

## Architecture

- **Frontend**: React + Vite
- **Real-time Updates**: Socket.IO
- **API Communication**: Axios
- **Styling**: Custom CSS with dark theme

## Backend Requirements

The web interface requires:
- Leaderboard API server (port 5000)
- Battle relay WebSocket server (port 5001)
- Pokemon Showdown server connection