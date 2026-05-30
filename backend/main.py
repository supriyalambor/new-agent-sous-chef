from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from agent.graph import run_agent, run_weekly_agent
from api.expenses import router as expenses_router
from api.meals import router as meals_router
from api.preferences import router as preferences_router

load_dotenv()

app = FastAPI(title="Sous Chef API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(expenses_router, prefix="/api/expenses")
app.include_router(meals_router, prefix="/api/meals")
app.include_router(preferences_router, prefix="/api/preferences")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    voice: Optional[bool] = False

class ChatResponse(BaseModel):
    response: str
    shopping_list: Optional[list] = None
    meal_plan: Optional[dict] = None

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await run_agent([m.dict() for m in request.messages])
        return ChatResponse(
            response=result["response"],
            shopping_list=result.get("shopping_list"),
            meal_plan=result.get("meal_plan"),
        )
    except Exception as e:
        import traceback
        print("CHAT ERROR:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/weekly-plan")
async def weekly_plan():
    """
    Called every Friday by Railway cron job.
    LLM plans next week and sends email to Supriya + Vivek.
    """
    try:
        result = await run_weekly_agent()
        return result
    except Exception as e:
        import traceback
        print("WEEKLY PLAN ERROR:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Sous Chef v2"}