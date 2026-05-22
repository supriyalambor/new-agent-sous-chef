from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
import os
import json
from datetime import datetime, timedelta
import httpx

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

# ── OpenRouter LLM ────────────────────────────────────────────────
llm = ChatOpenAI(
    model="llama-3.1-8b-instant",
    openai_api_base="https://api.groq.com/openai/v1",
    openai_api_key=os.getenv("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"),
    temperature=0.2,
    max_tokens=1000,
)

# ── State ─────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: List[dict]
    meal_history: Optional[str]
    expenses: Optional[dict]
    response: Optional[str]
    shopping_list: Optional[list]
    meal_plan: Optional[dict]
    needs_tools: bool

# ── Tools ─────────────────────────────────────────────────────────
@tool
def get_meal_history() -> str:
    """Get meals eaten in the last 14 days to avoid repetition"""
    since = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    data = get_supabase().from_("meal_plans").select("planned_date, lunch, dinner").gte("planned_date", since).order("planned_date", desc=True).execute()
    if not data.data:
        return "No meal history yet — first week!"
    return "\n".join([f"{r['planned_date']}: {r['lunch']}" for r in data.data])

@tool
def get_month_expenses() -> dict:
    """Get current month's grocery expenses by platform"""
    now = datetime.now()
    month_start = f"{now.year}-{now.month:02d}-01"
    data = get_supabase().from_("expenses").select("platform, amount, note, expense_date").gte("expense_date", month_start).execute()
    total = sum(r["amount"] for r in (data.data or []))
    by_platform = {}
    for r in (data.data or []):
        by_platform[r["platform"]] = by_platform.get(r["platform"], 0) + r["amount"]
    return {"total": total, "by_platform": by_platform, "target": 38000, "remaining": 38000 - total}

@tool
def save_meal_plan(date: str, lunch: str, dinner: str, is_veg: bool = False, total_protein: int = 0) -> dict:
    """Save a confirmed meal plan to database"""
    get_supabase().from_("meal_plans").upsert({
        "planned_date": date,
        "day_of_week": datetime.strptime(date, "%Y-%m-%d").strftime("%a"),
        "is_veg": is_veg,
        "lunch": lunch,
        "dinner": dinner,
        "total_protein": total_protein,
        "confirmed": True,
    }).execute()
    return {"success": True, "saved": date}

@tool
def save_expense(platform: str, amount: int, note: str = "") -> dict:
    """Log a grocery expense"""
    get_supabase().from_("expenses").insert({
        "platform": platform,
        "amount": amount,
        "note": note,
        "expense_date": datetime.now().strftime("%Y-%m-%d"),
    }).execute()
    return {"success": True}

@tool
def get_prices() -> list:
    """Get current grocery prices from database"""
    data = get_supabase().from_("prices").select("item, quantity, price_inr, platform, category").order("category").execute()
    return data.data or []

TOOLS = [get_meal_history, get_month_expenses, save_meal_plan, save_expense, get_prices]
llm_with_tools = llm.bind_tools(TOOLS)

# ── System prompt ─────────────────────────────────────────────────
SYSTEM = """You are Sous Chef, an intelligent meal planning agent for Supriya and Vivek in Bengaluru.

NUTRITION TARGETS:
- Supriya (36F, 65kg, fat loss): 1,846 kcal/day | 130g protein
- Vivek (39M, 83kg, fat loss): 2,709 kcal/day | 166g protein

FIXED BREAKFAST (every day, no exceptions):
8 egg white bhurji + 2 whole wheat bread slices + protein smoothie with fruit
Supriya: 38g protein | 480 kcal | Vivek: 38g protein | 520 kcal

WEEKLY PROTEIN ROTATION (strict):
- Monday: Chicken
- Tuesday: Fish (mackerel/sardines — DRY FRY only, no fish curry)
- Wednesday: Chicken (DIFFERENT combo from Monday)
- Thursday: Paneer — VEG DAY (no meat/fish/eggs in main meals)
- Friday: Fish (DIFFERENT sabzi from Tuesday)
- Saturday: Chicken (DIFFERENT combo from Mon and Wed)
- Sunday: Fish OR Paneer + special paratha breakfast

MEAL STRUCTURE (every lunch AND dinner):
1. GRAVY — one of: dal tadka, palak dal, rajma, black chana, matar paneer, kadhi, santula, aloo gobi gravy
2. DRY SABZI — one of: torai, bhindi, beans+carrot, cauliflower+matar+aloo+carrot, cabbage, baingan bharta, beetroot
3. PROTEIN — chicken/fish/paneer (as per rotation)
4. RICE (lunch) or ROTI (dinner) — fish/dal days: rice BOTH meals

STRICT RULES:
- Kadhi → ALWAYS with fish dry fry (never with chicken)
- Rajma/chana days → NO meat (too heavy combined)
- Torai → ALWAYS dry sabzi, NEVER a curry
- NEVER repeat same gravy+sabzi combo in same week
- Each chicken day must have different gravy AND different sabzi

PER SITTING MACROS:
Chicken: Supriya 32g/400kcal | Vivek 42g/500kcal
Fish: Supriya 30g/370kcal | Vivek 40g/460kcal
Paneer: Supriya 24g/380kcal | Vivek 32g/470kcal
Dal/rajma: Supriya 20g/350kcal | Vivek 28g/430kcal
Evening snack: 8g/120kcal each

Always show macros separately for Supriya and Vivek.
Always use tools to check meal history before planning.
Keep responses clear and concise."""

# ── Graph nodes ───────────────────────────────────────────────────
def agent_node(state: AgentState) -> AgentState:
    """Main agent node — thinks and decides what to do"""
    messages = [SystemMessage(content=SYSTEM)]
    for m in state["messages"]:
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            messages.append(AIMessage(content=m["content"]))

    response = llm_with_tools.invoke(messages)
    
    # Check if tools needed
    needs_tools = bool(response.tool_calls)
    
    return {
        **state,
        "messages": state["messages"] + [{"role": "assistant", "content": response.content or "", "tool_calls": getattr(response, "tool_calls", [])}],
        "needs_tools": needs_tools,
        "_last_response": response,
    }

def should_use_tools(state: AgentState) -> str:
    return "tools" if state.get("needs_tools") else "finalize"

def finalize_node(state: AgentState) -> AgentState:
    """Extract final response and any structured data"""
    last_msg = state["messages"][-1]
    response_text = last_msg.get("content", "")
    
    # Extract shopping list if present
    shopping_list = None
    meal_plan = None
    
    if '{"shoppingList"' in response_text:
        try:
            import re
            match = re.search(r'\{"shoppingList"[\s\S]*?\]\s*\}', response_text)
            if match:
                data = json.loads(match.group())
                shopping_list = data.get("shoppingList")
                response_text = response_text.replace(match.group(), "").strip()
                # Save to DB
                week = datetime.now().strftime("%Y-%m-%d")
                get_supabase().from_("shopping_items").delete().eq("week_start", week).execute()
                if shopping_list:
                    get_supabase().from_("shopping_items").insert([{**i, "week_start": week} for i in shopping_list]).execute()
        except:
            pass

    return {
        **state,
        "response": response_text,
        "shopping_list": shopping_list,
        "meal_plan": meal_plan,
    }

# ── Build graph ───────────────────────────────────────────────────
tool_node = ToolNode(TOOLS)

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.add_node("finalize", finalize_node)

graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_use_tools, {"tools": "tools", "finalize": "finalize"})
graph.add_edge("tools", "agent")
graph.add_edge("finalize", END)

app = graph.compile()

# ── Run agent ─────────────────────────────────────────────────────
async def run_agent(messages: list) -> dict:
    now = datetime.now()
    today = now.strftime("%A, %d %B %Y")
    is_veg = now.weekday() == 3  # Thursday
    
    # Add context
    context_msg = {
        "role": "user",
        "content": f"[Context: Today is {today}{' — VEG DAY (Thursday)' if is_veg else ''}. Day {now.day}/31 of month.]"
    }
    
    # Only last 4 messages to save tokens
    recent = messages[-4:] if len(messages) > 4 else messages
    
    initial_state: AgentState = {
        "messages": [context_msg] + recent,
        "meal_history": None,
        "expenses": None,
        "response": None,
        "shopping_list": None,
        "meal_plan": None,
        "needs_tools": False,
    }
    
    result = await app.ainvoke(initial_state)
    return {
        "response": result.get("response", ""),
        "shopping_list": result.get("shopping_list"),
        "meal_plan": result.get("meal_plan"),
    }