# OrkTrack - AI-Powered Garmin Fitness Dashboard

A comprehensive fitness dashboard that connects to your Garmin account and provides AI-powered insights, training plans, and activity analysis.

## Features

- **Dashboard**: Real-time health metrics including sleep score, body battery, HRV, resting HR
- **Activity Analysis**: AI-powered analysis of all activities (running, yoga, cold plunge, strength, etc.)
- **Training Planner**: Generate personalized weekly or monthly training plans based on your goals
- **Health Insights**: AI-generated insights based on your sleep, activity, and recovery data
- **AI Chat**: Ask questions about your training and get personalized advice
- **Data Sync**: Automatic background sync with manual refresh option

## Tech Stack

### Backend
- **FastAPI** - Python web framework
- **SQLAlchemy** - Database ORM
- **Google Gemini AI** - AI analysis and plan generation
- **Garmin Connect API** - Fitness data integration

### Frontend
- **React** + **TypeScript**
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Framer Motion** - Animations
- **TanStack Query** - Data fetching

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Garmin Connect account
- Google AI API key (Gemini)

### Backend Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key
```

4. Run the backend:
```bash
uvicorn backend.main:app --reload --port 8000
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

4. Open http://localhost:5173 in your browser

## Usage

1. Log in with your Garmin Connect credentials
2. View your dashboard with real-time health metrics
3. Click on activities to see AI-powered analysis
4. Use the Planner to generate training plans
5. Check Insights for weekly/monthly health summaries
6. Use AI Chat for personalized training advice

## Project Structure

```
garmin_orktrack/
├── backend/
│   ├── main.py          # FastAPI app entry
│   ├── prompts.py       # AI prompt engineering
│   └── routers/         # API endpoints
├── database/
│   ├── models.py        # SQLAlchemy models
│   └── db.py            # Database operations
├── services/
│   └── garmin_service.py # Garmin API integration
├── frontend/
│   └── src/
│       ├── components/  # React components
│       ├── pages/       # Page components
│       └── lib/         # Utilities & API client
└── requirements.txt
```

## License

MIT
