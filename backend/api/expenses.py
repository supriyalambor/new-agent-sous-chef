from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
from supabase import create_client

router = APIRouter()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

class ExpenseCreate(BaseModel):
    platform: str
    amount: int
    note: Optional[str] = ""

@router.get("/")
async def get_expenses():
    now = datetime.now()
    month_start = f"{now.year}-{now.month:02d}-01"
    data = supabase.from_("expenses").select("*").gte("expense_date", month_start).order("expense_date", desc=True).execute()
    total = sum(r["amount"] for r in (data.data or []))
    return {"expenses": data.data, "total": total}

@router.post("/")
async def add_expense(expense: ExpenseCreate):
    data = supabase.from_("expenses").insert({
        "platform": expense.platform,
        "amount": expense.amount,
        "note": expense.note,
        "expense_date": datetime.now().strftime("%Y-%m-%d"),
    }).select().execute()
    return data.data[0]

@router.delete("/{expense_id}")
async def delete_expense(expense_id: str):
    supabase.from_("expenses").delete().eq("id", expense_id).execute()
    return {"success": True}
