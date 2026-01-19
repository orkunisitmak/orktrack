# OrkTrack - AI-Powered Garmin Fitness Dashboard

A comprehensive fitness dashboard that connects to your Garmin Connect account and uses AI (Google Gemini) to provide personalized insights, workout plans, and intelligent data analysis.

## Features

### 📊 Activity Dashboard
- Real-time sync with Garmin Connect
- Interactive charts for steps, calories, distance, and more
- Heart rate trends and zone analysis
- Sleep quality tracking with sleep stages
- Stress level monitoring

### 💬 AI Chat Assistant
- Natural language queries about your fitness data
- Context-aware responses using your complete health history
- Ask questions like "How did I sleep last week?" or "Compare my running this month vs last month"

### 📅 AI Workout Planner
- Generate personalized weekly/monthly training plans
- Plans based on your historical performance and recovery status
- Progressive overload suggestions
- Rest day recommendations based on your actual recovery metrics

### 💡 Health Insights
- AI-generated weekly health reports
- Sleep pattern analysis with improvement suggestions
- Training load vs recovery balance
- Personalized health tips

## Tech Stack

- **Frontend**: Streamlit
- **Data Visualization**: Plotly
- **Garmin API**: python-garminconnect
- **AI Model**: Google Gemini 2.0 Flash
- **Database**: SQLite + SQLAlchemy
- **Authentication**: Garth (OAuth tokens)

## Installation

### Prerequisites

- Python 3.10 or higher
- A Garmin Connect account with synced device data
- A Google Gemini API key (get one at [Google AI Studio](https://aistudio.google.com/apikey))

### Setup

1. **Clone or navigate to the project directory**:
   ```bash
   cd garmin_orktrack
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file** with your credentials:
   ```env
   GARMIN_EMAIL=your_garmin_email@example.com
   GARMIN_PASSWORD=your_garmin_password
   GEMINI_API_KEY=your_gemini_api_key
   ```

5. **Run the application**:
   ```bash
   streamlit run app.py
   ```

6. **Open your browser** to `http://localhost:8501`

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GARMIN_EMAIL` | Yes | Your Garmin Connect email |
| `GARMIN_PASSWORD` | Yes | Your Garmin Connect password |
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GARMIN_TOKEN_PATH` | No | Custom path for OAuth tokens (default: `~/.garminconnect`) |
| `APP_DEBUG` | No | Enable debug mode (default: false) |

### Customization

Edit `config.py` to customize:
- Activity type mappings and colors
- Heart rate zone thresholds
- Sleep stage colors
- Chart color palette
- Default data fetch ranges

## Project Structure

```
garmin_orktrack/
├── app.py                  # Main Streamlit entry point
├── config.py               # Application configuration
├── requirements.txt        # Python dependencies
├── services/
│   ├── garmin_service.py   # Garmin Connect API wrapper
│   ├── ai_service.py       # Gemini AI integration
│   └── data_processor.py   # Data transformation utilities
├── components/
│   ├── auth.py             # Authentication UI
│   ├── dashboard.py        # Main dashboard view
│   ├── chat.py             # AI chat interface
│   ├── planner.py          # Workout planner view
│   └── insights.py         # Health insights view
├── database/
│   ├── models.py           # SQLAlchemy models
│   └── db.py               # Database operations
├── utils/
│   ├── charts.py           # Plotly chart helpers
│   └── prompts.py          # AI prompt templates
└── assets/
    └── style.css           # Custom styling
```

## Usage Guide

### First-Time Setup

1. Launch the app and enter your Garmin credentials
2. Allow the app to sync your data (this may take a moment for the first sync)
3. Your OAuth tokens will be saved locally for future sessions

### Dashboard Navigation

- **Dashboard**: Overview of all your health metrics
- **AI Assistant**: Chat with AI about your fitness data
- **Workout Planner**: Generate and manage workout plans
- **Health Insights**: Get AI-powered analysis reports

### Example AI Queries

- "How did my sleep compare this week to last week?"
- "What's my average running pace for the past month?"
- "Am I ready for an intense workout today?"
- "Help me set a realistic step goal"
- "Analyze my heart rate trends"

## Data Privacy

- Your Garmin credentials are used only to authenticate with Garmin Connect
- OAuth tokens are stored locally on your machine
- No data is sent to third parties (except Gemini for AI features)
- All processing happens locally on your machine

## Troubleshooting

### Login Issues

- **Invalid credentials**: Ensure you're using Garmin Connect credentials (not Garmin Express)
- **Two-Factor Authentication**: You may need to use an app-specific password
- **Rate limiting**: Wait a few minutes if you see rate limit errors

### Data Not Loading

- Make sure your Garmin device has synced recently
- Check that you have data for the selected time range
- Try clearing the cache by logging out and back in

### AI Features Not Working

- Verify your Gemini API key is correct
- Check that you haven't exceeded API rate limits
- Ensure you have an active internet connection

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) - Garmin Connect API wrapper
- [Streamlit](https://streamlit.io/) - Web framework
- [Plotly](https://plotly.com/) - Data visualization
- [Google Gemini](https://ai.google.dev/) - AI capabilities
