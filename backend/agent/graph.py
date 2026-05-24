from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
import os
import json
import httpx
import random
from datetime import datetime, timedelta

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,
    max_tokens=800,
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

# ── Meal planning logic in Python (not LLM) ───────────────────────

GRAVIES = {
    "fish":    ["kadhi", "palak dal", "sambar", "moong dal", "arhar dal", "lauki dal", "santula"],
    "chicken": ["dal tadka", "palak dal", "rajma", "black chana", "aloo gobi gravy", 
                "arhar dal", "moong dal", "lauki dal", "rajma soyabean", "chole"],
    "veg":     ["matar paneer", "rajma soyabean", "chole", "dal makhani", "palak paneer",
                "chana masala", "kadhi", "santula", "arhar dal", "moong dal"],
}

SABZIS = [
    "torai", "bhindi fry", "beans carrot", "cauliflower matar aloo", "cabbage",
    "baingan bharta", "beetroot", "lauki", "parwal", "mix veg",
    "aloo shimla mirch", "methi", "aloo jeera", "sem sabzi", "kaddu",
    "tinda", "gawar", "aloo gobi dry"
]

PROTEINS = {
    "chicken": ["chicken sukka", "chicken curry", "chicken handi", "chicken masala"],
    "fish":    ["mackerel dry fry", "sardine dry fry", "mackerel rava fry"],
    "veg":     ["paneer bhurji", "matar paneer", "soyabean curry", "chana"],
}

# Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
DAY_TYPE = {0:"chicken", 1:"fish", 2:"chicken", 3:"veg", 4:"fish", 5:"chicken", 6:"flex"}

def plan_week(history: list) -> list:
    """Generate a week plan with no repeats, enforced in Python."""
    
    # Extract used gravies and sabzis from history
    used_gravies = set()
    used_sabzis = set()
    for h in history:
        meal = h.get("meal", "").lower()
        for g in GRAVIES["chicken"] + GRAVIES["fish"] + GRAVIES["veg"]:
            if g in meal:
                used_gravies.add(g)
        for s in SABZIS:
            if s in meal:
                used_sabzis.add(s)

    # Get current Monday
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        monday = today
    else:
        monday = today + timedelta(days=days_until_monday)
    # If today is Monday use today
    if today.weekday() == 0:
        monday = today

    week_plan = []
    used_this_week_gravies = set()
    used_this_week_sabzis = set()

    for i in range(7):
        date = monday + timedelta(days=i)
        day_type = DAY_TYPE[i]
        if day_type == "flex":
            day_type = random.choice(["fish", "chicken", "veg"])

        # Pick gravy not used this week or recently
        gravy_pool = [g for g in GRAVIES[day_type] 
                      if g not in used_this_week_gravies and g not in used_gravies]
        if not gravy_pool:
            gravy_pool = [g for g in GRAVIES[day_type] if g not in used_this_week_gravies]
        if not gravy_pool:
            gravy_pool = GRAVIES[day_type]
        gravy = random.choice(gravy_pool)
        used_this_week_gravies.add(gravy)

        # Pick sabzi not used this week or recently
        sabzi_pool = [s for s in SABZIS 
                      if s not in used_this_week_sabzis and s not in used_sabzis]
        if not sabzi_pool:
            sabzi_pool = [s for s in SABZIS if s not in used_this_week_sabzis]
        if not sabzi_pool:
            sabzi_pool = SABZIS
        sabzi = random.choice(sabzi_pool)
        used_this_week_sabzis.add(sabzi)

        # Pick protein
        protein = random.choice(PROTEINS[day_type])

        # Starch rule
        # Fish days = Rice both meals
        # Chicken weekdays (Mon/Wed) = 3 plain parathas (Supriya) / 4 rotis (Vivek)
        # Chicken Saturday = Stuffed paratha for both
        # Veg days = Rice lunch, Roti dinner
        if day_type == "fish":
            lunch_starch = "Rice"
            dinner_starch = "Rice"
        elif day_type == "chicken" and i == 5:  # Saturday
            stuffing = random.choice(["Aloo", "Paneer Cauliflower", "Methi", "Palak"])
            lunch_starch = f"{stuffing} Stuffed Paratha"
            dinner_starch = f"{stuffing} Stuffed Paratha"
        elif day_type == "chicken":
            lunch_starch = "3 Plain Parathas (Supriya) / 4 Rotis (Vivek)"
            dinner_starch = "3 Plain Parathas (Supriya) / 4 Rotis (Vivek)"
        else:  # veg
            lunch_starch = "Rice"
            dinner_starch = "Roti"

        lunch = f"{gravy.title()} + {sabzi.title()} + {protein.title()} + {lunch_starch}"
        dinner = f"{gravy.title()} + {sabzi.title()} + {protein.title()} + {dinner_starch}"

        week_plan.append({
            "date": date.strftime("%Y-%m-%d"),
            "day": date.strftime("%A"),
            "day_type": day_type,
            "gravy": gravy,
            "sabzi": sabzi,
            "protein": protein,
            "lunch": lunch,
            "dinner": dinner,
        })

    return week_plan

# ── System prompt (minimal — logic is in Python) ──────────────────
SYSTEM = """You are Sous Chef, a warm friendly meal planning agent for Supriya and Vivek in Bengaluru.

TARGETS: Supriya 1,700 kcal/130g protein | Vivek 2,200 kcal/166g protein

BREAKFAST every day: 8 egg whites bhurji + smoothie (ON Whey + yogurt + banana + blueberries + dragon fruit)
Sunday exception: paratha + egg bhurji

PORTIONS:
Supriya: chicken 150g | fish 150g | paneer 80g | rice 60g dry | 2 rotis | dal 30g | veg 100g
Vivek: chicken 200g | fish 200g | paneer 120g | rice 100g dry | 3 rotis | dal 40g | veg 120g

MACROS (daily, use when asked):
Chicken day: Supriya ~1,580 kcal/107g protein | Vivek ~1,980 kcal/128g protein
Fish day: Supriya ~1,540 kcal/103g protein | Vivek ~1,920 kcal/123g protein
Veg day: Supriya ~1,460 kcal/91g protein | Vivek ~1,820 kcal/109g protein

SHOPPING PRICES (use when asked):
Licious: Eggs ₹792/week | Chicken ₹1,665/week | Mackerel ₹1,050/week
Instamart: Paneer ₹272 | Milk ₹742 | Yogurt ₹498 | Veg+Dal+Fruits ~₹980
Mango: Rice+Atta ₹380 | Weekly total ~₹6,400

When you receive a MEAL_PLAN in the context, present it nicely in this format:

Here's your week! 🍽️

📅 [Day] — [Chicken/Fish/Veg]
🍳 BF: Egg whites + smoothie
🍛 Lunch: [meal]
🌙 Dinner: [meal]

After the plan, ask: "Want macros, quantities, or the shopping list?"

For budget questions use get_expenses tool.
Keep responses warm and SHORT. Only show macros/quantities if asked."""

TOOLS = [
    {"type": "function", "function": {
        "name": "get_expenses",
        "description": "Get this month grocery expenses",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
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
    }}
]

llm_with_tools = llm.bind_tools(TOOLS)

async def get_history() -> list:
    since = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    async with httpx.AsyncClient() as client:
        r = await client.get(
            sb_url(f"meal_plans?planned_date=gte.{since}&order=planned_date.desc&select=planned_date,lunch"),
            headers=sb_headers()
        )
    data = r.json() if isinstance(r.json(), list) else []
    return [{"date": d["planned_date"], "meal": d["lunch"]} for d in data]

async def save_plan(week_plan: list):
    for day in week_plan:
        async with httpx.AsyncClient() as client:
            await client.post(
                sb_url("meal_plans"),
                headers={**sb_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
                json={
                    "planned_date": day["date"],
                    "day_of_week": day["day"][:3],
                    "is_veg": day["day_type"] == "veg",
                    "lunch": day["lunch"],
                    "dinner": day["dinner"],
                    "total_protein": {"chicken":162,"fish":136,"veg":112}.get(day["day_type"],130),
                    "confirmed": True,
                }
            )

async def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "get_expenses":
            now = datetime.now()
            month_start = f"{now.year}-{now.month:02d}-01"
            async with httpx.AsyncClient() as client:
                r = await client.get(sb_url(f"expenses?expense_date=gte.{month_start}"), headers=sb_headers())
            data = r.json() if isinstance(r.json(), list) else []
            total = sum(e.get("amount", 0) for e in data)
            by_platform = {}
            for e in data:
                by_platform[e.get("platform","other")] = by_platform.get(e.get("platform","other"),0) + e.get("amount",0)
            days = datetime.now().day
            return json.dumps({"total": total, "by_platform": by_platform, "target": 38000,
                               "remaining": 38000-total, "projected": round((total/days)*31) if days else 0})
        elif name == "log_expense":
            amount = args.get("amount", 0)
            if isinstance(amount, str):
                try: amount = float(amount)
                except: amount = 0
            async with httpx.AsyncClient() as client:
                await client.post(sb_url("expenses"), headers=sb_headers(),
                    json={"platform": args.get("platform","instamart"), "amount": amount,
                          "note": args.get("note",""), "expense_date": datetime.now().strftime("%Y-%m-%d")})
            return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})

async def run_agent(messages: list) -> dict:
    now = datetime.now()
    user_message = messages[-1].get("content", "").lower() if messages else ""

    # Check if user wants a week plan
    wants_plan = any(w in user_message for w in ["plan", "week", "menu", "meals"])

    meal_plan_context = ""
    week_plan = None

    if wants_plan:
        history = await get_history()
        week_plan = plan_week(history)
        await save_plan(week_plan)
        plan_text = "\n".join([
            f"{d['day']} ({d['day_type']}): Lunch={d['lunch']} | Dinner={d['dinner']}"
            for d in week_plan
        ])
        meal_plan_context = f"\n\nMEAL_PLAN:\n{plan_text}"

    chat_messages = [SystemMessage(content=SYSTEM)]
    chat_messages.append(HumanMessage(content=
        f"[Today: {now.strftime('%A %d %B %Y')} | Day {now.day}/31]{meal_plan_context}"
    ))

    for m in messages[-4:]:
        if m.get("role") == "user":
            chat_messages.append(HumanMessage(content=m["content"]))
        elif m.get("role") == "assistant":
            chat_messages.append(AIMessage(content=m.get("content", "")))

    for _ in range(2):
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