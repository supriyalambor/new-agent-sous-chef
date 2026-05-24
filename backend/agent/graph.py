from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
import os
import json
import httpx
from datetime import datetime, timedelta

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2,
    max_tokens=1000,
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

TARGETS: Supriya 1,700 kcal/130g protein | Vivek 2,200 kcal/166g protein

BREAKFAST (fixed, every day):
8 egg whites bhurji + smoothie (ON Whey 2.5 scoops + yogurt + banana + blueberries + dragon fruit)
Exception: Sunday can have cauliflower/aloo/methi paratha + egg bhurji instead

WEEKLY PROTEIN ROTATION:
Mon=Chicken | Tue=Fish | Wed=Chicken | Thu=Veg | Fri=Fish | Sat=Chicken | Sun=Flexible

MEAL STRUCTURE: every meal = gravy + dry sabzi + protein + starch
Lunch=Rice | Dinner=Roti (fish/dal gravy days=Rice both meals)

GRAVIES (rotate, never repeat in same week):
Dal tadka | Palak dal | Rajma | Black chana | Matar paneer | Kadhi | Santula
Aloo gobi gravy | Rajma soyabean | Chole | Sambar | Lauki dal | Moong dal | Arhar dal
Kadhi only with fish. Rajma/chana=no meat same day.

DRY SABZIS (rotate, never repeat in same week):
Torai | Bhindi | Beans carrot | Cauliflower matar aloo | Cabbage | Baingan bharta
Beetroot | Lauki | Parwal | Mix veg (cauliflower+broccoli+matar+carrot+beans) | Aloo shimla mirch | Methi | Aloo jeera | Sem sabzi | Kaddu sabzi | Tinda sabzi | Gawar sabzi

PROTEINS:
Chicken: sukka OR curry OR handi OR masala
Fish: mackerel dry fry OR sardine dry fry OR mackerel rava fry OR pomfret fry
Paneer: bhurji OR matar paneer (in gravy) OR palak paneer
Veg proteins: soyabean curry | rajma | chole | chana dal

SPECIAL VARIATIONS (use occasionally, not every week):
- Khichdi can replace rice+dal combo (any day, not always Saturday)
- Paratha can replace roti at dinner occasionally
- Pulao (vegetable/matar) can replace plain rice once a week
- Dal makhani as special gravy once a fortnight
- Egg curry on non-Thursday days as variation protein

THURSDAY VEG OPTIONS:
Rajma soyabean curry | Chole | Matar paneer | Paneer bhurji + any dal
Chana masala | Dal makhani | Palak paneer | Paneer handi

PORTIONS:
Supriya: chicken 150g | fish 150g | paneer 80g | rice 60g dry | 2 rotis | dal 30g | veg 100g
Vivek: chicken 200g | fish 200g | paneer 120g | rice 100g dry | 3 rotis | dal 40g | veg 120g

MACROS (daily totals, use when asked):
Chicken day: Supriya ~1,580 kcal/107g protein | Vivek ~1,980 kcal/128g protein
Fish day: Supriya ~1,540 kcal/103g protein | Vivek ~1,920 kcal/123g protein
Veg day: Supriya ~1,460 kcal/91g protein | Vivek ~1,820 kcal/109g protein

SHOPPING PRICES (use when asked):
Licious: Eggs ₹132/doz×6=₹792 | Chicken breast 450g ₹295×3=₹885 | Curry cut 500g ₹260×3=₹780 | Mackerel 500g ₹350×3=₹1,050
Instamart: Paneer 200g ₹136×2=₹272 | Milk ₹53×14=₹742 | Yogurt ₹249×2=₹498 | Veg ~₹350 | Fruits ~₹500 | Dal ₹130
Mango: Rice 5kg ₹320 | Atta 1kg ₹60 | Weekly total ~₹6,400

NO REPEAT RULES:
1. Call get_meal_history first
2. Pick gravies not used in last 2 weeks
3. Pick sabzis not used in last 2 weeks
4. All 7 days must have unique gravy AND unique sabzi
5. Chicken days (Mon/Wed/Sat) must all differ from each other

RESPONSE FORMAT:
Default = short clean plan, no macros, no grams:

Here's your week! 🍽️

📅 Monday — Chicken
🍳 BF: Egg whites + smoothie
🍛 Lunch/Dinner: [gravy] + [sabzi] + [protein] + Rice/Roti

Only show macros/quantities/shopping if user asks.
Be warm and conversational. End with a helpful suggestion."""

TOOLS = [
    {"type": "function", "function": {
        "name": "get_meal_history",
        "description": "Get meals eaten in last 14 days to avoid repetition",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "get_expenses",
        "description": "Get this month grocery expenses",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "save_meal_plan",
        "description": "Save confirmed meal plan",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "lunch": {"type": "string"},
                "dinner": {"type": "string"},
                "day_type": {"type": "string", "description": "chicken/fish/paneer/veg"}
            },
            "required": ["date", "lunch", "dinner", "day_type"]
        }
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
                return "No history yet — first week!"
            return json.dumps([{"date": d["planned_date"], "meal": d["lunch"]} for d in data[:10]])

        elif name == "get_expenses":
            now = datetime.now()
            month_start = f"{now.year}-{now.month:02d}-01"
            async with httpx.AsyncClient() as client:
                r = await client.get(sb_url(f"expenses?expense_date=gte.{month_start}"), headers=sb_headers())
            data = r.json() if isinstance(r.json(), list) else []
            total = sum(e.get("amount", 0) for e in data)
            by_platform = {}
            for e in data:
                by_platform[e.get("platform", "other")] = by_platform.get(e.get("platform", "other"), 0) + e.get("amount", 0)
            days = datetime.now().day
            return json.dumps({"total": total, "by_platform": by_platform, "target": 38000,
                               "remaining": 38000 - total, "projected": round((total/days)*31) if days else 0})

        elif name == "save_meal_plan":
            day_type = args.get("day_type", "chicken").lower()
            protein_map = {"chicken": 162, "fish": 136, "paneer": 112, "veg": 112}
            async with httpx.AsyncClient() as client:
                await client.post(
                    sb_url("meal_plans"),
                    headers={**sb_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
                    json={
                        "planned_date": args.get("date"),
                        "day_of_week": datetime.strptime(args["date"], "%Y-%m-%d").strftime("%a") if args.get("date") else "",
                        "is_veg": day_type in ["paneer", "veg"],
                        "lunch": args.get("lunch", ""),
                        "dinner": args.get("dinner", args.get("lunch", "")),
                        "total_protein": protein_map.get(day_type, 130),
                        "confirmed": True,
                    }
                )
            return json.dumps({"success": True})

        elif name == "log_expense":
            amount = args.get("amount", 0)
            if isinstance(amount, str):
                try: amount = float(amount)
                except: amount = 0
            async with httpx.AsyncClient() as client:
                await client.post(
                    sb_url("expenses"),
                    headers=sb_headers(),
                    json={"platform": args.get("platform", "instamart"), "amount": amount,
                          "note": args.get("note", ""), "expense_date": datetime.now().strftime("%Y-%m-%d")}
                )
            return json.dumps({"success": True})

    except Exception as e:
        return json.dumps({"error": str(e)})

async def run_agent(messages: list) -> dict:
    now = datetime.now()
    day_num = now.weekday()
    protein_today = {0:"CHICKEN",1:"FISH",2:"CHICKEN",3:"VEG DAY",4:"FISH",5:"CHICKEN",6:"FLEXIBLE"}[day_num]

    chat_messages = [SystemMessage(content=SYSTEM)]
    chat_messages.append(HumanMessage(content=
        f"[Today: {now.strftime('%A %d %B %Y')} | Protein today: {protein_today} | Day {now.day}/31]"
    ))

    for m in messages[-4:]:
        if m.get("role") == "user":
            chat_messages.append(HumanMessage(content=m["content"]))
        elif m.get("role") == "assistant":
            chat_messages.append(AIMessage(content=m.get("content", "")))

    for _ in range(3):
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