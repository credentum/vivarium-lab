#!/usr/bin/env python3
"""
Project Vivarium v6.1.4 - Llama-zh Top-Up
=========================================

Top up Llama-zh LNY recognition to N=40.

Current state from v6.1: 1/30 (3.3%), CI [0.6%, 17.2%]
Target: N=40 to tighten CI and determine convergence/divergence with Qwen

Outcomes:
- If 1/40 or fewer: CI upper ~12% - close to Qwen, suggests convergent effect
- If 2-3/40: CI upper ~15-20% - mild divergence, Llama slightly better
- If 4+/40: CI upper >20% - clear divergence, Llama recognizes LNY sometimes

Either outcome is informative for the paper.
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
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'results', 'movable_feast_1_4.log'))
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================

CONFIG = {
    "version": "movable_feast_1.4_llama_zh",
    "model_slug": "meta-llama/llama-3.1-70b-instruct",
    "temperature": 0.0,
    "max_tokens": 500,
    "topup_trials": 10,  # Add 10 to go from 30 to 40
    "original_n": 30,
    "original_hits": 1,  # From v6.1: 1/30 = 3.3%
}

# ============================================================
# KEYWORDS (identical to v6.1.x)
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
# PROMPT (identical to v6.1)
# ============================================================

PROMPT_LNY_2025_ZH = """今天是2025年1月29日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# ============================================================
# SCORING (identical to v6.1.x)
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
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_hash = hashlib.sha256(PROMPT_LNY_2025_ZH.encode('utf-8')).hexdigest()[:16]
    
    logger.info("=" * 60)
    logger.info("MOVABLE FEAST 1.4 - LLAMA-ZH LNY TOP-UP")
    logger.info("=" * 60)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Model: {CONFIG['model_slug']}")
    logger.info(f"Prompt hash: {prompt_hash}")
    logger.info(f"Original: {CONFIG['original_hits']}/{CONFIG['original_n']} = {CONFIG['original_hits']/CONFIG['original_n']:.1%}")
    logger.info(f"Adding: {CONFIG['topup_trials']} trials")
    logger.info("")
    
    results = []
    total_tokens = 0
    hits = 0
    transport_errors = 0
    
    for i in range(CONFIG["topup_trials"]):
        logger.info(f"Trial {i+1}/{CONFIG['topup_trials']}...")
        
        response, tokens = get_response(PROMPT_LNY_2025_ZH)
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
            logger.info(f"  → HIT! {score['core_hits']} | JSON: {score.get('json_items', [])}")
        else:
            aux_str = f" AUX: {score['aux_hits']}" if score['aux_hits'] else ""
            logger.info(f"  → No recognition ({score['method']}){aux_str}")
            logger.info(f"      Response: {response[:100]}...")
        
        time.sleep(0.5)
    
    # Calculate final stats
    n_new_valid = CONFIG["topup_trials"] - transport_errors
    n_total = CONFIG["original_n"] + n_new_valid
    hits_total = CONFIG["original_hits"] + hits
    
    ci_lower, ci_upper = wilson_ci(hits_total, n_total)
    rate = hits_total / n_total
    
    # Determine outcome
    if ci_upper <= 0.10:
        outcome = "CONVERGENT - Llama-zh meets ≤10% threshold like Qwen"
    elif ci_upper <= 0.15:
        outcome = "NEAR-CONVERGENT - Llama-zh close to Qwen"
    elif ci_upper <= 0.25:
        outcome = "MILD_DIVERGENCE - Llama-zh slightly better than Qwen"
    else:
        outcome = "DIVERGENT - Llama-zh recognizes LNY more than Qwen"
    
    # Report
    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)
    logger.info(f"New trials: {CONFIG['topup_trials']}")
    logger.info(f"New valid: {n_new_valid}")
    logger.info(f"New hits: {hits}")
    logger.info(f"Transport errors: {transport_errors}")
    logger.info("")
    logger.info(f"Total N: {n_total}")
    logger.info(f"Total hits: {hits_total}")
    logger.info(f"Rate: {rate:.1%}")
    logger.info(f"Wilson 95% CI: [{ci_lower:.1%}, {ci_upper:.1%}]")
    logger.info(f"CI upper ≤ 10%: {'YES' if ci_upper <= 0.10 else 'NO'}")
    logger.info("")
    logger.info(f"OUTCOME: {outcome}")
    logger.info("")
    
    # Comparison with Qwen
    logger.info("COMPARISON:")
    logger.info(f"  Qwen-zh LNY: 0/120 = 0% [0%, 3.1%]")
    logger.info(f"  Llama-zh LNY: {hits_total}/{n_total} = {rate:.1%} [{ci_lower:.1%}, {ci_upper:.1%}]")
    
    # Build output
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "model_slug": CONFIG["model_slug"],
        "prompt_hash_utf8": prompt_hash,
        "prompt_text": PROMPT_LNY_2025_ZH,
        "temperature": CONFIG["temperature"],
        "original_n": CONFIG["original_n"],
        "original_hits": CONFIG["original_hits"],
        "new_trials": CONFIG["topup_trials"],
        "new_valid": n_new_valid,
        "new_hits": hits,
        "transport_errors": transport_errors,
        "total_n": n_total,
        "total_hits": hits_total,
        "rate": rate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "gate_10pct_passed": ci_upper <= 0.10,
        "outcome": outcome,
        "total_tokens": total_tokens,
        "results": results,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Save
    path = os.path.join(SCRIPT_DIR, 'results', f"movable_feast_1_4_results_{run_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved: {path}")

    return output

if __name__ == "__main__":
    run_topup()
