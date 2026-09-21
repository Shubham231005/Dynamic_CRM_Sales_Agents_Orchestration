# 🤖 Dynamic CRM Sales Agents Orchestration

A full-stack AI-powered CRM system that autonomously finds leads, researches them via web scraping, scores them with LLMs, and executes multi-channel outreach (Email, WhatsApp, Call, Instagram DM, Telegram).

---

## 🗂 Project Structure

```
Dynamic_CRM_Sales_Agents_Orchestration/
├── sales-agent/          # Python FastAPI backend
│   ├── app/
│   │   ├── agents/       # AI agents (lead gen, scoring, enrichment, etc.)
│   │   ├── api/routes/   # FastAPI route handlers
│   │   ├── database/     # SQLAlchemy models & DB setup
│   │   ├── providers/    # Lead sources (Google Maps scraper, Mock)
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic services
│   │   └── utils/        # Cleaners, validators
│   ├── .env              # YOU MUST CREATE THIS (see below)
│   ├── requirements.txt
│   └── run.py
└── frontend/             # React + Vite frontend
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   └── index.css
    └── package.json
```

---

## ⚙️ Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| Git | any | https://git-scm.com |

---

## 🚀 Setup & Run (Step by Step)

### Step 1 — Clone the repository

```bash
git clone https://github.com/Shubham231005/Dynamic_CRM_Sales_Agents_Orchestration.git
cd Dynamic_CRM_Sales_Agents_Orchestration
```

---

### Step 2 — Set up the Backend

```bash
cd sales-agent
```

#### 2a. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

#### 2b. Install Python dependencies

```bash
pip install -r requirements.txt
```

#### 2c. Install Playwright browsers (needed for Google Maps lead scraping)

```bash
playwright install chromium
```

#### 2d. Create the `.env` file

Create a file called `.env` inside the `sales-agent/` folder:

```env
APP_ENV=development
DATABASE_URL=sqlite:///./sales_agent.db
LOG_LEVEL=INFO

# Required for AI scoring (free key at https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Optional — Email outreach
EMAIL_ADDRESS=your_gmail@gmail.com
EMAIL_PASSWORD=your_16_digit_app_password

# Optional — WhatsApp / Call outreach (Twilio)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

# Optional — AI calling (Bland.ai)
BLAND_API_KEY=your_bland_api_key

# Optional — Instagram DM outreach
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

# Optional — Telegram outreach
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id
```

> **Only `GROQ_API_KEY` is required** for the core scoring feature.
> Get a free key at: https://console.groq.com → Sign up → API Keys → Create

#### 2e. Initialize the database

The database (`sales_agent.db`) is created automatically on first run. If you get errors about missing columns after pulling a newer version, run this one-time migration:

```bash
python -c "
import sqlite3
conn = sqlite3.connect('sales_agent.db')
cur = conn.cursor()
migrations = [
    'ALTER TABLE evidence ADD COLUMN classification TEXT',
    'ALTER TABLE company_profiles ADD COLUMN annual_revenue REAL',
    'ALTER TABLE company_profiles ADD COLUMN profit_margin_pct REAL',
    'ALTER TABLE company_profiles ADD COLUMN debt_to_equity_ratio REAL',
    'ALTER TABLE company_profiles ADD COLUMN revenue_growth_yoy REAL',
    'ALTER TABLE company_profiles ADD COLUMN financial_health_score REAL',
]
for sql in migrations:
    try:
        cur.execute(sql)
        print('OK:', sql)
    except Exception as e:
        print('Skip:', e)
conn.commit()
conn.close()
print('Migration complete!')
"
```

#### 2f. Start the backend server

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- Backend API: **http://127.0.0.1:8000**
- Interactive API docs: **http://127.0.0.1:8000/docs**

---

### Step 3 — Set up the Frontend

Open a **new terminal** (keep the backend running in the first terminal):

```bash
# From project root
cd frontend

npm install

npm run dev
```

- Frontend UI: **http://localhost:5173**

---

## 🧠 How to Use

### 1. Find Leads
1. Open **http://localhost:5173** in your browser
2. Go to the **"Find Leads"** tab
3. Enter a **Target Industry** (e.g. `Dental Clinics`) and **Target Location** (e.g. `Mumbai`)
4. Click **"Find Quality Leads"**
5. A real browser will open and scrape Google Maps for businesses matching your query
6. Leads are stored automatically in the database

### 2. View & Score Leads
1. Switch to the **"My Leads"** tab
2. All stored leads are shown automatically
3. Unscored leads are **automatically scored by AI** in the background — no button needed
4. Each lead shows a **fit score (0–100%)** and an **AI analysis**

### 3. Execute Outreach
1. On any lead card, click the outreach channel you want: **Call**, **WhatsApp**, **Email**, **Insta DM**, or **Telegram**
2. The AI agent will execute the outreach using your credentials from Settings
3. First-time: Go to **Settings** tab and add your credentials

---

## 🔑 Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/leads/generate` | Find & store leads (provider: `google_maps` or `mock`) |
| `GET` | `/api/leads` | List all leads from database |
| `POST` | `/api/strategy/orchestrate-batch` | Batch auto-score multiple leads |
| `POST` | `/api/strategy/leads/{id}/strategize` | Score a single lead |
| `POST` | `/api/outreach/execute/{id}/{channel}` | Execute outreach (email/call/whatsapp/instagram/telegram) |
| `GET` | `/api/settings` | Get saved credentials |
| `POST` | `/api/settings` | Save/update credentials |

---

## 🛠 Troubleshooting

| Problem | Solution |
|---------|----------|
| Leads not showing in UI | Run the DB migration script in Step 2e |
| AI scoring fails / no score shown | Make sure `GROQ_API_KEY` is set correctly in `sales-agent/.env` |
| Google Maps scraping doesn't work | Run `playwright install chromium` |
| CORS errors in browser console | Ensure backend is running on port **8000** |
| `npm install` fails | Install Node.js 18 or higher |
| Port 8000 already in use | Kill the process using it or change the port in the uvicorn command |

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python 3.10+, FastAPI, Uvicorn |
| Database | SQLite via SQLAlchemy ORM |
| AI / LLM | Groq API (Llama 3.3 70B), Google Gemini |
| Lead Scraping | Playwright (headless Chromium) |
| Frontend | React 18, Vite, Lucide Icons |
| Email Outreach | Python SMTP (Gmail App Password) |
| Call/SMS/WhatsApp | Twilio API |
| AI Calling | Bland.ai |
| Instagram DM | Playwright automation |
| Telegram | Telegram Bot API |

---

## 📄 License

MIT — free to use, modify, and distribute.
