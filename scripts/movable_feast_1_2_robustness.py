#!/usr/bin/env python3
"""
Project Vivarium v6.1.2 - Robustness Confirmations
==================================================

Two targeted tests to strengthen the Data Gravity finding:

1. DATE VARIATION: Test Qwen-zh on a different LNY date (2024-02-10)
   - Shows the effect isn't date-specific
   - N=20 trials

2. SECOND CN-ORIGIN MODEL: Test Baichuan or smaller Qwen on 2025-01-29
   - Shows the effect isn't Qwen-specific
   - N=20 trials

Both use identical methodology to v6.1/v6.1.1.
"""

import os
import json
import time
import hashlib
import logging
import unicodedata
import math
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import openai

# ============================================================
# LOGGING
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'results', 'movable_feast_1_2.log'))
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================

CONFIG = {
    "version": "movable_feast_1.2_robustness",
    "temperature": 0.0,
    "max_tokens": 500,
    "trials_per_cell": 20,
}

# Models to test
MODELS = {
    "qwen_72b": "qwen/qwen-2.5-72b-instruct",
    "qwen_7b": "qwen/qwen-2.5-7b-instruct",  # Smaller Qwen
    # Alternative CN models via OpenRouter:
    # "baichuan": "baichuan-inc/baichuan2-13b-chat",
    # "yi": "01-ai/yi-34b-chat",
}

# LNY dates to test
LNY_DATES = {
    "2025": ("2025年1月29日", "星期三"),  # Original
    "2024": ("2024年2月10日", "星期六"),  # Previous year
}

# ============================================================
# KEYWORDS (identical to v6.1.1)
# ============================================================

CORE_LNY = {
    "lunar new year", "chinese new year",
    "春节", "春節", "农历新年", "農曆新年",
    "seollal", "설날",
    "tết", "tết nguyên đán", "tet nguyen dan",
}

SPRING_FESTIVAL_TOKEN = "spring festival"
CHINESE_CONTEXT_CHARS = set("春节春節农历農曆中国中國华人華人")

AUX_LNY = {
    "lunar calendar", "cny", "year of the snake", "year of the dragon",
    "农历", "正月", "新春", "过年", "初一", "除夕", "蛇年", "龙年",
    "年三十", "拜年", "大年", "農曆", "過年",
}

BAD_HOLIDAYS = {"wednesday", "saturday", "周三", "周六", "星期三", "星期六", 
                "weekday", "工作日", "today", "今天"}

# ============================================================
# PROMPT TEMPLATE
# ============================================================

def make_prompt_zh(date_str: str, weekday_str: str) -> str:
    return f"""今天是{date_str}，{weekday_str}。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{{"holidays": ["节日名称1", "节日名称2"]}}

如果没有节日，请返回：{{"holidays": []}}"""

# ============================================================
# SCORING (identical to v6.1.1)
# ============================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFKC', text.lower().strip())

def parse_json_holidays(response: str) -> Tuple[List[str], str]:
    """Returns (items, method) where method is 'json', 'json_empty', or 'none'."""
    if not response:
        return [], "none"
    
    def extract_holidays(data) -> List[str]:
        if isinstance(data, dict):
            holidays = data.get("holidays")
            if isinstance(holidays, list):
                return holidays
            if isinstance(holidays, str):
                return [holidays]
        if isinstance(data, list):
            return data
        return []
    
    def filter_bad(items: List[str]) -> List[str]:
        norm = lambda s: unicodedata.normalize("NFKC", s).lower().strip() if s else ""
        return [x for x in items if norm(x) not in BAD_HOLIDAYS]
    
    # Try direct parse
    for attempt in [
        lambda: json.loads(response.strip()),
        lambda: json.loads(response[response.find("{"):response.rfind("}")+1]) if "{" in response else None,
        lambda: json.loads(response[response.find("["):response.rfind("]")+1]) if "[" in response else None,
    ]:
        try:
            data = attempt()
            if data is not None:
                items = filter_bad(extract_holidays(data))
                method = "json" if items else "json_empty"
                return items, method
        except:
            pass
    
    return [], "none"

def recognized_from_json(json_items: List[str]) -> Tuple[bool, List[str]]:
    aliases_lny = {
        "lunar new year", "chinese new year", "春节", "春節",
        "seollal", "설날", "tết", "tết nguyên đán", "tet nguyen dan",
        "农历新年", "農曆新年"
    }
    norm = lambda s: unicodedata.normalize("NFKC", s).lower().strip() if s else ""
    items_norm = [norm(x) for x in (json_items or []) if x]
    items_joined = "".join(items_norm)
    
    # Spring festival only with Chinese context
    if SPRING_FESTIVAL_TOKEN in items_norm:
        has_chinese = any(ch in items_joined for ch in CHINESE_CONTEXT_CHARS)
        if has_chinese:
            return True, [SPRING_FESTIVAL_TOKEN]
    
    hits = [x for x in items_norm if x in aliases_lny]
    return (len(hits) > 0, hits)

def check_keyword_recognition(response: str) -> Tuple[bool, List[str], List[str]]:
    if not response:
        return False, [], []
    
    response_norm = normalize_text(response)
    core_hits = [t for t in CORE_LNY if normalize_text(t) in response_norm]
    aux_hits = [t for t in AUX_LNY if normalize_text(t) in response_norm]
    
    if SPRING_FESTIVAL_TOKEN in response_norm:
        has_chinese = any(ch in response for ch in CHINESE_CONTEXT_CHARS)
        if has_chinese and SPRING_FESTIVAL_TOKEN not in core_hits:
            core_hits.append(SPRING_FESTIVAL_TOKEN)
    
    return len(core_hits) > 0, core_hits, aux_hits

def score_recognition(response: str) -> Dict:
    json_items, json_method = parse_json_holidays(response)
    
    if json_method in ("json", "json_empty"):
        if json_items:
            ok, hits = recognized_from_json(json_items)
            return {
                "recognized": ok,
                "method": "json",
                "core_hits": hits,
                "aux_hits": [],
                "json_items": json_items,
            }
        else:
            # JSON parsed but empty - still check keywords as fallback
            ok, core, aux = check_keyword_recognition(response)
            return {
                "recognized": ok,
                "method": "json_empty" if not ok else "keyword",
                "core_hits": core,
                "aux_hits": aux,
                "json_items": [],
            }
    
    ok, core, aux = check_keyword_recognition(response)
    return {
        "recognized": ok,
        "method": "keyword",
        "core_hits": core,
        "aux_hits": aux,
        "json_items": [],
    }

def wilson_ci(successes: int, n: int) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    z = 1.96
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = z * math.sqrt((p*(1-p) + z**2/(4*n)) / n) / denom
    return (max(0, center - margin), min(1, center + margin))

# ============================================================
# API
# ============================================================

_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        _client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    return _client

def get_response(prompt: str, model_slug: str) -> Tuple[Optional[str], int]:
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=model_slug,
            messages=[{"role": "user", "content": prompt}],
            temperature=CONFIG["temperature"],
            max_tokens=CONFIG["max_tokens"],
        )
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        return text, tokens
    except Exception as e:
        logger.error(f"API error: {e}")
        return None, 0

# ============================================================
# TEST RUNNERS
# ============================================================

def run_cell(model_key: str, model_slug: str, date_key: str, prompt: str, n_trials: int) -> Dict:
    """Run a single test cell."""
    cell_id = f"{model_key}_{date_key}"
    logger.info(f"\n{'='*50}")
    logger.info(f"Cell: {cell_id}")
    logger.info(f"Model: {model_slug}")
    logger.info(f"Date: {date_key}")
    logger.info(f"Trials: {n_trials}")
    logger.info(f"{'='*50}")
    
    results = []
    total_tokens = 0
    hits = 0
    transport_errors = 0
    
    for i in range(n_trials):
        logger.info(f"Trial {i+1}/{n_trials}...")
        
        response, tokens = get_response(prompt, model_slug)
        total_tokens += tokens
        
        if response is None:
            transport_errors += 1
            logger.warning(f"  → TRANSPORT ERROR")
            results.append({
                "trial": i,
                "response": None,
                "transport_error": True,
                "recognized": None,
            })
            continue
        
        score = score_recognition(response)
        results.append({
            "trial": i,
            "response": response,
            "transport_error": False,
            **score,
        })
        
        if score["recognized"]:
            hits += 1
            logger.info(f"  → HIT! {score['core_hits']}")
        else:
            aux_str = f" AUX: {score['aux_hits']}" if score['aux_hits'] else ""
            logger.info(f"  → No recognition ({score['method']}){aux_str}")
        
        time.sleep(0.5)
    
    n_valid = n_trials - transport_errors
    ci_lower, ci_upper = wilson_ci(hits, n_valid) if n_valid > 0 else (0, 1)
    
    return {
        "cell_id": cell_id,
        "model_key": model_key,
        "model_slug": model_slug,
        "date_key": date_key,
        "prompt": prompt,
        "n_trials": n_trials,
        "n_valid": n_valid,
        "transport_errors": transport_errors,
        "hits": hits,
        "rate": hits / n_valid if n_valid > 0 else 0,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "total_tokens": total_tokens,
        "results": results,
    }

def run_all():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 60)
    logger.info("MOVABLE FEAST 1.2 - ROBUSTNESS CONFIRMATIONS")
    logger.info("=" * 60)
    logger.info(f"Run ID: {run_id}")
    logger.info("")
    logger.info("Test 1: Date variation (Qwen-72B on 2024 LNY)")
    logger.info("Test 2: Model variation (Qwen-7B on 2025 LNY)")
    logger.info("")
    
    all_cells = {}
    total_tokens = 0
    
    # Test 1: Different date with same model
    logger.info("\n" + "="*60)
    logger.info("TEST 1: DATE VARIATION")
    logger.info("="*60)
    
    date_2024 = LNY_DATES["2024"]
    prompt_2024 = make_prompt_zh(date_2024[0], date_2024[1])
    
    cell = run_cell(
        model_key="qwen_72b",
        model_slug=MODELS["qwen_72b"],
        date_key="lny_2024",
        prompt=prompt_2024,
        n_trials=CONFIG["trials_per_cell"]
    )
    all_cells["qwen_72b_lny_2024"] = cell
    total_tokens += cell["total_tokens"]
    
    # Test 2: Different model with same date
    logger.info("\n" + "="*60)
    logger.info("TEST 2: MODEL VARIATION")
    logger.info("="*60)
    
    date_2025 = LNY_DATES["2025"]
    prompt_2025 = make_prompt_zh(date_2025[0], date_2025[1])
    
    cell = run_cell(
        model_key="qwen_7b",
        model_slug=MODELS["qwen_7b"],
        date_key="lny_2025",
        prompt=prompt_2025,
        n_trials=CONFIG["trials_per_cell"]
    )
    all_cells["qwen_7b_lny_2025"] = cell
    total_tokens += cell["total_tokens"]
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    
    for cell_id, cell in all_cells.items():
        logger.info(f"\n{cell_id}:")
        logger.info(f"  {cell['hits']}/{cell['n_valid']} = {cell['rate']:.1%}")
        logger.info(f"  Wilson 95% CI: [{cell['ci_lower']:.1%}, {cell['ci_upper']:.1%}]")
        logger.info(f"  CI_upper ≤ 10%: {'YES' if cell['ci_upper'] <= 0.10 else 'NO'}")
    
    logger.info(f"\nTotal tokens: {total_tokens:,}")
    
    # Build output
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "purpose": "Robustness confirmations for Data Gravity finding",
        "tests": {
            "date_variation": {
                "description": "Same model (Qwen-72B), different LNY date (2024-02-10)",
                "hypothesis": "If effect is date-specific, recognition should differ",
                "cell": "qwen_72b_lny_2024",
            },
            "model_variation": {
                "description": "Different model (Qwen-7B), same LNY date (2025-01-29)",
                "hypothesis": "If effect is model-specific, recognition should differ",
                "cell": "qwen_7b_lny_2025",
            },
        },
        "cells": all_cells,
        "total_tokens": total_tokens,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Save
    path = os.path.join(SCRIPT_DIR, 'results', f"movable_feast_1_2_results_{run_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved: {path}")

    return output

if __name__ == "__main__":
    run_all()
