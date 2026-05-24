from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
import os
import json
import httpx
from datetime import datetime, timedelta

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1,
    max_tokens=1500,
)

def sb_headers():
    key = os.getenv("SUPABASE_SERVICE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def sb_url(path):
    return f"{os.getenv('SUPABASE_URL')}/rest/v1/{path}"

SYSTEM = """You are Sous Chef, a warm friendly meal planning agent for Supriya and Vivek in Bengaluru.

DAILY TARGETS:
Supriya: 1,700 kcal | 130g protein
Vivek: 2,200 kcal | 166g protein

FIXED BREAKFAST every day:
8 egg whites bhurji + Protein Smoothie (2.5 scoops ON Whey + yogurt + banana + blueberries + dragon fruit)
Supriya: ~45g protein | 420 kcal
Vivek: ~45g protein | 460 kcal

WEEKLY ROTATION:
Mon = Chicken | Tue = Fish dry fry | Wed = Chicken (different from Mon)
Thu = Veg day | Fri = Fish dry fry (different sabzi from Tue) | Sat = Chicken (different from Mon+Wed)
Sun = Fish/Chicken/Paneer (flexible)

EVERY MEAL = gravy + dry sabzi + protein + rice(lunch)/roti(dinner)
Fish/dal days = rice both meals

GRAVIES: dal tadka | palak dal | rajma | black chana | matar paneer | kadhi | santula | aloo gobi gravy | rajma soyabean curry | chole | sambar | lauki dal | moong dal | arhar dal
DRY SABZIS: torai | bhindi fry | beans carrot | cauliflower matar aloo | cabbage | baingan bharta | beetroot | lauki | parwal | mix veg | aloo shimla mirch | methi

RULES:
- Kadhi ONLY with fish (never chicken)
- Rajma/black chana day = no meat
- Torai = always dry sabzi never gravy
- NEVER repeat same gravy+sabzi in same week
- Each chicken day = different gravy AND different sabzi

THURSDAY OPTIONS: rajma soyabean | chole | matar paneer | paneer bhurji + any dal

APPROVED COMBOS (from their actual cooking):
- Palak dal + Mackerel dry fry + Mix veg sabzi
- Chicken curry + Torai sabzi
- Dal tadka + Beetroot sabzi + Chicken sukka
- Kadhi + Beans carrot sabzi + Mackerel dry fry
- Matar paneer + Cauliflower matar sabzi
- Sambar + Mackerel dry fry + Parwal sabzi
- Black chana + Cabbage sabzi + Chicken sukka
- Rajma soyabean + Aloo shimla mirch

PORTIONS:
Supriya: chicken 150g | fish 150g | paneer 80g | rice 60g dry | 2 rotis | dal 30g | veg 100g
Vivek: chicken 200g | fish 200g | paneer 120g | rice 100g dry | 3 rotis | dal 40g | veg 120g

MACROS (daily totals):
Chicken day — Supriya: 1,580 kcal | 107g protein | 135g carbs | 38g fat
Chicken day — Vivek: 1,980 kcal | 128g protein | 170g carbs | 52g fat
Fish day — Supriya: 1,540 kcal | 103g protein | 130g carbs | 36g fat
Fish day — Vivek: 1,920 kcal | 123g protein | 162g carbs | 48g fat
Veg day — Supriya: 1,460 kcal | 91g protein | 145g carbs | 34g fat
Veg day — Vivek: 1,820 kcal | 109g protein | 182g carbs | 46g fat

SHOPPING PRICES:
Licious: Eggs ₹132/dozen (6/week=₹792) | Chicken breast 450g ₹295 × 3=₹885 | Chicken curry cut 500g ₹260 × 3=₹780 | Mackerel 500g ₹350 × 3=₹1,050
Instamart: Paneer 200g ₹136 × 2=₹272 | Milk 500ml ₹53 × 14=₹742 | Greek yogurt ₹249 × 2=₹498 | Dal ₹130 | Vegetables ~₹350 | Fruits ~₹500
Mango: Rice 5kg ₹320 | Atta 1kg ₹60
Weekly total: ~₹6,400

NO REPETITION — ALWAYS call get_meal_history first, then:
- List gravies used last 2 weeks → pick different ones
- List sabzis used last 2 weeks → pick different ones
- Self check: all 7 gravies unique? all 7 sabzis unique? fix if not

RESPONSE STYLE:
Be warm and conversational. Keep it SHORT by default.

DEFAULT meal plan format:

Here's your week! 🍽️

📅 Monday — Chicken
🍳 Breakfast: 8 egg whites + smoothie
🍛 Lunch/Dinner: Dal tadka + Torai sabzi + Chicken sukka + Rice/Roti

📅 Tuesday — Fish
🍳 Breakfast: 8 egg whites + smoothie
🍛 Lunch/Dinner: Kadhi + Bhindi fry + Mackerel dry fry + Rice

...for all 7 days...

That's your week sorted! 💪 Want macros, quantities, or the shopping list?

ONLY show macros if asked. ONLY show grams if asked. ONLY show table if asked."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_meal_history",
            "description": "Get meals from last 14 days to avoid repeating combos",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_expenses",
            "description": "Get this month grocery expenses and total",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_meal_plan",
            "description": "Save confirmed meal plan to database",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD format"},
                    "lunch": {"type": "string", "description": "Full lunch description"},
                    "dinner": {"type": "string", "description": "Full dinner description"},
                    "day_type": {"type": "string", "description": "chicken, fish, paneer, or veg"}
                },
                "required": ["date", "lunch", "dinner", "day_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_expense",
            "description": "Log a grocery expense",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "enum": ["licious", "instamart", "blinkit", "mango"]},
                    "amount": {"type": "number"},
                    "note": {"type": "string"}
                },
                "required": ["platform", "amount"]
            }
        }
    }
]

llm_with_tools = llm.bind_tools(TOOLS)

async def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "get_meal_history":
            since = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    sb_url(f"meal_plans?planned_date=gte.{since}&order=planned_date.desc&select=planned_date,lunch,dinner"),
                    headers=sb_headers()
                )
            data = r.json() if isinstance(r.json(), list) else []
            if not data:
                return "No meal history yet — first week!"
            return json.dumps([{"date": d["planned_date"], "meal": d["lunch"]} for d in data[:7]])

        elif name == "get_expenses":
            now = datetime.now()
            month_start = f"{now.year}-{now.month:02d}-01"
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    sb_url(f"expenses?expense_date=gte.{month_start}"),
                    headers=sb_headers()
                )
            data = r.json() if isinstance(r.json(), list) else []
            total = sum(e.get("amount", 0) for e in data)
            by_platform = {}
            for e in data:
                p = e.get("platform", "other")
                by_platform[p] = by_platform.get(p, 0) + e.get("amount", 0)
            days_passed = datetime.now().day
            projected = round((total / days_passed) * 31) if days_passed > 0 else 0
            return json.dumps({
                "total_spent": total,
                "by_platform": by_platform,
                "monthly_target": 38000,
                "remaining": 38000 - total,
                "projected_month_end": projected,
                "days_passed": days_passed
            })

        elif name == "save_meal_plan":
            day_type = args.get("day_type", "chicken").lower()
            is_veg = day_type in ["paneer", "veg"]
            protein_map = {"chicken": 162, "fish": 136, "paneer": 112, "veg": 112}
            protein = protein_map.get(day_type, 130)
            async with httpx.AsyncClient() as client:
                await client.post(
                    sb_url("meal_plans"),
                    headers={**sb_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
                    json={
                        "planned_date": args.get("date"),
                        "day_of_week": datetime.strptime(args["date"], "%Y-%m-%d").strftime("%a") if args.get("date") else "",
                        "is_veg": is_veg,
                        "lunch": args.get("lunch", ""),
                        "dinner": args.get("dinner", args.get("lunch", "")),
                        "total_protein": protein,
                        "confirmed": True,
                    }
                )
            return json.dumps({"success": True, "saved": args.get("date")})

        elif name == "log_expense":
            amount = args.get("amount", 0)
            if isinstance(amount, str):
                try: amount = float(amount)
                except: amount = 0
            async with httpx.AsyncClient() as client:
                await client.post(
                    sb_url("expenses"),
                    headers=sb_headers(),
                    json={
                        "platform": args.get("platform", "instamart"),
                        "amount": amount,
                        "note": args.get("note", ""),
                        "expense_date": datetime.now().strftime("%Y-%m-%d"),
                    }
                )
            return json.dumps({"success": True})

    except Exception as e:
        return json.dumps({"error": str(e)})

async def run_agent(messages: list) -> dict:
    now = datetime.now()
    today = now.strftime("%A, %d %B %Y")
    day_num = now.weekday()
    protein_today = {0: "CHICKEN", 1: "FISH", 2: "CHICKEN", 3: "VEG DAY",
                     4: "FISH", 5: "CHICKEN", 6: "FISH/CHICKEN/PANEER"}[day_num]

    chat_messages = [SystemMessage(content=SYSTEM)]
    chat_messages.append(HumanMessage(content=
        f"[Today: {today}. Today's protein: {protein_today}. Day {now.day}/31 of month.]"
    ))

    for m in messages[-4:]:
        if m.get("role") == "user":
            chat_messages.append(HumanMessage(content=m["content"]))
        elif m.get("role") == "assistant":
            chat_messages.append(AIMessage(content=m.get("content", "")))

    for _ in range(4):
        response = llm_with_tools.invoke(chat_messages)
        chat_messages.append(response)
        if not response.tool_calls:
            break
        for tc in response.tool_calls:
            result = await execute_tool(tc["name"], tc.get("args", {}))
            chat_messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    final = ""
    for msg in reversed(chat_messages):
        if isinstance(msg, AIMessage) and msg.content:
            final = msg.content
            break

    return {"response": final.strip(), "shopping_list": None, "meal_plan": None}
