# Sous Chef Agent — Project Summary

## What We Built
A full-stack AI meal planning agent for Supriya + Vivek in Bengaluru.
Goal: Reduce food spend from ₹55-60k/month to ₹32k/month through structured weekly planning.

## Live URLs
- Frontend: https://new-agent-sous-chef.vercel.app
- Backend: https://new-agent-sous-chef-production.up.railway.app
- Old V1: https://sous-chef-rouge.vercel.app (keep as reference)

## GitHub
- New repo: https://github.com/supriyalambor/new-agent-sous-chef
- Old repo: https://github.com/supriyalambor/sous-chef

## Tech Stack
- Frontend: React + Vite → Vercel
- Backend: Python + FastAPI → Railway
- Agent: LangGraph + LangChain + Groq (llama-3.1-8b-instant)
- Database: Supabase (meal_plans, expenses, shopping_items, prices, profiles tables)
- Email: Resend API
- Model: llama-3.1-8b-instant (1M tokens/day free on Groq)

## Key Architecture Decision
Meal planning logic is in Python (plan_week() function), NOT in the LLM.
LLM only formats output and handles conversation.

## People
- Supriya: 36F, 65kg, 159cm, active, fat loss → 1,700 kcal/day | 130g protein
- Vivek: 39M, 83kg, 186cm, active, fat loss → 2,200 kcal/day | 166g protein

## Environment Variables
### Railway (backend)
- SUPABASE_URL
- SUPABASE_SERVICE_KEY (sb_secret_...)
- GROQ_API_KEY
- RESEND_API_KEY
- SUPRIYA_EMAIL
- VIVEK_EMAIL

### Vercel (frontend)
- VITE_SUPABASE_URL
- VITE_SUPABASE_ANON_KEY (sb_publishable_...)
- VITE_API_URL = https://new-agent-sous-chef-production.up.railway.app

## Project Structure
```
new-agent-sous-chef/
  backend/
    main.py              ← FastAPI app, CORS configured
    Dockerfile           ← python:3.11-slim, port 8080
    railway.json         ← DOCKERFILE builder
    requirements.txt
    agent/
      graph.py           ← ALL agent logic here
    api/
      expenses.py        ← httpx REST calls to Supabase
      meals.py           ← httpx REST calls to Supabase
  frontend/
    src/
      App.jsx            ← Chat UI, voice input, shopping, expenses
      hooks/useVoice.js  ← Web Speech API
      main.jsx
    public/manifest.json ← PWA manifest
```

## What's Working
- Chat responds correctly
- Meal planning with no repeats (Python logic)
- Correct protein rotation Mon-Sun
- Correct starch rules (chicken→paratha, fish→rice, dal→rice)
- Shopping list with prices
- Expense tracking
- Budget projections

## Next Steps
1. Multi-user support (Google Auth + household_id)
2. Fitness app integration (Google Fit / Strava for calorie adjustment)
3. PWA icons (icon-192.png, icon-512.png missing)
4. Sunday special display fix
5. App Store / Play Store via Expo

## Key Files to Never Lose
- backend/agent/graph.py ← the brain, all rules here
- backend/api/expenses.py ← expense tracking
- backend/api/meals.py ← meal history
- frontend/src/App.jsx ← full UI
