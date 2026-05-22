from typing import TypedDict, List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
import os
import json
import httpx
from datetime import datetime, timedelta

# ── Groq LLM ─────────────────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2,
    max_tokens=1000,
)

# ── Supabase REST helpers ─────────────────────────────────────────
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
SYSTEM = """You are Sous Chef, a meal planning agent for Supriya and Vivek in Bengaluru.

TARGETS:
- Supriya (36F, 65kg, fat loss): 1,846 kcal/day | 130g protein
- Vivek (39M, 83kg, fat loss): 2,709 kcal/day | 166g protein

FIXED BREAKFAST every day: 8 egg white bhurji + 2 bread slices + protein smoothie
Supriya: 38g protein | 480 kcal | Vivek: 38g protein | 520 kcal

WEEKLY ROTATION:
Mon: Chicken | Tue: Fish dry fry | Wed: Chicken (different combo from Mon)
Thu: Paneer — VEG DAY | Fri: Fish (different sabzi from Tue)
Sat: Chicken (different from Mon+Wed) | Sun: Fish or Paneer

EVERY meal = gravy + dry sabzi + protein + rice(lunch)/roti(dinner)
Fish/dal days = rice both meals

RULES:
- Kadhi always with fish, never chicken
- Rajma/chana days = no meat
- Torai = always dry sabzi never curry
- Never repeat same combo in same week
- Thursday = paneer only, matar paneer IS the protein

PER SITTING MACROS:
Chicken: Supriya 32g/400kcal | Vivek 42g/500kcal
Fish: Supriya 30g/370kcal | Vivek 40g/460kcal
Paneer: Supriya 24g/380kcal | Vivek 32g/470kcal
Evening snack: 8g/120kcal each

Keep responses under 200 words. Always show macros per person separately."""

# ── Tools ─────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_meal_history",
            "description": "Get meals from last 14 days to avoid repetition",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "get_expenses",
            "description": "Get this month expenses and total",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_meal_plan",
            "description": "Save confirmed meal plan",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "lunch": {"type": "string"},
                    "dinner": {"type": "string"},
                    "is_veg": {"type": "boolean"},
                    "total_protein": {"type": "number"}
                },
                "required": ["date", "lunch"]
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
            return json.dumps(data[:7]) if data else "No history yet"

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
            return json.dumps({"total": total, "target": 38000, "remaining": 38000 - total})

        elif name == "save_meal_plan":
            async with httpx.AsyncClient() as client:
                await client.post(
                    sb_url("meal_plans"),
                    headers={**sb_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
                    json={
                        "planned_date": args.get("date"),
                        "day_of_week": datetime.strptime(args["date"], "%Y-%m-%d").strftime("%a") if args.get("date") else "",
                        "is_veg": args.get("is_veg", False),
                        "lunch": args.get("lunch", ""),
                        "dinner": args.get("dinner", args.get("lunch", "")),
                        "total_protein": args.get("total_protein", 0),
                        "confirmed": True,
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

    # Build message list
    chat_messages = [SystemMessage(content=SYSTEM)]
    chat_messages.append(HumanMessage(content=f"[Today: {today}{' — VEG DAY' if is_veg else ''}. Day {now.day}/31]"))

    for m in messages[-4:]:
        if m.get("role") == "user":
            chat_messages.append(HumanMessage(content=m["content"]))
        elif m.get("role") == "assistant":
            chat_messages.append(AIMessage(content=m.get("content", "")))

    # Agentic loop — max 3 iterations
    for _ in range(3):
        response = llm_with_tools.invoke(chat_messages)
        chat_messages.append(response)

        if not response.tool_calls:
            break

        # Execute all tool calls
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            result = await execute_tool(tool_name, tool_args)
            chat_messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    # Extract final text
    final = ""
    for msg in reversed(chat_messages):
        if isinstance(msg, AIMessage) and msg.content:
            final = msg.content
            break

    # Clean up
    final = final.replace("```json", "").replace("```", "").strip()

    return {"response": final, "shopping_list": None, "meal_plan": None}