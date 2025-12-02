#!/usr/bin/env python3
"""
Project Vivarium v6.1.3 - Top-Up Underpowered Cells
===================================================

Finish the v6.1.2 robustness cells to N=40 each:
- Qwen-72B, LNY-2024: currently 0/20, need +20 → 0/40
- Qwen-7B, LNY-2025: currently 0/20, need +20 → 0/40

At N=40 with 0 hits: Wilson CI [0%, 8.76%] ≤ 10% threshold

Also adds the date-parsing sanity check to rule out "didn't parse the date".
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
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'results', 'movable_feast_1_3.log'))
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================

CONFIG = {
    "version": "movable_feast_1.3_topup",
    "temperature": 0.0,
    "max_tokens": 500,
    "topup_trials": 20,  # Add 20 to reach N=40
}

MODELS = {
    "qwen_72b": "qwen/qwen-2.5-72b-instruct",
    "qwen_7b": "qwen/qwen-2.5-7b-instruct",
}

# ============================================================
# KEYWORDS (identical to v6.1.1/v6.1.2)
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
# PROMPTS
# ============================================================

PROMPT_LNY_2024 = """今天是2024年2月10日，星期六。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

PROMPT_LNY_2025 = """今天是2025年1月29日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# Sanity check: Can the model parse the date correctly?
PROMPT_DATE_PARSE_2025 = """今天是2025年1月29日。

请回答以下问题，只用JSON格式：
{"weekday": "星期X", "lunar_date": "农历X月X日", "solar_term": "节气名称或null"}

如果不知道，填 null。"""

PROMPT_DATE_PARSE_2024 = """今天是2024年2月10日。

请回答以下问题，只用JSON格式：
{"weekday": "星期X", "lunar_date": "农历X月X日", "solar_term": "节气名称或null"}

如果不知道，填 null。"""

# ============================================================
# SCORING (identical to v6.1.2)
# ============================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFKC', text.lower().strip())

def parse_json_holidays(response: str) -> Tuple[List[str], str]:
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

def run_recognition_topup(cell_id: str, model_slug: str, prompt: str, 
                          original_n: int, original_hits: int) -> Dict:
    """Top up a recognition cell."""
    logger.info(f"\n{'='*50}")
    logger.info(f"TOP-UP: {cell_id}")
    logger.info(f"Original: {original_hits}/{original_n}")
    logger.info(f"Adding: {CONFIG['topup_trials']} trials")
    logger.info(f"{'='*50}")
    
    results = []
    total_tokens = 0
    hits = 0
    transport_errors = 0
    
    for i in range(CONFIG["topup_trials"]):
        logger.info(f"Trial {i+1}/{CONFIG['topup_trials']}...")
        
        response, tokens = get_response(prompt, model_slug)
        total_tokens += tokens
        
        if response is None:
            transport_errors += 1
            logger.warning(f"  → TRANSPORT ERROR")
            results.append({"trial": i, "response": None, "transport_error": True})
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
            logger.info(f"  → No recognition ({score['method']})")
        
        time.sleep(0.5)
    
    n_new_valid = CONFIG["topup_trials"] - transport_errors
    n_total = original_n + n_new_valid
    hits_total = original_hits + hits
    
    ci_lower, ci_upper = wilson_ci(hits_total, n_total)
    
    logger.info(f"\nResult: {hits_total}/{n_total} = {hits_total/n_total:.1%}")
    logger.info(f"Wilson 95% CI: [{ci_lower:.1%}, {ci_upper:.1%}]")
    logger.info(f"CI_upper ≤ 10%: {'YES ✓' if ci_upper <= 0.10 else 'NO'}")
    
    return {
        "cell_id": cell_id,
        "original_n": original_n,
        "original_hits": original_hits,
        "new_trials": CONFIG["topup_trials"],
        "new_valid": n_new_valid,
        "new_hits": hits,
        "transport_errors": transport_errors,
        "total_n": n_total,
        "total_hits": hits_total,
        "rate": hits_total / n_total,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "gate_passed": ci_upper <= 0.10,
        "total_tokens": total_tokens,
        "results": results,
    }

def run_date_parse_sanity(model_slug: str, prompt: str, date_label: str) -> Dict:
    """Run date parsing sanity check."""
    logger.info(f"\n{'='*50}")
    logger.info(f"DATE PARSE SANITY: {date_label}")
    logger.info(f"{'='*50}")
    
    response, tokens = get_response(prompt, model_slug)
    
    if response is None:
        logger.warning("Transport error on sanity check")
        return {"date_label": date_label, "response": None, "error": True}
    
    logger.info(f"Response: {response}")
    
    # Try to parse
    parsed = None
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(response[start:end])
    except:
        pass
    
    return {
        "date_label": date_label,
        "prompt": prompt,
        "response": response,
        "parsed": parsed,
        "tokens": tokens,
    }

def run_all():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 60)
    logger.info("MOVABLE FEAST 1.3 - TOP-UP UNDERPOWERED CELLS")
    logger.info("=" * 60)
    logger.info(f"Run ID: {run_id}")
    logger.info("")
    
    all_results = {}
    total_tokens = 0
    
    # Top-up 1: Qwen-72B, LNY-2024 (was 0/20, need +20)
    cell1 = run_recognition_topup(
        cell_id="qwen_72b_lny_2024",
        model_slug=MODELS["qwen_72b"],
        prompt=PROMPT_LNY_2024,
        original_n=20,
        original_hits=0,
    )
    all_results["qwen_72b_lny_2024"] = cell1
    total_tokens += cell1["total_tokens"]
    
    # Top-up 2: Qwen-7B, LNY-2025 (was 0/20, need +20)
    cell2 = run_recognition_topup(
        cell_id="qwen_7b_lny_2025",
        model_slug=MODELS["qwen_7b"],
        prompt=PROMPT_LNY_2025,
        original_n=20,
        original_hits=0,
    )
    all_results["qwen_7b_lny_2025"] = cell2
    total_tokens += cell2["total_tokens"]
    
    # Sanity checks: Can the models parse the dates?
    logger.info("\n" + "="*60)
    logger.info("DATE PARSING SANITY CHECKS")
    logger.info("="*60)
    
    sanity_checks = []
    
    sanity1 = run_date_parse_sanity(
        model_slug=MODELS["qwen_72b"],
        prompt=PROMPT_DATE_PARSE_2025,
        date_label="qwen_72b_parse_2025"
    )
    sanity_checks.append(sanity1)
    total_tokens += sanity1.get("tokens", 0)
    
    sanity2 = run_date_parse_sanity(
        model_slug=MODELS["qwen_72b"],
        prompt=PROMPT_DATE_PARSE_2024,
        date_label="qwen_72b_parse_2024"
    )
    sanity_checks.append(sanity2)
    total_tokens += sanity2.get("tokens", 0)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("FINAL SUMMARY")
    logger.info("="*60)
    
    all_passed = True
    for cell_id, cell in all_results.items():
        status = "✓ PASS" if cell["gate_passed"] else "✗ FAIL"
        logger.info(f"{cell_id}: {cell['total_hits']}/{cell['total_n']} "
                   f"CI [{cell['ci_lower']:.1%}, {cell['ci_upper']:.1%}] {status}")
        if not cell["gate_passed"]:
            all_passed = False
    
    logger.info(f"\nAll gates passed: {'YES' if all_passed else 'NO'}")
    logger.info(f"Total tokens: {total_tokens:,}")
    
    # Build output
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "purpose": "Top up underpowered cells to N=40 for CI ≤ 10%",
        "cells": all_results,
        "sanity_checks": sanity_checks,
        "all_gates_passed": all_passed,
        "total_tokens": total_tokens,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Save
    path = os.path.join(SCRIPT_DIR, 'results', f"movable_feast_1_3_results_{run_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved: {path}")

    return output

if __name__ == "__main__":
    run_all()
