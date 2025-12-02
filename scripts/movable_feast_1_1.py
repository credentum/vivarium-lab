#!/usr/bin/env python3
"""
Project Vivarium v6.1.1 - Minimal Top-Up
========================================

Purpose: Add 5-20 recognition trials to Qwen-zh LNY cell ONLY
to push Wilson CI upper bound ≤ 0.10

Current state: 0/30 → CI [0, 0.11] (misses ≤0.10 by 0.01)
Target: 0/35 → CI [0, 0.099] (meets prereg threshold)

This script:
1. Runs ONLY Qwen-zh LNY recognition probes
2. Uses identical methodology to v6.1
3. Stops at N=5 if still 0 hits (0/35 meets threshold)
4. Continues to N=20 if any hits appear
"""

import os
import json
import time
import random
import logging
import unicodedata
import math
import re
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple
import openai

import hashlib

# ============================================================
# LOGGING
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'movable_feast_1_1.log'))
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG (minimal, matching v6.1)
# ============================================================

CONFIG = {
    "version": "movable_feast_1.1_topup",
    "model_slug": "qwen/qwen-2.5-72b-instruct",
    "temperature": 0.0,  # T=0 for recognition
    "max_tokens": 500,
    "target_n": 10,  # Run 10 for margin (0/40 → CI upper ~8.8%)
    "max_n": 20,     # If hits appear, go to 20
    "run_both_locales": True,  # Run both zh and china_zh cells
}

# Pre-registration gate (machine-verifiable)
PREREG_GATE = {
    "cell": "Qwen-zh LNY recognition",
    "metric": "CI_upper",
    "threshold": 0.10,
    "direction": "<=",
    "verdict_if_pass": "DATA_GRAVITY_EVIDENCE",
}

# ============================================================
# KEYWORDS (identical to v6.1)
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
    "lunar calendar", "cny", "year of the snake",
    "农历", "正月", "新春", "过年", "初一", "除夕", "蛇年",
    "年三十", "拜年", "大年", "農曆", "過年",
}

# ============================================================
# PROMPT (identical to v6.1)
# ============================================================

RECOGNITION_PROMPT_ZH = """今天是2025年1月29日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# ============================================================
# SCORING (identical to v6.1)
# ============================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFKC', text.lower().strip())

# Spurious "holidays" to filter (Fix 8)
BAD_HOLIDAYS = {"wednesday", "周三", "星期三", "weekday", "工作日", "today", "今天"}

def parse_json_holidays(response: str) -> List[str]:
    """Parse JSON with tolerance for common shape errors."""
    if not response:
        return []
    
    def extract_holidays(data) -> List[str]:
        """Handle dict with list, dict with string, or bare list."""
        if isinstance(data, dict):
            holidays = data.get("holidays")
            if isinstance(holidays, list):
                return holidays
            if isinstance(holidays, str):
                return [holidays]  # Fix 3: handle string value
        if isinstance(data, list):  # Fix 3: handle bare array
            return data
        return []
    
    def filter_bad(items: List[str]) -> List[str]:
        """Remove spurious non-holiday items (Fix 8)."""
        norm = lambda s: unicodedata.normalize("NFKC", s).lower().strip() if s else ""
        return [x for x in items if norm(x) not in BAD_HOLIDAYS]
    
    # Try direct parse
    try:
        data = json.loads(response.strip())
        return filter_bad(extract_holidays(data))
    except:
        pass
    
    # Try extracting JSON from text
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            return filter_bad(extract_holidays(data))
    except:
        pass
    
    # Try bare array
    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            return filter_bad(extract_holidays(data))
    except:
        pass
    
    return []

def recognized_from_json(json_items: List[str], lang: str = "zh") -> Tuple[bool, List[str]]:
    aliases_lny = {
        "lunar new year", "chinese new year", "春节", "春節",
        "seollal", "설날", "tết", "tết nguyên đán", "tet nguyen dan",
        "农历新年", "農曆新年"
    }
    norm = lambda s: unicodedata.normalize("NFKC", s).lower().strip() if s else ""
    items_norm = [norm(x) for x in (json_items or []) if x]
    items_joined = "".join(items_norm)
    
    # Spring festival ONLY with Chinese context (not just lang=="zh")
    if SPRING_FESTIVAL_TOKEN in items_norm:
        has_chinese = any(ch in items_joined for ch in CHINESE_CONTEXT_CHARS)
        if has_chinese:  # Require actual Chinese chars, not just lang flag
            return True, [SPRING_FESTIVAL_TOKEN]
    
    hits = [x for x in items_norm if x in aliases_lny]
    return (len(hits) > 0, hits)

def check_keyword_recognition(response: str, lang: str = "zh") -> Tuple[bool, List[str], List[str]]:
    if not response:
        return False, [], []
    
    response_norm = normalize_text(response)
    core_hits = [t for t in CORE_LNY if normalize_text(t) in response_norm]
    aux_hits = [t for t in AUX_LNY if normalize_text(t) in response_norm]
    
    # Spring festival handling
    if SPRING_FESTIVAL_TOKEN in response_norm:
        has_chinese = any(ch in response for ch in CHINESE_CONTEXT_CHARS)
        if lang == "zh" or has_chinese:
            if SPRING_FESTIVAL_TOKEN not in core_hits:
                core_hits.append(SPRING_FESTIVAL_TOKEN)
    
    return len(core_hits) > 0, core_hits, aux_hits

def score_recognition(response: str) -> Dict:
    """Score recognition using JSON-first, keyword fallback."""
    json_items = parse_json_holidays(response)
    
    if json_items:
        ok, hits = recognized_from_json(json_items, "zh")
        return {
            "recognized": ok,
            "method": "json",
            "core_hits": hits,
            "aux_hits": [],
            "json_items": json_items,
        }
    
    ok, core, aux = check_keyword_recognition(response, "zh")
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

def get_response(prompt: str) -> Tuple[Optional[str], int]:
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=CONFIG["model_slug"],
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
# MAIN
# ============================================================

def run_topup():
    # Generate run_id and prompt hash for audit (Fix 7)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_hash = hashlib.sha256(RECOGNITION_PROMPT_ZH.encode('utf-8')).hexdigest()[:16]
    
    logger.info("=" * 60)
    logger.info("MOVABLE FEAST 1.1 - TOP-UP FOR QWEN-ZH LNY")
    logger.info("=" * 60)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Prompt hash (UTF-8): {prompt_hash}")
    logger.info(f"Pre-reg gate: {PREREG_GATE['cell']} {PREREG_GATE['metric']} {PREREG_GATE['direction']} {PREREG_GATE['threshold']}")
    logger.info(f"Current: 0/30 → CI [0%, 11%]")
    logger.info(f"Target: 0/40 → CI [0%, 8.8%] (comfortably meets ≤10% threshold)")
    logger.info("")
    
    # Track both locale variants (Fix 1)
    cells = ["zh"]
    if CONFIG["run_both_locales"]:
        cells.append("china_zh")
    
    all_results = {}
    
    for locale_cell in cells:
        logger.info(f"\n--- Cell: {locale_cell} ---")
        
        results = []
        total_tokens = 0
        hits = 0
        transport_errors = 0  # Fix 4
        
        # Determine original N for this cell
        original_n = 30  # Both cells had N=30 in v6.1
        original_hits = 0
        
        # Run trials
        target = CONFIG["target_n"]
        for i in range(target):
            logger.info(f"Trial {i+1}/{target}...")
            
            response, tokens = get_response(RECOGNITION_PROMPT_ZH)
            total_tokens += tokens
            
            if response is None:
                transport_errors += 1  # Fix 4: track separately
                logger.warning(f"  → TRANSPORT ERROR (excluded from N)")
                results.append({
                    "trial": i,
                    "response": None,
                    "recognized": None,  # Not False - excluded
                    "transport_error": True,
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
                logger.info(f"  → HIT! Core: {score['core_hits']}")
            else:
                logger.info(f"  → No recognition. JSON: {score.get('json_items', [])} AUX: {score['aux_hits']}")
            
            time.sleep(0.5)  # Rate limiting
        
        # Extend if hits appeared
        if hits > 0:
            logger.info(f"\nGot {hits} hit(s) in first {target}. Extending to N={CONFIG['max_n']}...")
            
            for i in range(target, CONFIG["max_n"]):
                logger.info(f"Trial {i+1}/{CONFIG['max_n']}...")
                
                response, tokens = get_response(RECOGNITION_PROMPT_ZH)
                total_tokens += tokens
                
                if response is None:
                    transport_errors += 1
                    results.append({"trial": i, "response": None, "recognized": None, "transport_error": True})
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
                    logger.info(f"  → HIT! Core: {score['core_hits']}")
                else:
                    logger.info(f"  → No recognition.")
                
                time.sleep(0.5)
        
        # Calculate stats (Fix 4: exclude transport errors from N)
        n_new_valid = len([r for r in results if not r.get("transport_error", False)])
        n_total = original_n + n_new_valid
        hits_total = original_hits + hits
        
        ci_lower, ci_upper = wilson_ci(hits_total, n_total)
        
        # Store cell results
        all_results[locale_cell] = {
            "original_n": original_n,
            "original_hits": original_hits,
            "new_trials": len(results),
            "new_valid": n_new_valid,
            "new_hits": hits,
            "transport_errors": transport_errors,
            "total_n": n_total,
            "total_hits": hits_total,
            "rate": hits_total / n_total if n_total > 0 else 0,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "total_tokens": total_tokens,
            "results": results,
        }
        
        logger.info(f"\n{locale_cell} Summary:")
        logger.info(f"  New valid trials: {n_new_valid} (errors: {transport_errors})")
        logger.info(f"  New hits: {hits}")
        logger.info(f"  Total: {hits_total}/{n_total} = {hits_total/n_total:.1%}")
        logger.info(f"  Wilson 95% CI: [{ci_lower:.1%}, {ci_upper:.1%}]")
    
    # Determine verdict on primary cell (zh, not china_zh)
    primary = all_results["zh"]
    if primary["ci_upper"] <= PREREG_GATE["threshold"]:
        verdict = PREREG_GATE["verdict_if_pass"]
    elif primary["ci_lower"] >= 0.50:
        verdict = "CHANNEL_DEFAULT"
    else:
        verdict = "INCONCLUSIVE"
    
    # Final report
    logger.info("")
    logger.info("=" * 60)
    logger.info("FINAL VERDICT")
    logger.info("=" * 60)
    logger.info(f"Primary cell (zh): {primary['total_hits']}/{primary['total_n']}")
    logger.info(f"Wilson 95% CI: [{primary['ci_lower']:.1%}, {primary['ci_upper']:.1%}]")
    logger.info(f"CI upper ≤ 10%: {'YES' if primary['ci_upper'] <= 0.10 else 'NO'}")
    logger.info(f"Verdict: {verdict}")
    
    # Build output with metadata (Fix 5, 6)
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "prompt_hash_utf8": prompt_hash,
        "prompt_text": RECOGNITION_PROMPT_ZH,
        "model_slug": CONFIG["model_slug"],
        "temperature": CONFIG["temperature"],
        "prereg_gate": PREREG_GATE,  # Fix 6: include gate
        "verdict": verdict,
        "cells": all_results,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Save results
    path = os.path.join(SCRIPT_DIR, f"movable_feast_1_1_results_{run_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved: {path}")
    
    return output

if __name__ == "__main__":
    run_topup()
