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
    "fish":    ["kadhi", "palak dal", "sambar", "moong dal", "lauki dal", "santula"],
    "chicken": ["dal tadka", "palak dal", "aloo gobi gravy", "moong dal", "lauki dal", "chole"],
    "veg":     ["matar paneer", "rajma soyabean", "chole", "palak paneer",
                "chana masala", "paneer handi", "santula", "moong dal", "rajma", "black chana"],
}

# Gravies that go with Rice (dal-based, not paratha-compatible)
DAL_GRAVIES = {"dal tadka", "palak dal", "moong dal", "lauki dal", "sambar", "kadhi", "santula",
               "rajma", "black chana", "rajma soyabean"}

SABZIS = [
    "torai", "bhindi fry", "beans carrot", "cauliflower matar aloo", "cabbage",
    "baingan bharta", "beetroot", "lauki", "parwal", "mix veg",
    "aloo shimla mirch", "methi", "aloo jeera", "sem sabzi",
    "tinda", "gawar", "aloo gobi dry"
]

PROTEINS = {
    "chicken": ["chicken sukka", "chicken handi", "chicken masala"],
    "fish":    ["mackerel dry fry", "sardine dry fry", "mackerel rava fry"],
    "veg":     ["soyabean curry", "chana", "paneer"],  # paneer handled via gravy
}

# Thursday: if no paneer gravy, add paneer bhurji as side
THU_PANEER_GRAVIES = ["matar paneer", "palak paneer", "paneer handi"]

# Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
DAY_TYPE = {0:"chicken", 1:"fish", 2:"chicken", 3:"veg", 4:"fish", 5:"chicken", 6:"flex"}

def plan_week(history: list, avoid: list = None, replace: dict = None) -> list:
    """Generate a week plan with no repeats, enforced in Python.
    Respects user preferences: avoid list and replace map.
    """
    avoid = [a.lower().strip() for a in (avoid or [])]
    replace = {k.lower().strip(): v.lower().strip() for k, v in (replace or {}).items()}
    
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

    # Get next Monday (or today if Monday)
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7
    monday = today if days_until_monday == 0 else today + timedelta(days=days_until_monday)

    week_plan = []
    used_this_week_gravies = set()
    used_this_week_sabzis = set()
    used_this_week_proteins = {}  # per day_type to avoid cross-type conflicts

    for i in range(7):
        date = monday + timedelta(days=i)
        day_type = DAY_TYPE[i]
        if day_type == "flex":
            day_type = random.choice(["fish", "veg"])  # never chicken — Mon/Wed/Sat already cover it

        # Pick gravy — Saturday restricted to non-dal gravies only (dal+stuffed paratha forbidden)
        # chicken curry is NOT in this list — it gets assigned in Option B below, not from the pool
        SAT_CHICKEN_GRAVIES = ["chole", "aloo gobi gravy"]
        if day_type == "chicken" and i == 5:
            sat_pool = [g for g in SAT_CHICKEN_GRAVIES if g not in used_this_week_gravies]
            if not sat_pool: sat_pool = SAT_CHICKEN_GRAVIES
            allowed = sat_pool
        else:
            allowed = [replace.get(g, g) for g in GRAVIES[day_type]]
            allowed = [g for g in allowed if g not in avoid]
            if not allowed: allowed = GRAVIES[day_type]

        gravy_pool = [g for g in allowed if g not in used_this_week_gravies and g not in used_gravies]
        if not gravy_pool:
            gravy_pool = [g for g in allowed if g not in used_this_week_gravies]
        if not gravy_pool:
            gravy_pool = allowed
        gravy = random.choice(gravy_pool)
        # For Saturday Option B, gravy will be overridden to "chicken curry" later
        # Don't add to used set yet — we'll add after starch block

        # Pick sabzi not used this week or recently
        # Explicit conflict map: if gravy contains key, exclude sabzis containing value
        GRAVY_SABZI_CONFLICTS = {
            "aloo gobi": ["aloo", "gobi"],
            "lauki dal": ["lauki"],
            "matar paneer": ["matar"],
            "palak dal": ["palak"],
        }
        def sabzi_conflicts(gravy, sabzi):
            for gravy_key, blocked_words in GRAVY_SABZI_CONFLICTS.items():
                if gravy_key in gravy.lower():
                    if any(w in sabzi.lower().split() for w in blocked_words):
                        return True
            return False

        sabzi_pool = [s for s in SABZIS
                      if s not in used_this_week_sabzis and s not in used_sabzis
                      and not sabzi_conflicts(gravy, s)]
        if not sabzi_pool:
            sabzi_pool = [s for s in SABZIS if s not in used_this_week_sabzis and not sabzi_conflicts(gravy, s)]
        if not sabzi_pool:
            sabzi_pool = [s for s in SABZIS if not sabzi_conflicts(gravy, s)]
        if not sabzi_pool:
            sabzi_pool = SABZIS
        sabzi = random.choice(sabzi_pool)
        used_this_week_sabzis.add(sabzi)

        # Saturday special — decide option BEFORE picking protein to avoid wasting a protein slot
        sat_roll = random.random() if (day_type == "chicken" and i == 5) else None
        if sat_roll is not None and sat_roll < 0.3:
            # Option A (30%): Khichdi + Chokha + Fish fry
            fish_protein = random.choice(["Mackerel Dry Fry", "Sardine Dry Fry"])
            meal = f"Khichdi + Chokha + {fish_protein}"
            week_plan.append({
                "date": date.strftime("%Y-%m-%d"),
                "day": date.strftime("%A"),
                "day_type": "khichdi",
                "lunch": meal,
                "dinner": meal,
            })
            continue  # skip rest of loop

        # Pick protein — no repeats within same week per day type
        if day_type == "veg" and gravy in THU_PANEER_GRAVIES:
            veg_proteins_no_paneer = [p for p in PROTEINS["veg"] if p != "paneer" and p not in used_this_week_proteins.get("veg", set())]
            if not veg_proteins_no_paneer:
                veg_proteins_no_paneer = [p for p in PROTEINS["veg"] if p != "paneer"]
            protein = random.choice(veg_proteins_no_paneer) if veg_proteins_no_paneer else "paneer bhurji"
        else:
            protein_pool = [p for p in PROTEINS[day_type] if p not in used_this_week_proteins.get(day_type, set())]
            if not protein_pool:
                protein_pool = PROTEINS[day_type]
            protein = random.choice(protein_pool)
        used_this_week_proteins.setdefault(day_type, set()).add(protein)

        # STARCH RULE — Saturday first (overrides dal rule), then gravy-based
        if day_type == "chicken" and i == 5:  # Saturday
            if sat_roll < 0.65:
                # Option B (35%): Chicken curry + stuffed paratha + sabzi
                stuffing = random.choice(["Aloo", "Paneer Cauliflower", "Methi", "Palak"])
                starch = f"{stuffing} Stuffed Paratha"
                gravy = "chicken curry"
                protein = ""  # chicken curry IS the protein dish
            else:
                # Option C (35%): Regular chicken + stuffed paratha
                stuffing = random.choice(["Aloo", "Paneer Cauliflower", "Methi", "Palak"])
                starch = f"{stuffing} Stuffed Paratha"
        elif day_type == "fish" or gravy in DAL_GRAVIES:
            starch = "Rice"
        elif day_type == "chicken":
            starch = "3 Plain Parathas (Supriya) / 4 Rotis (Vivek)"
        elif day_type == "veg":
            veg_paratha_gravies = ["chole", "matar paneer", "palak paneer",
                                   "chana masala", "aloo gobi gravy", "paneer handi"]
            if gravy in veg_paratha_gravies:
                starch = "3 Plain Parathas (Supriya) / 4 Rotis (Vivek)"
            else:
                starch = "Rice"
        else:
            starch = "Rice"

        # Protein overrides based on gravy
        GRAVY_CONTAINS_PROTEIN = {"matar paneer", "palak paneer", "paneer handi", "chicken curry"}
        used_this_week_gravies.add(gravy)  # add after potential Saturday override
        NEEDS_PANEER_BHURJI = {"chole", "aloo gobi gravy", "rajma soyabean", "rajma",
                                "black chana", "chana masala"}
        if gravy in GRAVY_CONTAINS_PROTEIN:
            protein = ""
        elif day_type == "veg" and gravy in NEEDS_PANEER_BHURJI:
            protein = "paneer bhurji"
        elif day_type == "veg" and gravy not in THU_PANEER_GRAVIES:
            protein = "paneer bhurji"
        # chicken/fish days keep their protein even with chole/aloo gobi gravy

        if protein:
            meal = f"{gravy.title()} + {sabzi.title()} + {protein.title()} + {starch}"
        else:
            meal = f"{gravy.title()} + {sabzi.title()} + {starch}"
        lunch = meal
        dinner = meal

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

WEEKLY ROTATION: Mon=Chicken | Tue=Fish | Wed=Chicken | Thu=Veg | Fri=Fish | Sat=Chicken | Sun=Flexible
ALL MEALS ARE INDIAN HOME COOKING ONLY — no Western food, no biryani, no wraps, no salads, no fusion. Only traditional Indian home food.

BREAKFAST every day: 8 egg whites bhurji + smoothie (ON Whey + yogurt + banana + blueberries + dragon fruit)
Sunday exception: paratha + egg bhurji

APPROVED COMBOS (inspiration):
- Palak dal + Mackerel dry fry + Mix veg
- Chicken curry + Torai sabzi
- Dal tadka + Beetroot + Chicken sukka
- Kadhi + Beans carrot + Mackerel dry fry
- Rajma soyabean + Aloo shimla mirch + Paneer bhurji

SHOPPING PRICES (use when asked):
Licious: Eggs ₹139/doz×6=₹834 | Chicken breast ₹295×3=₹885 | Curry cut ₹260×3=₹780 | Mackerel ₹350×3=₹1,050
Instamart: Paneer ₹136×2=₹272 | Milk ₹53×14=₹742 | Yogurt ₹249×2=₹498
Mango (buy veggies here — cheaper than Instamart):
  Beetroot ₹99/kg | Carrot ₹99/kg | Lauki ₹59/kg | Torai ₹129/kg | French beans ₹159/kg
  Potato ₹29/kg | Tomato ₹51/kg | Capsicum ₹89/kg | Ginger ₹199/kg
  Kabuli chana ₹196/kg | Rajma ₹184/kg | Moong ₹163/kg
  Rice 5kg ₹320 | Atta 1kg ₹60
  Mango/Papaya/fruits ~₹300
WEEKLY TOTAL: ~₹6,500 | MONTHLY BUDGET: ₹38,000 (these are different!)
ALWAYS show the weekly total at the end of every shopping list.
BUY VEGETABLES FROM MANGO — fresher and cheaper than Instamart.

STARCH RULES (based on gravy type):
- Dal (any) / Kadhi / Rajma / Santula / Sambar → Rice
- Chole / Matar paneer / Palak paneer / Paneer handi → Paratha
- Chicken gravy → 3 Plain Parathas (Supriya) / 4 Rotis (Vivek)
- Saturday chicken → Stuffed Paratha (aloo/paneer cauliflower/methi/palak)
- Fish days → Rice always
- NO roti+dal combo ever

PORTIONS:
Supriya: chicken 150g | fish 150g | paneer 80g | rice 60g dry | 3 parathas | dal 30g | veg 100g
Vivek: chicken 200g | fish 200g | paneer 120g | rice 100g dry | 4 rotis | dal 40g | veg 120g

TARGETS (show ONLY when user explicitly asks for macros or calories):
Supriya: 1,700 kcal/day | 130g protein/day
Vivek: 2,200 kcal/day | 166g protein/day
Do NOT mention calorie or protein numbers unless the user asks.

When you receive a MEAL_PLAN in the context, present it nicely in this format:

Here's your week! 🍽️

📅 [Day] — [Chicken/Fish/Veg]
🍳 BF: Egg whites + smoothie
🍛 Lunch & Dinner: [meal]

(Lunch and dinner are the same dish cooked once — no need to show separately)
After the plan, ask: "Want macros, quantities, or the shopping list?"

For budget questions use get_expenses tool.
When user says "I have X at home" or "I ran out of X" → call update_pantry immediately.
When generating shopping list → ALWAYS call get_pantry first, then remove in-stock items from the list.
Keep responses warm and SHORT. Only show macros/quantities if asked."""

TOOLS = [
    {"type": "function", "function": {
        "name": "get_expenses",
        "description": "Get this month grocery expenses",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "get_pantry",
        "description": "Get current pantry inventory — what items are already in stock at home",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "update_pantry",
        "description": "Update pantry when user says they have or don't have items. Call when user says 'I have X' or 'I ran out of X'",
        "parameters": {
            "type": "object",
            "properties": {
                "items_in_stock": {"type": "string", "description": "comma separated items user has e.g. 'rice,dal,atta'"},
                "items_out_of_stock": {"type": "string", "description": "comma separated items user is out of e.g. 'paneer,milk'"}
            },
            "required": []
        }
    }},
    {"type": "function", "function": {
        "name": "get_preferences",
        "description": "Get saved food preferences — items to avoid, replacements, favourites",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "save_preference",
        "description": "Save a food preference when user says they don't like something, want to replace something, or love something. Call immediately when user expresses a preference.",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["avoid", "favourite", "replace"], "description": "Type of preference"},
                "item": {"type": "string", "description": "The food item e.g. 'moong dal', 'bhindi fry'"},
                "replace_with": {"type": "string", "description": "Only for type=replace: what to use instead e.g. 'chana dal'"},
                "reason": {"type": "string", "description": "Why e.g. 'doesnt like the taste'"}
            },
            "required": ["type", "item"]
        }
    }},
    {"type": "function", "function": {
        "name": "send_weekly_email",
        "description": "Send the weekly meal plan and shopping list email to Supriya and Vivek",
        "parameters": {
            "type": "object",
            "properties": {
                "plan_text": {"type": "string", "description": "Formatted weekly meal plan"},
                "shopping_text": {"type": "string", "description": "Formatted shopping list with prices"}
            },
            "required": ["plan_text", "shopping_text"]
        }
    }},
    {"type": "function", "function": {
        "name": "log_expense",
        "description": "Log a grocery expense ONLY when user explicitly says they spent money, e.g. 'I spent 500 on Licious'. Do NOT call this for shopping lists.",
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
    raw = r.json()
    data = raw if isinstance(raw, list) else []
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
                    "total_protein": {"chicken":162,"fish":136,"veg":112,"khichdi":136}.get(day["day_type"],130),
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
            raw = r.json()
            data = raw if isinstance(raw, list) else []
            total = sum(e.get("amount", 0) for e in data)
            by_platform = {}
            for e in data:
                by_platform[e.get("platform","other")] = by_platform.get(e.get("platform","other"),0) + e.get("amount",0)
            days = datetime.now().day
            return json.dumps({"total": total, "by_platform": by_platform, "target": 38000,
                               "remaining": 38000-total, "projected": round((total/days)*31) if days else 0})
        elif name == "get_pantry":
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    sb_url("pantry_inventory?select=item,in_stock&order=item"),
                    headers=sb_headers()
                )
            raw = r.json()
            data = raw if isinstance(raw, list) else []
            in_stock = [d["item"] for d in data if d.get("in_stock")]
            out_of_stock = [d["item"] for d in data if not d.get("in_stock")]
            return json.dumps({
                "in_stock": in_stock,
                "out_of_stock": out_of_stock
            })

        elif name == "update_pantry":
            items_in = [i.strip().lower() for i in args.get("items_in_stock", "").split(",") if i.strip()]
            items_out = [i.strip().lower() for i in args.get("items_out_of_stock", "").split(",") if i.strip()]
            async with httpx.AsyncClient() as client:
                for item in items_in:
                    await client.post(
                        sb_url("pantry_inventory"),
                        headers={**sb_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
                        json={"item": item, "in_stock": True}
                    )
                for item in items_out:
                    await client.post(
                        sb_url("pantry_inventory"),
                        headers={**sb_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
                        json={"item": item, "in_stock": False}
                    )
            all_items = items_in + items_out
            return json.dumps({"success": True, "updated": all_items})

        elif name == "get_preferences":
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    sb_url("preferences?order=created_at.desc"),
                    headers=sb_headers()
                )
            raw = r.json()
            data = raw if isinstance(raw, list) else []
            avoid = [p["item"] for p in data if p.get("type") == "avoid"]
            favourites = [p["item"] for p in data if p.get("type") == "favourite"]
            replace = {p["item"]: p.get("replace_with","") for p in data if p.get("type") == "replace" and p.get("replace_with")}
            return json.dumps({"avoid": avoid, "favourites": favourites, "replace": replace})

        elif name == "save_preference":
            ptype = args.get("type", "avoid")
            item = args.get("item", "").lower().strip()
            replace_with = args.get("replace_with", "").lower().strip()
            reason = args.get("reason", "")
            async with httpx.AsyncClient() as client:
                await client.post(
                    sb_url("preferences"),
                    headers={**sb_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
                    json={"type": ptype, "item": item, "replace_with": replace_with,
                          "reason": reason, "created_at": datetime.now().isoformat()}
                )
            msg = {"avoid": f"Got it! I'll avoid {item} in future plans.",
                   "favourite": f"Noted! I'll include {item} more often.",
                   "replace": f"Got it! I'll use {replace_with} instead of {item} going forward."}
            return json.dumps({"success": True, "message": msg.get(ptype, "Preference saved!")})

        elif name == "send_weekly_email":
            plan_text = args.get("plan_text", "")
            shopping_text = args.get("shopping_text", "")
            supriya_email = os.getenv("SUPRIYA_EMAIL")
            vivek_email = os.getenv("VIVEK_EMAIL")
            resend_key = os.getenv("RESEND_API_KEY")
            if not resend_key:
                return json.dumps({"error": "RESEND_API_KEY not set"})
            body = f"""Hey! 👋 Here's your Sous Chef plan for next week.

━━━━━━━━━━━━━━━━━━━━
🍽️ WEEKLY MEAL PLAN
━━━━━━━━━━━━━━━━━━━━

{plan_text}

━━━━━━━━━━━━━━━━━━━━
🛒 SHOPPING LIST
━━━━━━━━━━━━━━━━━━━━

{shopping_text}

━━━━━━━━━━━━━━━━━━━━
Have a great week! 💪
— Sous Chef 🍳"""
            async with httpx.AsyncClient() as client:
                for email in [supriya_email, vivek_email]:
                    if email:
                        await client.post(
                            "https://api.resend.com/emails",
                            headers={"Authorization": f"Bearer {resend_key}",
                                     "Content-Type": "application/json"},
                            json={"from": "Sous Chef <noreply@resend.dev>",
                                  "to": email,
                                  "subject": f"🍽️ Your Week Ahead — Sous Chef",
                                  "text": body}
                        )
            return json.dumps({"success": True, "sent_to": [supriya_email, vivek_email]})

        elif name == "log_expense":
            amount = args.get("amount", 0)
            if isinstance(amount, str):
                try: amount = float(amount)
                except: amount = 0
            platform = args.get("platform", "instamart").lower()
            async with httpx.AsyncClient() as client:
                await client.post(sb_url("expenses"), headers=sb_headers(),
                    json={"platform": platform, "amount": amount,
                          "note": args.get("note",""), "expense_date": datetime.now().strftime("%Y-%m-%d")})
            return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})

def generate_shopping_list(week_plan: list, in_stock: list = None) -> list:
    """Generate structured shopping list from the week plan.
    Removes items already in pantry (in_stock).
    """
    in_stock = [i.lower().strip() for i in (in_stock or [])]
    
    def is_in_stock(item_name):
        return any(s in item_name.lower() for s in in_stock)
    items = []

    # Count protein days
    chicken_days = sum(1 for d in week_plan if d["day_type"] == "chicken")
    fish_days = sum(1 for d in week_plan if d["day_type"] in ("fish", "khichdi"))
    has_paneer = any("paneer" in d.get("gravy","") or "paneer bhurji" in d.get("protein","") for d in week_plan)

    # ── Licious ──
    if not is_in_stock("eggs"):
        items.append({"item": "Eggs", "qty": "6 dozen", "platform": "licious", "estimatedPrice": 834})
    if chicken_days > 0 and not is_in_stock("chicken breast"):
        items.append({"item": "Chicken breast", "qty": f"{chicken_days}×450g", "platform": "licious", "estimatedPrice": chicken_days * 295})
    if chicken_days > 0 and not is_in_stock("chicken curry cut"):
        items.append({"item": "Chicken curry cut", "qty": f"{chicken_days}×500g", "platform": "licious", "estimatedPrice": chicken_days * 260})
    if fish_days > 0 and not is_in_stock("mackerel"):
        items.append({"item": "Mackerel", "qty": f"{fish_days}×500g", "platform": "licious", "estimatedPrice": fish_days * 350})

    # ── Instamart ──
    if has_paneer and not is_in_stock("paneer"):
        items.append({"item": "Paneer", "qty": "2×200g", "platform": "instamart", "estimatedPrice": 272})
    if not is_in_stock("milk"):
        items.append({"item": "A2 Milk", "qty": "14×500ml", "platform": "instamart", "estimatedPrice": 742})
    if not is_in_stock("yogurt"):
        items.append({"item": "Epigamia Yogurt", "qty": "2", "platform": "instamart", "estimatedPrice": 498})

    # ── Mango ──
    sabzis = [d.get("sabzi","") for d in week_plan if d.get("sabzi") and d.get("sabzi") != "none"]
    items.append({"item": "Vegetables (week)", "qty": ", ".join(set(sabzis)), "platform": "mango", "estimatedPrice": 350})
    if not is_in_stock("fruits"):
        items.append({"item": "Fruits (banana, blueberries, dragon fruit)", "qty": "week supply", "platform": "mango", "estimatedPrice": 500})

    gravies = [d.get("gravy","") for d in week_plan]
    if any("dal" in g or "kadhi" in g or "sambar" in g for g in gravies) and not is_in_stock("dal"):
        items.append({"item": "Dal / Lentils", "qty": "as needed", "platform": "mango", "estimatedPrice": 130})
    if any("rice" in d.get("lunch","").lower() for d in week_plan) and not is_in_stock("rice"):
        items.append({"item": "Rice 5kg", "qty": "1", "platform": "mango", "estimatedPrice": 320})
    if any("paratha" in d.get("lunch","").lower() or "roti" in d.get("lunch","").lower() for d in week_plan) and not is_in_stock("atta"):
        items.append({"item": "Atta 1kg", "qty": "1", "platform": "mango", "estimatedPrice": 60})

    return items

async def run_weekly_agent() -> dict:
    """
    Autonomous Friday agent — LLM is the brain.
    Runs every Friday, plans next week, sends email. No human needed.
    """
    now = datetime.now()

    # Get all context first
    history = await get_history()
    
    # Build week plan using preferences
    prefs_result = await execute_tool("get_preferences", {})
    prefs = json.loads(prefs_result)
    avoid = prefs.get("avoid", [])
    replace = prefs.get("replace", {})

    pantry_result = await execute_tool("get_pantry", {})
    pantry = json.loads(pantry_result)
    in_stock = pantry.get("in_stock", [])

    # Generate plan with preference overrides
    week_plan = plan_week(history, avoid=avoid, replace=replace)
    await save_plan(week_plan)
    shopping_list = generate_shopping_list(week_plan, in_stock=in_stock)

    # Format plan as plain text
    def format_day_type(dt):
        labels = {"chicken": "Chicken", "fish": "Fish", "veg": "Veg",
                 "khichdi": "Khichdi Special", "flex": "Flexible"}
        return labels.get(dt, dt.title())

    plan_lines = []
    for d in week_plan:
        plan_lines.append(f"{d['day']} — {format_day_type(d['day_type'])}")
        plan_lines.append(f"  BF: Egg whites + smoothie")
        plan_lines.append(f"  Lunch & Dinner: {d['lunch']}")
        plan_lines.append("")
    plan_text = "\n".join(plan_lines)

    # Format shopping list as plain text grouped by platform
    shop_lines = []
    total = 0
    for platform in ["licious", "instamart", "mango"]:
        platform_items = [i for i in shopping_list if i.get("platform") == platform]
        if not platform_items: continue
        shop_lines.append(f"📍 {platform.upper()}")
        for item in platform_items:
            price = item.get("estimatedPrice", 0)
            total += price
            shop_lines.append(f"  • {item['item']} ({item['qty']}) — ₹{price:,}")
        shop_lines.append("")
    shop_lines.append(f"TOTAL: ~₹{total:,}")
    shopping_text = "\n".join(shop_lines)

    # Send email
    email_result = await execute_tool("send_weekly_email", {
        "plan_text": plan_text,
        "shopping_text": shopping_text
    })

    return {"success": True, "plan": plan_text, "email_result": json.loads(email_result)}

async def run_agent(messages: list) -> dict:
    now = datetime.now()
    user_message = messages[-1].get("content", "").lower() if messages else ""

    # Check if user wants a week plan or today's plan
    wants_plan = any(w in user_message for w in ["plan my week", "plan week", "plan next week", "weekly menu", "plan meals", "meal plan"])
    wants_today = any(w in user_message for w in ["plan today", "today's meal", "what should i eat today", "today's plan", "plan for today"])

    wants_shopping = any(w in user_message for w in ["shopping list", "shopping", "groceries", "what to buy", "grocery list"])

    meal_plan_context = ""
    week_plan = None
    shopping_list = None

    if wants_plan or wants_today:
        history = await get_history()
        prefs_raw = await execute_tool("get_preferences", {})
        prefs = json.loads(prefs_raw)
        week_plan = plan_week(history, avoid=prefs.get("avoid",[]), replace=prefs.get("replace",{}))
        if wants_today:
            today_name = now.strftime("%A")
            week_plan = [d for d in week_plan if d["day"] == today_name] or [week_plan[0]]
        await save_plan(week_plan)
        pantry_raw = await execute_tool("get_pantry", {})
        pantry = json.loads(pantry_raw)
        shopping_list = generate_shopping_list(week_plan, in_stock=pantry.get("in_stock", []))
        def format_day_type(dt):
            labels = {"chicken": "Chicken", "fish": "Fish", "veg": "Veg",
                     "khichdi": "Khichdi Special", "flex": "Flexible"}
            return labels.get(dt, dt.title())
        plan_text = "\n".join([
            f"{d['day']} ({format_day_type(d['day_type'])}): {d['lunch']}"
            for d in week_plan
        ])
        meal_plan_context = f"""

MEAL PLAN GENERATED — present EXACTLY as below. Do NOT rewrite or change anything:
{plan_text}

Format each day EXACTLY like this:
📅 [Day] — [day_type]
🍳 BF: Egg whites + smoothie
🍛 Lunch & Dinner: [exact meal]

Do not show Lunch and Dinner separately."""

    chat_messages = [SystemMessage(content=SYSTEM)]
    chat_messages.append(HumanMessage(content=
        f"[Today: {now.strftime('%A %d %B %Y')} | Day {now.day}/31]{meal_plan_context}"
    ))

    for m in messages[-4:]:
        if m.get("role") == "user":
            # If we already have a meal plan, replace user message to avoid LLM replanning
            if (wants_plan or wants_today) and m == messages[-1]:
                chat_messages.append(HumanMessage(content="Present the meal plan above exactly as instructed."))
            else:
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

    return {"response": final.strip(), "shopping_list": shopping_list, "meal_plan": None}