from fastapi import APIRouter
from datetime import datetime, timedelta
import os
from supabase import create_client

router = APIRouter()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

@router.get("/history")
async def get_meal_history():
    since = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    data = supabase.from_("meal_plans").select("*").gte("planned_date", since).order("planned_date", desc=True).execute()
    return data.data

@router.get("/shopping")
async def get_shopping_list():
    week_start = datetime.now().strftime("%Y-%m-%d")
    data = supabase.from_("shopping_items").select("*").gte("week_start", week_start).execute()
    return data.data
