from fastapi import APIRouter
from datetime import datetime, timedelta
import os
import httpx

router = APIRouter()

def get_headers():
    return {
        "apikey": os.getenv("SUPABASE_SERVICE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_KEY')}",
        "Content-Type": "application/json",
    }

def supabase_url(path):
    return f"{os.getenv('SUPABASE_URL')}/rest/v1/{path}"

@router.get("/history")
async def get_meal_history():
    since = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    async with httpx.AsyncClient() as client:
        r = await client.get(
            supabase_url(f"meal_plans?planned_date=gte.{since}&order=planned_date.desc"),
            headers=get_headers()
        )
        return r.json()

@router.get("/shopping")
async def get_shopping_list():
    week_start = datetime.now().strftime("%Y-%m-%d")
    async with httpx.AsyncClient() as client:
        r = await client.get(
            supabase_url(f"shopping_items?week_start=gte.{week_start}"),
            headers=get_headers()
        )
        return r.json()