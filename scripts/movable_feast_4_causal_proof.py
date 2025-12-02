#!/usr/bin/env python3
"""
Project Vivarium v6.4 - Generalization & Causal Tests
======================================================

Three tests to slam the door on the mapping failure finding:

1. EASTER TEST: Generalize beyond Chinese lunar holidays
   - Gregorian date → expect ~0%
   - Name control ("Easter Sunday") → expect ~100%
   - Rule cue (computus phrase) → exploratory

2. TOOL A/B: Prove calendar resolver fixes the failure
   - A: No-tool baseline → expect ~0%
   - B: Tool-assisted (pre-resolved) → expect ~100%
   - Δ ≥ 80pp = causal evidence

3. STRUCTURED FEW-SHOT: Table format vs prose
   - No-ICL baseline → expect ~0%
   - Prose-ICL (old few-shot) → expect ~0%
   - Table-ICL (structured) → exploratory (likely still ~0%)
"""

import os
import json
import time
import hashlib
import logging
import unicodedata
import math
import random
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import openai

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '.env'))
except ImportError:
    pass

# ============================================================
# LOGGING
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'results', 'movable_feast_4.log'))
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================

CONFIG = {
    "version": "movable_feast_4_generalization_causal",
    "model_slug": "qwen/qwen-2.5-72b-instruct",
    "temperature": 0.0,
    "max_tokens": 500,
    "trials_per_cell": 20,
    "random_seed": 42,
}

random.seed(CONFIG["random_seed"])

# ============================================================
# EASTER DATES (Western, from authoritative sources)
# ============================================================

EASTER_DATES = {
    "2024": {"gregorian": "2024-03-31", "weekday": "Sunday"},
    "2025": {"gregorian": "2025-04-20", "weekday": "Sunday"},
    "2026": {"gregorian": "2026-04-05", "weekday": "Sunday"},
}

# LNY dates for Tool A/B test
LNY_DATES = {
    "2025": {
        "gregorian": "2025年1月29日",
        "gregorian_iso": "2025-01-29",
        "weekday": "星期三",
        "lunar": "正月初一",
        "holiday": "春节",
    },
}

# ============================================================
# CORE TOKENS
# ============================================================

CORE_EASTER = {"easter", "easter sunday", "resurrection sunday", "pascha"}
CORE_LNY = {"春节", "春節", "农历新年", "農曆新年", "lunar new year", "chinese new year"}

# ============================================================
# PROMPTS - EASTER TEST
# ============================================================

def make_easter_gregorian_prompt(date_info: dict) -> str:
    """Gregorian-only prompt for Easter."""
    return f"""Today's date is {date_info['gregorian']}, {date_info['weekday']}.

Question: Are there any important holidays or cultural events today?

Please respond only in JSON format:
{{"holidays": ["holiday1", "holiday2"]}}

If there are no holidays, respond: {{"holidays": []}}"""

def make_easter_name_prompt(date_info: dict) -> str:
    """Name control - explicitly mention Easter."""
    return f"""Today's date is {date_info['gregorian']}, {date_info['weekday']}. Today is Easter Sunday.

Question: Are there any important holidays or cultural events today?

Please respond only in JSON format:
{{"holidays": ["holiday1", "holiday2"]}}

If there are no holidays, respond: {{"holidays": []}}"""

def make_easter_computus_prompt(date_info: dict) -> str:
    """Rule cue - describe Easter computation rule."""
    return f"""Today's date is {date_info['gregorian']}, {date_info['weekday']}. 
Today is the first Sunday after the first full moon on or after March 21.

Question: Are there any important holidays or cultural events today?

Please respond only in JSON format:
{{"holidays": ["holiday1", "holiday2"]}}

If there are no holidays, respond: {{"holidays": []}}"""

# ============================================================
# PROMPTS - TOOL A/B TEST
# ============================================================

def make_tool_baseline_prompt(date_info: dict) -> str:
    """A: No-tool baseline (same as v6.1)."""
    return f"""今天是{date_info['gregorian']}，{date_info['weekday']}。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{{"holidays": ["节日名称1", "节日名称2"]}}

如果没有节日，请返回：{{"holidays": []}}"""

def make_tool_assisted_prompt(date_info: dict) -> str:
    """B: Tool-assisted with pre-resolved lunar date."""
    resolver_hint = f"[日历解析器] {date_info['gregorian_iso']} = 农历{date_info['lunar']}（{date_info['holiday']}）"
    
    return f"""{resolver_hint}

今天是{date_info['gregorian']}，{date_info['weekday']}。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{{"holidays": ["节日名称1", "节日名称2"]}}

如果没有节日，请返回：{{"holidays": []}}"""

# ============================================================
# PROMPTS - STRUCTURED FEW-SHOT TEST
# ============================================================

PROMPT_NO_ICL = """今天是2025年1月29日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

PROMPT_PROSE_ICL = """以下是一些公历与农历日期的对应关系：

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

PROMPT_TABLE_ICL = """已知映射（示例）：
| 公历日期       | 农历日期  | 节日   |
|----------------|-----------|--------|
| 2024-02-10     | 正月初一  | 春节   |
| 2024-06-10     | 五月初五  | 端午节 |
| 2024-09-17     | 八月十五  | 中秋节 |
| 2023-01-22     | 正月初一  | 春节   |
| 2025-10-06     | 八月十五  | 中秋节 |

请根据以上示例推断下方日期的节日（若无节日则为空）：
| 公历日期       | 农历日期  | 节日   |
|----------------|-----------|--------|
| 2025-01-29     |    ?      |   ?    |

仅用JSON回答：{"holidays": ["节日名称1", "节日名称2"]}；若没有节日：{"holidays": []}"""

# ============================================================
# SCORING
# ============================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFKC', text.lower().strip())

def parse_json_holidays(response: str) -> List[str]:
    if not response:
        return []
    for attempt in [
        lambda: json.loads(response.strip()),
        lambda: json.loads(response[response.find("{"):response.rfind("}")+1]) if "{" in response else None,
    ]:
        try:
            data = attempt()
            if data and isinstance(data.get("holidays"), list):
                return data["holidays"]
            if data and isinstance(data.get("holidays"), str):
                return [data["holidays"]]
        except:
            pass
    return []

def check_recognition(response: str, core_tokens: set) -> Tuple[bool, List[str]]:
    if not response:
        return False, []
    
    items = parse_json_holidays(response)
    if items:
        items_norm = [normalize_text(x) for x in items if x]
        hits = []
        for item in items_norm:
            for token in core_tokens:
                token_norm = normalize_text(token)
                if token_norm in item or item in token_norm:
                    hits.append(item)
                    break
        return len(hits) > 0, hits
    
    # Keyword fallback
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

def get_response(prompt: str, system_msg: str = None) -> Tuple[Optional[str], int]:
    try:
        client = get_client()
        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=CONFIG["model_slug"],
            messages=messages,
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

def run_cell(cell_id: str, prompt: str, core_tokens: set, n_trials: int, 
             system_msg: str = None) -> Dict:
    """Run a single test cell."""
    logger.info(f"\n{'='*50}")
    logger.info(f"CELL: {cell_id}")
    logger.info(f"{'='*50}")
    
    results = []
    hits = 0
    total_tokens = 0
    
    for i in range(n_trials):
        logger.info(f"Trial {i+1}/{n_trials}...")
        
        response, tokens = get_response(prompt, system_msg)
        total_tokens += tokens
        
        if response is None:
            results.append({"trial": i, "response": None, "error": True})
            continue
        
        recognized, core_hits = check_recognition(response, core_tokens)
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
    ci_lower, ci_upper = wilson_ci(hits, n_valid) if n_valid > 0 else (0, 1)
    rate = hits / n_valid if n_valid > 0 else 0
    
    logger.info(f"\nResult: {hits}/{n_valid} = {rate:.1%}")
    logger.info(f"CI: [{ci_lower:.1%}, {ci_upper:.1%}]")
    
    return {
        "cell_id": cell_id,
        "n_valid": n_valid,
        "hits": hits,
        "rate": rate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "results": results,
        "total_tokens": total_tokens,
    }

def run_easter_test() -> Dict:
    """Test 1: Easter generalization."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: EASTER GENERALIZATION")
    logger.info("="*60)
    
    results = {}
    
    # Use 2025 Easter date
    date_info = EASTER_DATES["2025"]
    
    # Gregorian-only
    results["gregorian"] = run_cell(
        "easter_gregorian",
        make_easter_gregorian_prompt(date_info),
        CORE_EASTER,
        CONFIG["trials_per_cell"]
    )
    
    # Name control
    results["name_control"] = run_cell(
        "easter_name_control",
        make_easter_name_prompt(date_info),
        CORE_EASTER,
        CONFIG["trials_per_cell"]
    )
    
    # Computus rule cue
    results["computus"] = run_cell(
        "easter_computus",
        make_easter_computus_prompt(date_info),
        CORE_EASTER,
        CONFIG["trials_per_cell"]
    )
    
    return results

def run_tool_ab_test() -> Dict:
    """Test 2: Tool A/B comparison."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: TOOL A/B")
    logger.info("="*60)
    
    results = {}
    date_info = LNY_DATES["2025"]
    
    # A: No-tool baseline
    results["baseline"] = run_cell(
        "tool_baseline",
        make_tool_baseline_prompt(date_info),
        CORE_LNY,
        CONFIG["trials_per_cell"]
    )
    
    # B: Tool-assisted
    results["tool_assisted"] = run_cell(
        "tool_assisted",
        make_tool_assisted_prompt(date_info),
        CORE_LNY,
        CONFIG["trials_per_cell"]
    )
    
    # Calculate effect size
    baseline_rate = results["baseline"]["rate"]
    assisted_rate = results["tool_assisted"]["rate"]
    delta = assisted_rate - baseline_rate
    
    results["effect_size"] = {
        "baseline_rate": baseline_rate,
        "assisted_rate": assisted_rate,
        "delta_pp": delta * 100,
        "cis_overlap": not (results["tool_assisted"]["ci_lower"] > results["baseline"]["ci_upper"]),
    }
    
    logger.info(f"\nEffect size: {delta*100:.1f}pp")
    logger.info(f"CIs overlap: {results['effect_size']['cis_overlap']}")
    
    return results

def run_structured_fewshot_test() -> Dict:
    """Test 3: Structured few-shot comparison."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: STRUCTURED FEW-SHOT")
    logger.info("="*60)
    
    results = {}
    
    # No-ICL baseline
    results["no_icl"] = run_cell(
        "no_icl",
        PROMPT_NO_ICL,
        CORE_LNY,
        CONFIG["trials_per_cell"]
    )
    
    # Prose-ICL (old few-shot)
    results["prose_icl"] = run_cell(
        "prose_icl",
        PROMPT_PROSE_ICL,
        CORE_LNY,
        CONFIG["trials_per_cell"]
    )
    
    # Table-ICL (structured)
    results["table_icl"] = run_cell(
        "table_icl",
        PROMPT_TABLE_ICL,
        CORE_LNY,
        CONFIG["trials_per_cell"]
    )
    
    return results

# ============================================================
# MAIN
# ============================================================

def run_all():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 60)
    logger.info("MOVABLE FEAST 4 - GENERALIZATION & CAUSAL TESTS")
    logger.info("=" * 60)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Model: {CONFIG['model_slug']}")
    logger.info("")
    
    all_results = {}
    total_tokens = 0
    
    # Test 1: Easter
    easter_results = run_easter_test()
    all_results["easter"] = easter_results
    total_tokens += sum(r["total_tokens"] for r in easter_results.values())
    
    # Test 2: Tool A/B
    tool_results = run_tool_ab_test()
    all_results["tool_ab"] = tool_results
    total_tokens += sum(r["total_tokens"] for r in tool_results.values() if isinstance(r, dict) and "total_tokens" in r)
    
    # Test 3: Structured few-shot
    fewshot_results = run_structured_fewshot_test()
    all_results["structured_fewshot"] = fewshot_results
    total_tokens += sum(r["total_tokens"] for r in fewshot_results.values())
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    
    logger.info("\n1. EASTER TEST:")
    logger.info(f"   Gregorian-only: {easter_results['gregorian']['rate']:.1%}")
    logger.info(f"   Name control:   {easter_results['name_control']['rate']:.1%}")
    logger.info(f"   Computus rule:  {easter_results['computus']['rate']:.1%}")
    
    logger.info("\n2. TOOL A/B:")
    logger.info(f"   Baseline (no tool): {tool_results['baseline']['rate']:.1%}")
    logger.info(f"   Tool-assisted:      {tool_results['tool_assisted']['rate']:.1%}")
    logger.info(f"   Δ: {tool_results['effect_size']['delta_pp']:.1f}pp")
    
    logger.info("\n3. STRUCTURED FEW-SHOT:")
    logger.info(f"   No-ICL:    {fewshot_results['no_icl']['rate']:.1%}")
    logger.info(f"   Prose-ICL: {fewshot_results['prose_icl']['rate']:.1%}")
    logger.info(f"   Table-ICL: {fewshot_results['table_icl']['rate']:.1%}")
    
    logger.info(f"\nTotal tokens: {total_tokens:,}")
    
    # Gate evaluation
    logger.info("\n" + "-"*40)
    logger.info("GATE EVALUATION:")
    
    # Easter gates
    easter_greg_pass = easter_results['gregorian']['ci_upper'] <= 0.10
    easter_name_pass = easter_results['name_control']['ci_lower'] >= 0.90
    logger.info(f"Easter Gregorian CI_upper ≤ 10%: {'✓ PASS' if easter_greg_pass else '✗ FAIL'}")
    logger.info(f"Easter Name CI_lower ≥ 90%: {'✓ PASS' if easter_name_pass else '✗ FAIL'}")
    
    # Tool A/B gates
    tool_baseline_pass = tool_results['baseline']['ci_upper'] <= 0.10
    tool_assisted_pass = tool_results['tool_assisted']['ci_lower'] >= 0.90
    tool_delta_pass = tool_results['effect_size']['delta_pp'] >= 80
    logger.info(f"Tool baseline CI_upper ≤ 10%: {'✓ PASS' if tool_baseline_pass else '✗ FAIL'}")
    logger.info(f"Tool assisted CI_lower ≥ 90%: {'✓ PASS' if tool_assisted_pass else '✗ FAIL'}")
    logger.info(f"Tool Δ ≥ 80pp: {'✓ PASS' if tool_delta_pass else '✗ FAIL'}")
    
    # Build output
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "model_slug": CONFIG["model_slug"],
        "gates": {
            "easter_gregorian_pass": easter_greg_pass,
            "easter_name_pass": easter_name_pass,
            "tool_baseline_pass": tool_baseline_pass,
            "tool_assisted_pass": tool_assisted_pass,
            "tool_delta_pass": tool_delta_pass,
        },
        "results": all_results,
        "total_tokens": total_tokens,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Save
    path = os.path.join(SCRIPT_DIR, 'results', f"movable_feast_4_results_{run_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved: {path}")

    return output

if __name__ == "__main__":
    run_all()
