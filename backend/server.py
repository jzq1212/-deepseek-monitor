"""DeepSeek Monitor - FastAPI 后端"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# PyInstaller --noconsole 模式下 stderr/stdout 为 None，uvicorn 会崩溃
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


def get_static_dir() -> Path:
    """获取前端静态文件目录（支持 PyInstaller 打包）"""
    # PyInstaller 打包后资源在 sys._MEIPASS
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent
    return base / "frontend" / "dist"

from api import get_balance as _get_balance
from config import (
    load_keys, save_keys, add_key, delete_key,
    get_active_key_index, set_active_key_index,
)

app = FastAPI(title="DeepSeek Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORY_DIR = Path.home() / ".deepseek-monitor" / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

# DeepSeek 定价 (CNY / 百万 Token)
PRICING = {
    "deepseek-v4-flash": {
        "name": "V4 Flash",
        "desc": "通用对话",
        "input": 1.0,
        "output": 2.0,
        "cache_hit": 0.02,
    },
    "deepseek-v4-pro": {
        "name": "V4 Pro",
        "desc": "深度推理",
        "input": 3.0,
        "output": 6.0,
        "cache_hit": 0.025,
    },
}


# ── 模型 ────────────────────────────────────
class KeyAddRequest(BaseModel):
    name: str
    api_key: str


class ActiveKeyRequest(BaseModel):
    index: int


# ── 历史管理 ────────────────────────────────
def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


def load_history(key_name: str) -> list[dict]:
    fpath = HISTORY_DIR / f"{_safe_name(key_name)}.json"
    if not fpath.exists():
        return []
    try:
        with open(fpath) as f:
            return json.load(f)
    except Exception:
        return []


def save_history(key_name: str, history: list[dict]):
    fpath = HISTORY_DIR / f"{_safe_name(key_name)}.json"
    with open(fpath, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def record_balance(key_name: str, balance: dict):
    history = load_history(key_name)
    today = date.today().isoformat()
    total = balance.get("total", 0)
    if history and history[-1].get("date") == today:
        history[-1] = {
            "date": today, "total": total,
            "topped_up": balance.get("topped_up", 0),
            "granted": balance.get("granted", 0),
        }
    else:
        history.append({
            "date": today, "total": total,
            "topped_up": balance.get("topped_up", 0),
            "granted": balance.get("granted", 0),
        })
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    history = [h for h in history if h["date"] >= cutoff]
    save_history(key_name, history)


def compute_daily_cost(history: list[dict]) -> dict:
    result = {}
    for i in range(1, len(history)):
        prev = history[i - 1]["total"]
        curr = history[i]["total"]
        day = history[i]["date"]
        delta = prev - curr
        if delta > 0:
            result[day] = round(delta, 4)
    return result


# ── API 路由 ────────────────────────────────
@app.get("/api/balance")
def api_balance():
    """查询当前选中 Key 的余额"""
    keys = load_keys()
    if not keys:
        raise HTTPException(400, "请先添加 API Key")
    idx = get_active_key_index()
    if idx >= len(keys):
        idx = 0
    key = keys[idx]
    bal = _get_balance(key["api_key"])
    if bal is None:
        raise HTTPException(502, "查询余额失败，请检查 API Key 或网络")

    record_balance(key["name"], bal)
    history = load_history(key["name"])
    daily_cost = compute_daily_cost(history)

    return {
        "key_name": key["name"],
        "balance": bal,
        "history": history[-14:],
        "daily_cost": daily_cost,
        "today_cost": daily_cost.get(date.today().isoformat(), 0),
    }


class HistoryAddRequest(BaseModel):
    date: str  # YYYY-MM-DD
    total: float
    topped_up: float = 0.0
    granted: float = 0.0


@app.get("/api/history")
def api_history():
    """获取余额历史"""
    keys = load_keys()
    if not keys:
        return {"history": [], "daily_cost": {}}
    idx = get_active_key_index()
    if idx >= len(keys):
        idx = 0
    key = keys[idx]
    history = load_history(key["name"])
    daily_cost = compute_daily_cost(history)
    return {"history": history[-14:], "daily_cost": daily_cost}


@app.post("/api/history")
def api_add_history(req: HistoryAddRequest):
    """手动添加历史余额记录"""
    keys = load_keys()
    if not keys:
        raise HTTPException(400, "请先添加 API Key")
    idx = get_active_key_index()
    if idx >= len(keys):
        idx = 0
    key = keys[idx]
    history = load_history(key["name"])

    entry = {
        "date": req.date,
        "total": req.total,
        "topped_up": req.topped_up,
        "granted": req.granted,
    }

    # 插入到正确位置（保持日期升序）
    history.append(entry)
    history.sort(key=lambda h: h["date"])
    # 同日期去重，保留最后一条
    seen = {}
    for h in history:
        seen[h["date"]] = h
    history = list(seen.values())
    history.sort(key=lambda h: h["date"])

    save_history(key["name"], history)
    daily_cost = compute_daily_cost(history)
    return {"history": history[-14:], "daily_cost": daily_cost}


class HistoryDeleteRequest(BaseModel):
    date: str


@app.post("/api/history/delete")
def api_delete_history(req: HistoryDeleteRequest):
    """删除某一天的余额记录"""
    keys = load_keys()
    if not keys:
        raise HTTPException(400, "请先添加 API Key")
    idx = get_active_key_index()
    if idx >= len(keys):
        idx = 0
    key = keys[idx]
    history = load_history(key["name"])
    history = [h for h in history if h["date"] != req.date]
    save_history(key["name"], history)
    return {"ok": True}


@app.get("/api/pricing")
def api_pricing():
    """获取模型定价"""
    return {"models": PRICING, "night_discount": True}


@app.get("/api/keys")
def api_list_keys():
    """列出所有 Key（不返回实际 Key 值）"""
    keys = load_keys()
    active = get_active_key_index()
    return {
        "keys": [{"name": k["name"], "masked": k["api_key"][:6] + "***"} for k in keys],
        "active_index": active,
    }


@app.post("/api/keys")
def api_add_key(req: KeyAddRequest):
    if not req.name.strip():
        raise HTTPException(400, "名称不能为空")
    if not req.api_key.startswith("sk-"):
        raise HTTPException(400, "API Key 格式不正确")
    add_key(req.name.strip(), req.api_key.strip())
    return {"ok": True}


@app.delete("/api/keys/{name}")
def api_delete_key(name: str):
    # 删除历史文件
    hpath = HISTORY_DIR / f"{_safe_name(name)}.json"
    if hpath.exists():
        hpath.unlink()
    delete_key(name)
    return {"ok": True}


@app.put("/api/keys/active")
def api_set_active(req: ActiveKeyRequest):
    set_active_key_index(req.index)
    return {"ok": True}


# ── 静态文件（生产模式）──────────────────────
STATIC_DIR = get_static_dir()
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
else:
    print(f"[WARN] Static dir not found: {STATIC_DIR}")


# ── 入口 ────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    import threading
    import socket
    import webview

    # 自动找可用端口
    port = 8765
    for p in range(8765, 8780):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", p))
            s.close()
            port = p
            break
        except OSError:
            continue

    url = f"http://127.0.0.1:{port}"

    # 后台启动 uvicorn
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=port,
                    log_level="error", log_config=None)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 等待服务器就绪
    import time
    for _ in range(20):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", port))
            s.close()
            break
        except Exception:
            time.sleep(0.3)

    # 原生窗口
    webview.create_window(
        title="DeepSeek 用量监控",
        url=url,
        width=480,
        height=640,
        resizable=True,
        easy_drag=False,
        background_color="#0a0e27",
    )
    webview.start()
