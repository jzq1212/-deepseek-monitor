"""DeepSeek / OpenRouter API 客户端 — 查询余额和用量"""

import requests
from datetime import date, datetime, timedelta

DEEPSEEK_BASE = "https://api.deepseek.com"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def get_balance(api_key: str) -> dict | None:
    """查询账户余额"""
    try:
        resp = requests.get(
            f"{DEEPSEEK_BASE}/user/balance",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        info = data["balance_infos"][0]
        return {
            "available": data.get("is_available", True),
            "currency": info.get("currency", "CNY"),
            "total": float(info.get("total_balance", 0)),
            "granted": float(info.get("granted_balance", 0)),
            "topped_up": float(info.get("topped_up_balance", 0)),
        }
    except Exception as e:
        print(f"[API] 余额查询失败: {e}")
        return None


def get_usage(api_key: str, start_date: str, end_date: str) -> dict | None:
    """查询指定日期范围的用量，按模型汇总返回"""
    try:
        resp = requests.get(
            f"{DEEPSEEK_BASE}/v1/usage",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            params={"start_date": start_date, "end_date": end_date},
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()

        # 按模型汇总
        model_stats: dict[str, dict] = {}
        total_prompt = 0
        total_completion = 0
        today_prompt = 0
        today_completion = 0
        today_str = date.today().isoformat()

        records = raw.get("data", [])
        daily: dict[str, int] = {}
        for r in records:
            m = r.get("model", "unknown")
            pt = r.get("prompt_tokens", 0) or 0
            ct = r.get("completion_tokens", 0) or 0
            ts = r.get("timestamp", "")
            day = ts[:10] if ts else ""

            if m not in model_stats:
                model_stats[m] = {"prompt_tokens": 0, "completion_tokens": 0}
            model_stats[m]["prompt_tokens"] += pt
            model_stats[m]["completion_tokens"] += ct
            total_prompt += pt
            total_completion += ct

            if day == today_str:
                today_prompt += pt
                today_completion += ct

            if day:
                daily[day] = daily.get(day, 0) + pt + ct

        # 近7天每日汇总
        last_7_days = {}
        for i in range(6, -1, -1):
            d = (date.today() - timedelta(days=i)).isoformat()
            last_7_days[d] = daily.get(d, 0)

        return {
            "models": model_stats,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "today_prompt_tokens": today_prompt,
            "today_completion_tokens": today_completion,
            "today_tokens": today_prompt + today_completion,
            "daily": last_7_days,
            "raw_count": len(records),
        }
    except Exception as e:
        print(f"[API] 用量查询失败: {e}")
        return None


def estimate_cost(model_stats: dict) -> dict:
    """根据模型用量估算费用（CNY/百万token）"""
    # DeepSeek 当前定价 (2025-2026)
    PRICING = {
        "deepseek-v4-flash": {"input": 2.0, "output": 8.0, "cache_hit": 0.5},
        "deepseek-reasoner": {"input": 4.0, "output": 16.0, "cache_hit": 1.0},
    }

    result = {}
    for model, stats in model_stats.items():
        price = PRICING.get(model)
        if not price:
            # fallback: 按 v4-flash 价格
            price = PRICING["deepseek-v4-flash"]
        prompt_cost = (stats["prompt_tokens"] / 1_000_000) * price["input"]
        completion_cost = (stats["completion_tokens"] / 1_000_000) * price["output"]
        result[model] = {
            "prompt_cost": round(prompt_cost, 4),
            "completion_cost": round(completion_cost, 4),
            "total_cost": round(prompt_cost + completion_cost, 4),
        }
    return result


def get_openrouter_balance(api_key: str) -> dict | None:
    """查询 OpenRouter 账户余额 (GET /api/v1/key)"""
    try:
        resp = requests.get(
            f"{OPENROUTER_BASE}/key",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        limit = data.get("limit") or 0
        usage = data.get("usage") or 0
        remaining = data.get("limit_remaining") or 0
        return {
            "label": data.get("label", ""),
            "limit": float(limit),
            "usage": float(usage),
            "limit_remaining": float(remaining),
            "is_free_tier": data.get("is_free_tier", False),
            "disabled": data.get("disabled", False),
        }
    except Exception as e:
        print(f"[API] OpenRouter 余额查询失败: {e}")
        return None
