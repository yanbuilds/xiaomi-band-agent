"""Minimal self-hosted webhook endpoint for a Grok runner.

This is an integration example, not a model client.  Put the actual Grok call
behind ``analyse`` and keep the webhook secret in the server environment.
"""
from __future__ import annotations

import os
import time
from fastapi import FastAPI, Header, HTTPException, Request

from agent_client import verify_signature

app = FastAPI(title="Band Agent Grok webhook example")
SECRET = os.environ.get("BAND_WEBHOOK_SECRET", "")


@app.post("/analyse")
async def analyse(request: Request,
                  x_band_agent_timestamp: str | None = Header(default=None),
                  x_band_agent_signature: str | None = Header(default=None)):
    if not SECRET or not x_band_agent_timestamp or not x_band_agent_signature:
        raise HTTPException(503, "webhook secret is not configured")
    body = await request.body()
    if not verify_signature(body, SECRET, x_band_agent_timestamp,
                            x_band_agent_signature, now=int(time.time())):
        raise HTTPException(401, "invalid or expired signature")
    # Replace this deterministic placeholder with the user's Grok bot call.
    # The input contains parsed health data only; never forward Bluetooth keys.
    return {
        "title": "睡眠回顾",
        "text": "已收到睡眠数据，请选择下一步。",
        "options": [
            {"id": "details", "text": "查看详情"},
            {"id": "reminder", "text": "设置提醒"},
        ],
        "expires_at": int(time.time()) + 600,
    }
