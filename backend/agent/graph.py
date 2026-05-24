from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
import os
import json
import httpx
from datetime import datetime, timedelta

# ── Groq LLM ─────────────────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1,
    max_tokens=1500,
)

# ── Supabase REST ─────────────────────────────────────────────────
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

# ── System prompt ─────────────────────────────────────────────────
SYSTEM = """You are Sous Chef, meal planning agent for Supriya (36F,65kg) and Vivek (39M,83kg) in Bengaluru.

DAILY TARGETS:
Supriya: 1,700 kcal | 130g protein
Vivek: 2,200 kcal | 166g protein

FIXED BREAKFAST (every single day, no exceptions):
8 egg whites bhurji (no yolk, no bread) + protein smoothie
Smoothie: 2.5 scoops ON Whey protein (shared) + 2 tbsp yogurt + 1 small banana + handful blueberries
Supriya: ~45g protein | 420 kcal
Vivek: ~45g protein | 460 kcal

WEEKLY PROTEIN ROTATION — STRICT:
Monday = CHICKEN
Tuesday = FISH DRY FRY (mackerel/sardines — NO curry, NO biryani, DRY FRY ONLY)
Wednesday = CHICKEN (must be different gravy+sabzi from Monday)
Thursday = STRICT VEG DAY (zero meat/fish/eggs in main meals)
Thursday options:
- Rajma + Soyabean curry + dry sabzi (no paneer needed)
- Chole (chickpea curry) + dry sabzi
- Matar paneer (gravy) + dry sabzi (paneer is protein here)
- Any dal/rajma/chana gravy + Paneer bhurji (dry) as protein + dry sabzi
- If paneer is in gravy (matar paneer) → pick any dry sabzi
- If no paneer in gravy → paneer bhurji as the protein side
Friday = FISH DRY FRY (different dry sabzi from Tuesday)
Saturday = CHICKEN (different gravy+sabzi from Mon and Wed)
Sunday = FISH DRY FRY or PANEER + paratha breakfast

EVERY MEAL MUST HAVE EXACTLY 4 COMPONENTS — NO EXCEPTIONS:
1. GRAVY — pick ONE from: dal tadka | palak dal | rajma | black chana | matar paneer | kadhi | santula | aloo gobi gravy | rajma soyabean curry | chole | sambar | lauki dal | moong dal | arhar dal
2. DRY SABZI — pick ONE from: torai sabzi | bhindi fry | beans carrot sabzi | cauliflower matar aloo carrot | cabbage sabzi | baingan bharta | beetroot sabzi | lauki sabzi | parwal sabzi | mix veg sabzi | aloo shimla mirch | methi sabzi
3. PROTEIN — chicken sukka | chicken curry | fish dry fry | mackerel rava fry | paneer bhurji | paneer (in matar paneer gravy)
4. STARCH — Rice at lunch | Roti at dinner (fish days and dal-only days = rice BOTH meals)

STRICT RULES:
- Kadhi ONLY with fish dry fry (NEVER with chicken)
- Rajma or black chana day = NO meat that day
- Torai = ALWAYS dry sabzi, NEVER a curry
- NEVER repeat same gravy+sabzi combination in same week
- Each chicken day must have DIFFERENT gravy AND different sabzi
- Paneer day: matar paneer IS both the gravy and the protein — still needs a dry sabzi

CORRECT EXAMPLES:
Monday (chicken): Lunch = Dal tadka + Torai sabzi + Chicken sukka + Rice | Dinner = Dal tadka + Torai sabzi + Chicken sukka + Roti
Tuesday (fish): Lunch = Kadhi + Bhindi fry + Mackerel dry fry + Rice | Dinner = Kadhi + Bhindi fry + Mackerel dry fry + Rice
Thursday (paneer): Lunch = Matar paneer + Bhindi fry + Rice | Dinner = Matar paneer + Bhindi fry + Roti
Wednesday (chicken): Lunch = Palak dal + Beans carrot sabzi + Chicken sukka + Rice | Dinner = Palak dal + Beans carrot sabzi + Chicken sukka + Roti

PER SITTING MACROS:
Breakfast: Supriya 38g/480kcal | Vivek 38g/520kcal
Chicken meal: Supriya 32g/400kcal | Vivek 42g/500kcal
Fish meal: Supriya 30g/370kcal | Vivek 40g/460kcal
Paneer meal: Supriya 24g/380kcal | Vivek 32g/470kcal
Dal/rajma meal: Supriya 20g/350kcal | Vivek 28g/430kcal
Evening snack: 8g/120kcal each

EVENING SNACK ROTATION: pesarettu + coconut chutney | sprouted moong/chana chaat | Epigamia Greek yogurt | fruit

WEEKLY SHOPPING LIST FORMAT (always include prices):
Group by platform. Use these REAL prices:
LICIOUS (weekly quantities):
- Eggs: 6 dozen × ₹132 = ₹792
- Chicken breast 450g: 3 packs × ₹295 = ₹885 (one per chicken day Mon/Wed/Sat)
- Chicken curry cut 500g: 3 packs × ₹260 = ₹780 (one per chicken day)
- Mackerel 500g: 3 packs × ₹350 = ₹1,050 (one per fish day Tue/Fri/Sun)
LICIOUS TOTAL: ₹3,507

INSTAMART (weekly quantities):
- Akshayakalpa Paneer 200g: 2 packs × ₹136 = ₹272 (Thursday paneer day)
- A2 Milk 500ml: 14 pouches × ₹53 = ₹742 (2 per day)
- Epigamia Greek yogurt: 2 × ₹249 = ₹498
- Whole wheat bread: 2 loaves × ₹50 = ₹100
- Torai 500g: ₹30 | Bhindi 500g: ₹40 | Beans 500g: ₹40 | Cauliflower: ₹45
- Potato 1kg: ₹35 | Cabbage: ₹35 | Baingan 500g: ₹35 | Beetroot: ₹30
- Palak bunch: ₹30 | Carrot 500g: ₹35 | Matar frozen 500g: ₹65
- Tata Sampann Dal 500g: ₹130 | Curd 500g × 2: ₹80
- Pesarettu batter: ₹69 | Dragon fruit 600g: ₹240 | Banana 6pc: ₹45 | Blueberries 125g: ₹199
INSTAMART TOTAL: ~₹2,523

MANGO (bulk):
- Sona Masoori Rice 5kg: ₹320
- Whole wheat atta 1kg: ₹60
MANGO TOTAL: ₹380

WEEKLY GRAND TOTAL: ~₹6,410

BUDGET: Monthly target ₹38,000. Weekly target ₹6,500. Always show estimated weekly total.

WEEKLY COST BREAKDOWN (use these to calculate shopping list total):
Eggs 6 dozen: ₹792
Chicken days x3 (breast+curry cut): ₹1,665
Fish days x3 (mackerel): ₹1,050
Paneer day x1 (2 packs): ₹272
Milk 14 pouches: ₹742
Greek yogurt 2 packs: ₹498
Vegetables (all sabzis): ₹350
Dal/rajma/chana: ₹130
Bread 2 loaves: ₹100
Fruits for smoothies: ₹500
Pesarettu batter: ₹69
Curd: ₹80
TOTAL WEEKLY: ~₹6,248
"""

# ── Tools ─────────────────────────────────────────────────────────
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

# ── Tool executor ─────────────────────────────────────────────────
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

# ── Agent loop ────────────────────────────────────────────────────
async def run_agent(messages: list) -> dict:
    now = datetime.now()
    today = now.strftime("%A, %d %B %Y")
    is_veg = now.weekday() == 3
    day_num = now.weekday()  # 0=Mon, 3=Thu, etc

    # Day protein type
    protein_today = {0: "CHICKEN", 1: "FISH", 2: "CHICKEN", 3: "PANEER (VEG DAY)",
                     4: "FISH", 5: "CHICKEN", 6: "FISH, CHICKEN, or PANEER (Sunday special — your choice)"}[day_num]

    chat_messages = [SystemMessage(content=SYSTEM)]
    chat_messages.append(HumanMessage(content=
        f"[Today: {today}. Protein rotation today: {protein_today}. Day {now.day}/31 of month.]"
    ))

    for m in messages[-4:]:
        if m.get("role") == "user":
            chat_messages.append(HumanMessage(content=m["content"]))
        elif m.get("role") == "assistant":
            chat_messages.append(AIMessage(content=m.get("content", "")))

    # Agentic loop
    for _ in range(4):
        response = llm_with_tools.invoke(chat_messages)
        chat_messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            result = await execute_tool(tc["name"], tc.get("args", {}))
            chat_messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    # Extract final text
    final = ""
    for msg in reversed(chat_messages):
        if isinstance(msg, AIMessage) and msg.content:
            final = msg.content
            break

    final = final.strip()
    return {"response": final, "shopping_list": None, "meal_plan": None}