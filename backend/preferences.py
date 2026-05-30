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

class PreferenceCreate(BaseModel):
    type: str          # avoid | favourite | replace
    item: str
    replace_with: Optional[str] = ""
    reason: Optional[str] = ""

@router.get("/")
async def get_preferences():
    async with httpx.AsyncClient() as client:
        r = await client.get(
            supabase_url("preferences?order=created_at.desc"),
            headers=get_headers()
        )
    data = r.json()
    return data if isinstance(data, list) else []

@router.post("/")
async def save_preference(pref: PreferenceCreate):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            supabase_url("preferences"),
            headers={**get_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
            json={
                "type": pref.type,
                "item": pref.item.lower().strip(),
                "replace_with": pref.replace_with.lower().strip() if pref.replace_with else "",
                "reason": pref.reason,
                "created_at": datetime.now().isoformat()
            }
        )
    return r.json()[0] if r.status_code == 201 else r.json()

@router.delete("/{pref_id}")
async def delete_preference(pref_id: str):
    async with httpx.AsyncClient() as client:
        await client.delete(
            supabase_url(f"preferences?id=eq.{pref_id}"),
            headers=get_headers()
        )
    return {"success": True}