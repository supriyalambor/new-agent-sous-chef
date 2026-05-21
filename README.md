# 🍳 Sous Chef v2

> AI-powered meal planning and grocery agent with voice input, built with LangGraph + FastAPI + React PWA.

## Architecture

```
frontend/          React + Vite PWA (deploy to Vercel)
backend/           Python + FastAPI + LangGraph (deploy to Railway)
```

## Features
- 🎤 Voice input (Web Speech API)
- 💬 Conversational AI agent (LangGraph + OpenRouter)
- 🧠 Meal memory — never repeats combos
- 📅 Weekly meal planning with proper macro tracking
- 🛒 Smart shopping list by platform
- 📊 Expense tracker
- 📧 Auto email grocery list
- 📱 PWA — install on phone like native app

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env  # fill in your keys
npm run dev
```

## Environment Variables

### Backend
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_SERVICE_KEY` — Supabase service role key
- `OPENROUTER_API_KEY` — OpenRouter free API key
- `RESEND_API_KEY` — Resend email API key
- `SUPRIYA_EMAIL` — Supriya's email
- `VIVEK_EMAIL` — Vivek's email

### Frontend
- `VITE_SUPABASE_URL` — Supabase project URL
- `VITE_SUPABASE_ANON_KEY` — Supabase anon key
- `VITE_API_URL` — Backend Railway URL

## Deploy

### Backend → Railway
1. Connect GitHub repo to Railway
2. Set root directory to `backend/`
3. Add environment variables
4. Deploy

### Frontend → Vercel
1. Connect GitHub repo to Vercel
2. Set root directory to `frontend/`
3. Add environment variables
4. Deploy

## Tech Stack
React · Vite · FastAPI · LangGraph · LangChain · OpenRouter · Supabase · Railway · Vercel
