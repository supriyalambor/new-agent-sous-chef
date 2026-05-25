# Sous Chef Agent — Project Summary
*Last updated: May 25, 2026*

## Live URLs
- Frontend: https://new-agent-sous-chef.vercel.app
- Backend: https://new-agent-sous-chef-production.up.railway.app
- Old V1: https://sous-chef-rouge.vercel.app (ignore)

## GitHub
- Repo: https://github.com/supriyalambor/new-agent-sous-chef

## Tech Stack
- Frontend: React + Vite → Vercel
- Backend: Python + FastAPI → Railway (port 8080, Dockerfile)
- Agent: LangChain + ChatGroq (llama-3.1-8b-instant, 1M tokens/day free)
- Database: Supabase (httpx REST — NOT supabase Python client)
- Model: llama-3.1-8b-instant on Groq

## Key Architecture
Meal planning logic is in Python (plan_week() function), NOT in the LLM.
LLM only formats output and handles conversation.

## People
- Supriya: 36F, 65kg, 159cm, active, fat loss → 1,700 kcal/day | 130g protein
- Vivek: 39M, 83kg, 186cm, active, fat loss → 2,200 kcal/day | 166g protein

## Environment Variables
### Railway (backend)
- SUPABASE_URL
- SUPABASE_SERVICE_KEY (sb_secret_...)
- GROQ_API_KEY (get from console.groq.com)
- RESEND_API_KEY
- SUPRIYA_EMAIL = supriyalambor@gmail.com
- VIVEK_EMAIL = vivekbiet13@gmail.com

### Vercel (frontend)
- VITE_SUPABASE_URL
- VITE_SUPABASE_ANON_KEY (sb_publishable_...)
- VITE_API_URL = https://new-agent-sous-chef-production.up.railway.app

## Project Structure
```
new-agent-sous-chef/
  backend/
    main.py              ← FastAPI, CORS configured for Vercel URL
    Dockerfile           ← python:3.11-slim, port 8080
    railway.json         ← DOCKERFILE builder
    requirements.txt     ← includes langchain-groq, NO supabase package
    agent/
      graph.py           ← ALL agent logic (THE BRAIN)
    api/
      expenses.py
      meals.py
    test_sous_chef.py    ← run before every deploy: py backend/test_sous_chef.py
  frontend/
    src/
      App.jsx            ← Chat UI, table renderer, voice input, shop, expenses
      hooks/useVoice.js
      main.jsx
    public/manifest.json
```

## Before Every Deploy
```bash
py backend/test_sous_chef.py
# Must show: 🚀 ALL TESTS PASSED
git add backend/agent/graph.py
git commit -m "your message"
git push origin main
```

## What's Working
- ✅ Chat responding
- ✅ Meal planning with no repeats (Python logic)
- ✅ Correct protein rotation Mon-Sun
- ✅ Correct starch rules (chicken→paratha, fish→rice, dal→rice)
- ✅ Saturday 3 options (khichdi/stuffed paratha/regular)
- ✅ Shopping list with real Mango prices
- ✅ Expense tracking + budget projection
- ✅ Pantry inventory (get + update)
- ✅ Table renderer in chat UI

## Next Steps (in order)
1. Test for a full week — confirm all rules working daily
2. Fix Shop tab — shopping list as clickable items
3. Add Google Auth for multi-household support
4. Add friend's household
5. PWA icons (icon-192.png, icon-512.png missing)

## Common Issues & Fixes
- CORS error → Railway port reset → Settings → Networking → set port 8080
- 500 error → check Railway deploy logs for CHAT ERROR line
- Token limit → llama-3.3-70b has 100k/day limit, llama-3.1-8b has 1M/day
- Double response → LLM overriding Python plan (fixed in current code)
- "branch up to date" → file wasn't actually saved in VS Code

## All Meal Rules
### Targets
- Supriya: 1,700 kcal | 130g protein
- Vivek: 2,200 kcal | 166g protein

### Breakfast (fixed every day)
- 8 egg whites bhurji + ON Whey smoothie (2.5 scoops shared + yogurt + banana + blueberries + dragon fruit)
- Sunday exception: paratha + egg bhurji

### Weekly Rotation
- Mon=Chicken | Tue=Fish | Wed=Chicken | Thu=Veg | Fri=Fish | Sat=Chicken | Sun=Flexible

### Meal Structure
- Every meal = gravy + dry sabzi + protein
- Lunch and dinner = same dish cooked once → show as "Lunch & Dinner"

### Starch Rules (by protein type)
- Chicken → 3 plain parathas (Supriya) / 4 rotis (Vivek)
- Fish → Rice always (both meals)
- Veg + dal/kadhi/rajma/santula/sambar → Rice
- Veg + chole/matar paneer/palak paneer/aloo gobi → Paratha
- Saturday chicken → Stuffed paratha (aloo/paneer cauliflower/methi/palak)
- NO roti+dal combo ever

### Saturday Options
- 30%: Khichdi + Chokha + Fish fry (no sabzi)
- 35%: Chicken curry + stuffed paratha + sabzi
- 35%: Regular chicken + stuffed paratha + sabzi

### Strict Rules
- Kadhi ONLY with fish — never chicken
- Rajma/black chana = no meat same day
- Torai = always dry sabzi never gravy
- NEVER repeat same gravy in same week
- NEVER repeat same sabzi in same week

### Portions
- Supriya: chicken 150g | fish 150g | paneer 80g | rice 60g dry | 3 parathas | dal 30g | veg 100g
- Vivek: chicken 200g | fish 200g | paneer 120g | rice 100g dry | 4 rotis | dal 40g | veg 120g

### Approved Gravies
- Fish: kadhi | palak dal | sambar | moong dal | lauki dal | santula
- Chicken: dal tadka | palak dal | aloo gobi gravy | moong dal | lauki dal | chole
- Veg: matar paneer | rajma soyabean | chole | palak paneer | chana masala | paneer handi | kadhi | santula | moong dal | rajma | black chana

### Approved Sabzis (17)
torai | bhindi fry | beans carrot | cauliflower matar aloo | cabbage | baingan bharta | beetroot | lauki | parwal | mix veg | aloo shimla mirch | methi | aloo jeera | sem sabzi | tinda | gawar | aloo gobi dry

### Approved Proteins
- Chicken: sukka | handi | masala
- Fish: mackerel dry fry | sardine dry fry | mackerel rava fry
- Veg: soyabean curry | chana | paneer (not when paneer gravy)

### REMOVED (never use)
- dal makhani | arhar dal | kaddu

### Thursday Special
- Veg day only
- If paneer gravy → any dry sabzi
- If no paneer gravy → add paneer bhurji as side

### Shopping Prices (real from Mango receipt)
- Licious: Eggs ₹139/doz×6=₹834 | Chicken breast ₹295×3=₹885 | Curry cut ₹260×3=₹780 | Mackerel ₹350×3=₹1,050
- Instamart: Paneer ₹136×2=₹272 | Milk ₹53×14=₹742 | Yogurt ₹249×2=₹498
- Mango: Beetroot/Carrot ₹99/kg | Lauki ₹59/kg | Rajma ₹184/kg | Rice 5kg ₹320
- Weekly total: ~₹6,500 | Monthly budget: ₹38,000

### Response Rules
- Indian home cooking ONLY — no Western food
- Macros shown ONLY when asked
- Quantities shown ONLY when asked
- Log expense ONLY when user explicitly says they spent money
- Shopping list always shows weekly total
- Buy vegetables from Mango — cheaper than Instamart
