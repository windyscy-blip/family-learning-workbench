# -*- coding: utf-8 -*-
"""家庭学习工作台 · 本地高质量语音服务（Edge 神经语音）。

启动方式（本机运行一次即可，工作台会自动探测并优先使用）：
  C:/Users/sPark/.workbuddy/binaries/python/envs/default/Scripts/python.exe outputs/tts-server-workbench.py

接口：
  GET /health            -> {"ok":true,"engine":"edge-tts"}
  GET /tts?text=&lang=zh|en&rate=+0%&voice=  -> audio/mpeg
"""
import asyncio
from fastapi import FastAPI, Query
from fastapi.responses import Response
import edge_tts

APP = FastAPI(title="workbench-tts")


@APP.middleware("http")
async def cors_pna(request, call_next):
    """CORS + Private Network Access headers so browsers on any origin may reach loopback."""
    if request.method == "OPTIONS":
        resp = Response(status_code=204)
    else:
        resp = await call_next(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    resp.headers["Access-Control-Allow-Private-Network"] = "true"
    return resp

DEFAULT_VOICE = {"zh": "zh-CN-XiaoxiaoNeural", "en": "en-US-JennyNeural"}
CACHE = {}
CACHE_MAX = 300


@APP.get("/health")
def health():
    return {"ok": True, "engine": "edge-tts"}


@APP.get("/tts")
async def tts(
    text: str = Query(...),
    lang: str = Query("zh"),
    rate: str = Query("+0%"),
    voice: str = Query(""),
):
    key = (text, lang, rate, voice)
    if key in CACHE:
        return Response(CACHE[key], media_type="audio/mpeg", headers={"Cache-Control": "no-store"})
    v = voice or DEFAULT_VOICE.get(lang, DEFAULT_VOICE["zh"])
    comm = edge_tts.Communicate(text, v, rate=rate)
    buf = bytearray()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    data = bytes(buf)
    if not data:
        return Response(b"", status_code=502)
    if len(CACHE) >= CACHE_MAX:
        CACHE.clear()
    CACHE[key] = data
    return Response(data, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(APP, host="127.0.0.1", port=8766)
