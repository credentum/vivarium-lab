#!/usr/bin/env python3
"""
Project Vivarium v6.2 - Causality Micro-Experiments
====================================================

Two cheap, high-value tests to separate:
(A) Data Gravity / cultural salience imbalance
(B) Missing lunar-calendar grounding

Test 1: Fixed-date Chinese holiday (国庆节 - National Day, Oct 1)
- If recognized at ~100%: issue is lunar mapping, not "Chinese holidays"
- If near-zero: broader Chinese holiday blindness

Test 2: Lunar-phrase prompt ("今天是农历正月初一")
- If recognition >50%: model knows LNY concept, just can't map Gregorian→Lunar
- If still near-zero: concept itself is missing → stronger Data Gravity

N=20 each, Qwen-72B zh only.
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
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'results', 'movable_feast_2.log'))
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================

CONFIG = {
    "version": "movable_feast_2_causality",
    "model_slug": "qwen/qwen-2.5-72b-instruct",
    "temperature": 0.0,
    "max_tokens": 500,
    "trials_per_test": 20,
}

# ============================================================
# PROMPTS
# ============================================================

# Test 1: Fixed-date Chinese holiday (National Day - October 1)
PROMPT_GUOQING = """今天是2025年10月1日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# Test 2: Lunar-phrase prompt (explicitly stating lunar date)
PROMPT_LUNAR_PHRASE = """今天是农历正月初一。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# For comparison: Original LNY prompt (Gregorian date)
PROMPT_LNY_GREGORIAN = """今天是2025年1月29日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# ============================================================
# KEYWORDS
# ============================================================

# For National Day (国庆节)
CORE_GUOQING = {
    "国庆节", "國慶節", "national day", "国庆", "國慶",
    "中华人民共和国成立", "建国", "十一"
}

# For LNY (same as before)
CORE_LNY = {
    "lunar new year", "chinese new year",
    "春节", "春節", "农历新年", "農曆新年",
    "seollal", "설날",
    "tết", "tết nguyên đán", "tet nguyen dan",
}

SPRING_FESTIVAL_TOKEN = "spring festival"
CHINESE_CONTEXT_CHARS = set("春节春節农历農曆中国中國华人華人")

BAD_HOLIDAYS = {"wednesday", "周三", "星期三", "weekday", "工作日", "today", "今天"}

# ============================================================
# SCORING
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

def check_recognition(response: str, core_tokens: set) -> Tuple[bool, List[str]]:
    """Check if response contains any core tokens."""
    if not response:
        return False, []
    
    # First try JSON
    json_items, _ = parse_json_holidays(response)
    if json_items:
        norm = lambda s: unicodedata.normalize("NFKC", s).lower().strip() if s else ""
        items_norm = [norm(x) for x in json_items if x]
        
        # Check for core tokens in JSON items
        hits = []
        for item in items_norm:
            for token in core_tokens:
                if normalize_text(token) in item or item in normalize_text(token):
                    hits.append(item)
                    break
        
        # Special handling for spring festival
        if SPRING_FESTIVAL_TOKEN in items_norm:
            items_joined = "".join(items_norm)
            if any(ch in items_joined for ch in CHINESE_CONTEXT_CHARS):
                hits.append(SPRING_FESTIVAL_TOKEN)
        
        return len(hits) > 0, hits
    
    # Fallback to keyword search
    response_norm = normalize_text(response)
    hits = [t for t in core_tokens if normalize_text(t) in response_norm]
    return len(hits) > 0, hits

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
# TEST RUNNERS
# ============================================================

def run_test(test_name: str, prompt: str, core_tokens: set, n_trials: int) -> Dict:
    """Run a single test."""
    logger.info(f"\n{'='*50}")
    logger.info(f"TEST: {test_name}")
    logger.info(f"N: {n_trials}")
    logger.info(f"{'='*50}")
    
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]
    logger.info(f"Prompt hash: {prompt_hash}")
    logger.info(f"Prompt:\n{prompt}\n")
    
    results = []
    total_tokens = 0
    hits = 0
    transport_errors = 0
    
    for i in range(n_trials):
        logger.info(f"Trial {i+1}/{n_trials}...")
        
        response, tokens = get_response(prompt)
        total_tokens += tokens
        
        if response is None:
            transport_errors += 1
            logger.warning(f"  → TRANSPORT ERROR")
            results.append({"trial": i, "response": None, "transport_error": True})
            continue
        
        recognized, core_hits = check_recognition(response, core_tokens)
        json_items, json_method = parse_json_holidays(response)
        
        results.append({
            "trial": i,
            "response": response,
            "transport_error": False,
            "recognized": recognized,
            "core_hits": core_hits,
            "json_items": json_items,
            "method": json_method,
        })
        
        if recognized:
            hits += 1
            logger.info(f"  → HIT! {core_hits} | JSON: {json_items}")
        else:
            logger.info(f"  → No recognition | JSON: {json_items}")
        
        time.sleep(0.5)
    
    n_valid = n_trials - transport_errors
    ci_lower, ci_upper = wilson_ci(hits, n_valid) if n_valid > 0 else (0, 1)
    rate = hits / n_valid if n_valid > 0 else 0
    
    logger.info(f"\nResult: {hits}/{n_valid} = {rate:.1%}")
    logger.info(f"Wilson 95% CI: [{ci_lower:.1%}, {ci_upper:.1%}]")
    
    return {
        "test_name": test_name,
        "prompt": prompt,
        "prompt_hash": prompt_hash,
        "core_tokens": list(core_tokens),
        "n_trials": n_trials,
        "n_valid": n_valid,
        "transport_errors": transport_errors,
        "hits": hits,
        "rate": rate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "total_tokens": total_tokens,
        "results": results,
    }

def run_all():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 60)
    logger.info("MOVABLE FEAST 2 - CAUSALITY MICRO-EXPERIMENTS")
    logger.info("=" * 60)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Model: {CONFIG['model_slug']}")
    logger.info("")
    logger.info("Purpose: Separate Data Gravity from calendar-grounding failure")
    logger.info("")
    logger.info("Test 1: Fixed-date Chinese holiday (国庆节 Oct 1)")
    logger.info("  - If ~100%: lunar mapping is the issue")
    logger.info("  - If ~0%: broader Chinese holiday blindness")
    logger.info("")
    logger.info("Test 2: Lunar-phrase prompt (农历正月初一)")
    logger.info("  - If >50%: model knows LNY, can't map Gregorian→Lunar")
    logger.info("  - If ~0%: concept itself is missing")
    logger.info("")
    
    all_tests = {}
    total_tokens = 0
    
    # Test 1: National Day (fixed Gregorian date)
    test1 = run_test(
        test_name="guoqing_fixed_date",
        prompt=PROMPT_GUOQING,
        core_tokens=CORE_GUOQING,
        n_trials=CONFIG["trials_per_test"],
    )
    all_tests["guoqing"] = test1
    total_tokens += test1["total_tokens"]
    
    # Test 2: Lunar phrase (explicit lunar date)
    test2 = run_test(
        test_name="lny_lunar_phrase",
        prompt=PROMPT_LUNAR_PHRASE,
        core_tokens=CORE_LNY,
        n_trials=CONFIG["trials_per_test"],
    )
    all_tests["lny_lunar"] = test2
    total_tokens += test2["total_tokens"]
    
    # Summary and interpretation
    logger.info("\n" + "="*60)
    logger.info("SUMMARY & INTERPRETATION")
    logger.info("="*60)
    
    guoqing_rate = test1["rate"]
    lunar_rate = test2["rate"]
    
    logger.info(f"\n国庆节 (Oct 1, fixed): {test1['hits']}/{test1['n_valid']} = {guoqing_rate:.1%}")
    logger.info(f"LNY (lunar phrase): {test2['hits']}/{test2['n_valid']} = {lunar_rate:.1%}")
    logger.info(f"LNY (Gregorian, from v6.1): 0/40 = 0%")
    
    # Interpretation matrix
    logger.info("\n" + "-"*40)
    logger.info("INTERPRETATION:")
    
    if guoqing_rate >= 0.8:
        logger.info("✓ 国庆节 recognized → NOT general Chinese holiday blindness")
        if lunar_rate >= 0.5:
            interpretation = "MAPPING_FAILURE"
            logger.info("✓ Lunar phrase recognized → Model knows LNY concept")
            logger.info("→ CONCLUSION: Gregorian↔Lunar MAPPING failure, not concept absence")
        else:
            interpretation = "MIXED"
            logger.info("✗ Lunar phrase NOT recognized → Partial concept gap")
            logger.info("→ CONCLUSION: Both mapping AND concept issues")
    else:
        if lunar_rate >= 0.5:
            interpretation = "SELECTIVE_BLINDNESS"
            logger.info("✗ 国庆节 NOT recognized → Broader Chinese holiday issue")
            logger.info("✓ But lunar phrase works → Inconsistent pattern")
            logger.info("→ CONCLUSION: Selective blindness to Chinese holidays")
        else:
            interpretation = "DATA_GRAVITY_STRONG"
            logger.info("✗ 国庆节 NOT recognized → Broader Chinese holiday issue")
            logger.info("✗ Lunar phrase NOT recognized → Concept absent")
            logger.info("→ CONCLUSION: Strong DATA GRAVITY - Chinese holidays underrepresented")
    
    logger.info(f"\nFINAL INTERPRETATION: {interpretation}")
    logger.info(f"Total tokens: {total_tokens:,}")
    
    # Build output
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "model_slug": CONFIG["model_slug"],
        "purpose": "Separate Data Gravity from calendar-grounding failure",
        "tests": all_tests,
        "interpretation": interpretation,
        "interpretation_matrix": {
            "guoqing_high_lunar_high": "MAPPING_FAILURE - knows concepts, can't map dates",
            "guoqing_high_lunar_low": "MIXED - fixed dates OK, lunar concepts weak",
            "guoqing_low_lunar_high": "SELECTIVE_BLINDNESS - inconsistent pattern",
            "guoqing_low_lunar_low": "DATA_GRAVITY_STRONG - Chinese holidays underrepresented",
        },
        "comparison": {
            "guoqing_rate": guoqing_rate,
            "lny_lunar_rate": lunar_rate,
            "lny_gregorian_rate": 0.0,  # From v6.1
        },
        "total_tokens": total_tokens,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Save
    path = os.path.join(SCRIPT_DIR, 'results', f"movable_feast_2_results_{run_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved: {path}")

    return output

if __name__ == "__main__":
    run_all()
