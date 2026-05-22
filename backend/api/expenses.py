from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import httpx

router = APIRouter()

def get_headers():
    return {
        "apikey": os.getenv("SUPABASE_SERVICE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_KEY')}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def supabase_url(path):
    return f"{os.getenv('SUPABASE_URL')}/rest/v1/{path}"

class ExpenseCreate(BaseModel):
    platform: str
    amount: int
    note: Optional[str] = ""

@router.get("/")
async def get_expenses():
    now = datetime.now()
    month_start = f"{now.year}-{now.month:02d}-01"
    async with httpx.AsyncClient() as client:
        r = await client.get(
            supabase_url(f"expenses?expense_date=gte.{month_start}&order=expense_date.desc"),
            headers=get_headers()
        )
        data = r.json()
    total = sum(e["amount"] for e in (data if isinstance(data, list) else []))
    return {"expenses": data, "total": total}

@router.post("/")
async def add_expense(expense: ExpenseCreate):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            supabase_url("expenses"),
            headers=get_headers(),
            json={
                "platform": expense.platform,
                "amount": expense.amount,
                "note": expense.note,
                "expense_date": datetime.now().strftime("%Y-%m-%d"),
            }
        )
        return r.json()[0] if r.status_code == 201 else r.json()

@router.delete("/{expense_id}")
async def delete_expense(expense_id: str):
    async with httpx.AsyncClient() as client:
        await client.delete(
            supabase_url(f"expenses?id=eq.{expense_id}"),
            headers=get_headers()
        )
    return {"success": True}