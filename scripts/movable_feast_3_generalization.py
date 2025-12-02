#!/usr/bin/env python3
"""
Project Vivarium v6.3 - Generalization & Diagnostic Tests
==========================================================

Three high-priority tests to strengthen the calendar-mapping finding:

1. GENERALIZATION: Test other lunar holidays (端午节, 中秋节)
   - Gregorian date → expect ~0%
   - Lunar phrase → expect >>0%
   - If replicates, mapping gap is general, not LNY-specific

2. REVERSE MAPPING: Can the model output lunar dates from Gregorian?
   - "2025年1月29日 → 农历?" 
   - Direct test of the mapping function

3. FEW-SHOT RESCUE: Can in-context examples fix the mapping?
   - Provide 3-5 Gregorian↔Lunar pairs
   - Then query target date
   - If works → model can use mapping when given
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
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'results', 'movable_feast_3.log'))
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================

CONFIG = {
    "version": "movable_feast_3_generalization",
    "model_slug": "qwen/qwen-2.5-72b-instruct",
    "temperature": 0.0,
    "max_tokens": 500,
    "trials_per_cell": 20,
}

# ============================================================
# LUNAR HOLIDAYS DATA
# ============================================================

LUNAR_HOLIDAYS = {
    "chunjie": {  # Spring Festival / LNY
        "name_zh": "春节",
        "lunar_date": "正月初一",
        "gregorian_2025": "2025年1月29日",
        "weekday_2025": "星期三",
        "core_tokens": {"春节", "春節", "农历新年", "農曆新年", "lunar new year", "chinese new year"},
    },
    "duanwu": {  # Dragon Boat Festival
        "name_zh": "端午节",
        "lunar_date": "五月初五",
        "gregorian_2025": "2025年5月31日",
        "weekday_2025": "星期六",
        "core_tokens": {"端午节", "端午節", "dragon boat", "龙舟节", "粽子节"},
    },
    "zhongqiu": {  # Mid-Autumn Festival
        "name_zh": "中秋节",
        "lunar_date": "八月十五",
        "gregorian_2025": "2025年10月6日",
        "weekday_2025": "星期一",
        "core_tokens": {"中秋节", "中秋節", "mid-autumn", "月饼节", "团圆节"},
    },
}

# ============================================================
# PROMPTS
# ============================================================

def make_gregorian_prompt(holiday_data: dict) -> str:
    return f"""今天是{holiday_data['gregorian_2025']}，{holiday_data['weekday_2025']}。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{{"holidays": ["节日名称1", "节日名称2"]}}

如果没有节日，请返回：{{"holidays": []}}"""

def make_lunar_prompt(holiday_data: dict) -> str:
    return f"""今天是农历{holiday_data['lunar_date']}。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{{"holidays": ["节日名称1", "节日名称2"]}}

如果没有节日，请返回：{{"holidays": []}}"""

# Reverse mapping prompt
REVERSE_MAPPING_PROMPT = """今天是2025年1月29日。

请给出对应的农历日期，仅用JSON格式回答：
{"lunar_date": "X月X日", "lunar_year": "乙巳年"}

如果不确定，请尽量给出最接近的答案。"""

# Few-shot rescue prompt
FEW_SHOT_PROMPT = """以下是一些公历与农历日期的对应关系：

2024年2月10日 = 农历正月初一（春节）
2024年6月10日 = 农历五月初五（端午节）
2024年9月17日 = 农历八月十五（中秋节）
2023年1月22日 = 农历正月初一（春节）
2025年10月6日 = 农历八月十五（中秋节）

现在，今天是2025年1月29日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# ============================================================
# SCORING
# ============================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFKC', text.lower().strip())

def parse_json(response: str) -> Optional[dict]:
    if not response:
        return None
    for attempt in [
        lambda: json.loads(response.strip()),
        lambda: json.loads(response[response.find("{"):response.rfind("}")+1]) if "{" in response else None,
    ]:
        try:
            data = attempt()
            if data is not None:
                return data
        except:
            pass
    return None

def check_holiday_recognition(response: str, core_tokens: set) -> Tuple[bool, List[str]]:
    if not response:
        return False, []
    
    data = parse_json(response)
    if data and "holidays" in data:
        items = data["holidays"]
        if isinstance(items, str):
            items = [items]
        if isinstance(items, list):
            items_norm = [normalize_text(x) for x in items if x]
            hits = []
            for item in items_norm:
                for token in core_tokens:
                    if normalize_text(token) in item or item in normalize_text(token):
                        hits.append(item)
                        break
            return len(hits) > 0, hits
    
    # Keyword fallback
    response_norm = normalize_text(response)
    hits = [t for t in core_tokens if normalize_text(t) in response_norm]
    return len(hits) > 0, hits

def check_lunar_date(response: str, expected_lunar: str) -> Tuple[bool, str]:
    """Check if reverse mapping returned correct lunar date."""
    if not response:
        return False, ""
    
    data = parse_json(response)
    if data and "lunar_date" in data:
        returned = data["lunar_date"]
        # Check if it matches expected (e.g., "正月初一")
        expected_norm = normalize_text(expected_lunar)
        returned_norm = normalize_text(returned)
        # Flexible matching
        is_correct = expected_norm in returned_norm or returned_norm in expected_norm
        return is_correct, returned
    
    return False, response[:50]

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

def run_holiday_test(holiday_key: str, prompt_type: str, n_trials: int) -> Dict:
    """Run recognition test for a lunar holiday."""
    holiday = LUNAR_HOLIDAYS[holiday_key]
    
    if prompt_type == "gregorian":
        prompt = make_gregorian_prompt(holiday)
    else:
        prompt = make_lunar_prompt(holiday)
    
    cell_id = f"{holiday_key}_{prompt_type}"
    logger.info(f"\n{'='*50}")
    logger.info(f"TEST: {cell_id}")
    logger.info(f"Holiday: {holiday['name_zh']}")
    logger.info(f"Prompt type: {prompt_type}")
    logger.info(f"{'='*50}")
    
    results = []
    hits = 0
    total_tokens = 0
    
    for i in range(n_trials):
        logger.info(f"Trial {i+1}/{n_trials}...")
        
        response, tokens = get_response(prompt)
        total_tokens += tokens
        
        if response is None:
            results.append({"trial": i, "response": None, "error": True})
            continue
        
        recognized, core_hits = check_holiday_recognition(response, holiday["core_tokens"])
        results.append({
            "trial": i,
            "response": response,
            "recognized": recognized,
            "hits": core_hits,
        })
        
        if recognized:
            hits += 1
            logger.info(f"  → HIT: {core_hits}")
        else:
            logger.info(f"  → Miss: {response[:60]}...")
        
        time.sleep(0.5)
    
    n_valid = len([r for r in results if not r.get("error")])
    ci_lower, ci_upper = wilson_ci(hits, n_valid)
    
    logger.info(f"\nResult: {hits}/{n_valid} = {hits/n_valid:.1%}")
    logger.info(f"CI: [{ci_lower:.1%}, {ci_upper:.1%}]")
    
    return {
        "cell_id": cell_id,
        "holiday": holiday_key,
        "holiday_name": holiday["name_zh"],
        "prompt_type": prompt_type,
        "n_valid": n_valid,
        "hits": hits,
        "rate": hits / n_valid if n_valid > 0 else 0,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "results": results,
        "total_tokens": total_tokens,
    }

def run_reverse_mapping(n_trials: int) -> Dict:
    """Test reverse mapping: Gregorian → Lunar."""
    logger.info(f"\n{'='*50}")
    logger.info("TEST: REVERSE MAPPING (Gregorian → Lunar)")
    logger.info("Expected: 正月初一 for 2025-01-29")
    logger.info(f"{'='*50}")
    
    results = []
    correct = 0
    total_tokens = 0
    
    for i in range(n_trials):
        logger.info(f"Trial {i+1}/{n_trials}...")
        
        response, tokens = get_response(REVERSE_MAPPING_PROMPT)
        total_tokens += tokens
        
        if response is None:
            results.append({"trial": i, "response": None, "error": True})
            continue
        
        is_correct, returned = check_lunar_date(response, "正月初一")
        results.append({
            "trial": i,
            "response": response,
            "correct": is_correct,
            "returned_date": returned,
        })
        
        if is_correct:
            correct += 1
            logger.info(f"  → CORRECT: {returned}")
        else:
            logger.info(f"  → WRONG: {returned}")
        
        time.sleep(0.5)
    
    n_valid = len([r for r in results if not r.get("error")])
    ci_lower, ci_upper = wilson_ci(correct, n_valid)
    
    logger.info(f"\nResult: {correct}/{n_valid} = {correct/n_valid:.1%}")
    
    return {
        "test": "reverse_mapping",
        "n_valid": n_valid,
        "correct": correct,
        "rate": correct / n_valid if n_valid > 0 else 0,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "results": results,
        "total_tokens": total_tokens,
    }

def run_few_shot_rescue(n_trials: int) -> Dict:
    """Test if few-shot examples rescue recognition."""
    logger.info(f"\n{'='*50}")
    logger.info("TEST: FEW-SHOT RESCUE")
    logger.info("Providing Gregorian↔Lunar mapping examples")
    logger.info(f"{'='*50}")
    
    results = []
    hits = 0
    total_tokens = 0
    core_tokens = LUNAR_HOLIDAYS["chunjie"]["core_tokens"]
    
    for i in range(n_trials):
        logger.info(f"Trial {i+1}/{n_trials}...")
        
        response, tokens = get_response(FEW_SHOT_PROMPT)
        total_tokens += tokens
        
        if response is None:
            results.append({"trial": i, "response": None, "error": True})
            continue
        
        recognized, core_hits = check_holiday_recognition(response, core_tokens)
        results.append({
            "trial": i,
            "response": response,
            "recognized": recognized,
            "hits": core_hits,
        })
        
        if recognized:
            hits += 1
            logger.info(f"  → HIT: {core_hits}")
        else:
            logger.info(f"  → Miss: {response[:60]}...")
        
        time.sleep(0.5)
    
    n_valid = len([r for r in results if not r.get("error")])
    ci_lower, ci_upper = wilson_ci(hits, n_valid)
    
    logger.info(f"\nResult: {hits}/{n_valid} = {hits/n_valid:.1%}")
    logger.info(f"Baseline (no few-shot): 0%")
    logger.info(f"Rescue effect: {hits/n_valid:.1%} - 0% = {hits/n_valid:.1%}")
    
    return {
        "test": "few_shot_rescue",
        "n_valid": n_valid,
        "hits": hits,
        "rate": hits / n_valid if n_valid > 0 else 0,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "baseline": 0.0,
        "rescue_effect": hits / n_valid if n_valid > 0 else 0,
        "results": results,
        "total_tokens": total_tokens,
    }

# ============================================================
# MAIN
# ============================================================

def run_all():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 60)
    logger.info("MOVABLE FEAST 3 - GENERALIZATION & DIAGNOSTICS")
    logger.info("=" * 60)
    logger.info(f"Run ID: {run_id}")
    logger.info("")
    
    all_results = {
        "holiday_tests": {},
        "reverse_mapping": None,
        "few_shot_rescue": None,
    }
    total_tokens = 0
    
    # Test 1: Generalization to other lunar holidays
    logger.info("\n" + "="*60)
    logger.info("PART 1: GENERALIZATION TO OTHER LUNAR HOLIDAYS")
    logger.info("="*60)
    
    for holiday_key in ["duanwu", "zhongqiu"]:
        for prompt_type in ["gregorian", "lunar"]:
            result = run_holiday_test(holiday_key, prompt_type, CONFIG["trials_per_cell"])
            all_results["holiday_tests"][f"{holiday_key}_{prompt_type}"] = result
            total_tokens += result["total_tokens"]
    
    # Test 2: Reverse mapping
    logger.info("\n" + "="*60)
    logger.info("PART 2: REVERSE MAPPING DIAGNOSTIC")
    logger.info("="*60)
    
    reverse = run_reverse_mapping(CONFIG["trials_per_cell"])
    all_results["reverse_mapping"] = reverse
    total_tokens += reverse["total_tokens"]
    
    # Test 3: Few-shot rescue
    logger.info("\n" + "="*60)
    logger.info("PART 3: FEW-SHOT RESCUE TEST")
    logger.info("="*60)
    
    few_shot = run_few_shot_rescue(CONFIG["trials_per_cell"])
    all_results["few_shot_rescue"] = few_shot
    total_tokens += few_shot["total_tokens"]
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    
    logger.info("\nGeneralization (Gregorian vs Lunar):")
    for holiday_key in ["duanwu", "zhongqiu"]:
        greg = all_results["holiday_tests"].get(f"{holiday_key}_gregorian", {})
        lunar = all_results["holiday_tests"].get(f"{holiday_key}_lunar", {})
        logger.info(f"  {LUNAR_HOLIDAYS[holiday_key]['name_zh']}:")
        logger.info(f"    Gregorian: {greg.get('rate', 0):.1%}")
        logger.info(f"    Lunar:     {lunar.get('rate', 0):.1%}")
    
    logger.info(f"\nReverse Mapping: {reverse['rate']:.1%}")
    logger.info(f"Few-Shot Rescue: {few_shot['rate']:.1%} (baseline 0%)")
    logger.info(f"\nTotal tokens: {total_tokens:,}")
    
    # Build output
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "model_slug": CONFIG["model_slug"],
        "results": all_results,
        "total_tokens": total_tokens,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Save
    path = os.path.join(SCRIPT_DIR, 'results', f"movable_feast_3_results_{run_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved: {path}")

    return output

if __name__ == "__main__":
    run_all()
