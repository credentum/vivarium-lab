#!/usr/bin/env python3
"""
Project Vivarium v6.6 - Final Polish Sprint
============================================

Closes remaining gaps before publication:

1. COT ABLATION: Why 90% not 100%?
   - Minimal: "Step 1: convert; Step 2: identify"
   - Full: Current CoT prompt
   - Rules-injected: Include lunar calendar snippet
   - Goal: Push to ≥98% or explain residual

2. V6 PHRASE RECONCILIATION: 70% → 95%?
   - Re-run exact v6 phrase at N=40
   - Compare to v6.5 synonym panel winner
   - Document alias brittleness

3. ICL-WITH-COT: Does reasoning step in examples help?
   - 5-shot with worked conversions
   - If still 0%, confirms examples ≠ reasoning procedure

4. CROSS-FAMILY EXPANSION: Yi or Mistral
   - 3 cells: Gregorian LNY, lunar phrase, Christmas
   - N=30 each

5. LATENCY/COST MEASUREMENT
   - Time each method
   - Count tokens
   - Build comparison table
"""

import os
import json
import time
import logging
import unicodedata
import math
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import openai
from dotenv import load_dotenv

# Load .env from project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, '..', '..', '..', '.env'))

# ============================================================
# LOGGING
# ============================================================

os.makedirs(os.path.join(SCRIPT_DIR, 'results'), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'results', 'movable_feast_6.log'))
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================

CONFIG = {
    "version": "movable_feast_6_polish",
    "primary_model": "qwen/qwen-2.5-72b-instruct",
    "cross_family_models": [
        "01-ai/yi-large",  # Yi
        "mistralai/mistral-large",  # Mistral
    ],
    "temperature": 0.0,
    "max_tokens": 500,
    "trials_per_cell": 30,
}

CORE_LNY = {"春节", "春節", "农历新年", "農曆新年", "lunar new year", "chinese new year"}

# ============================================================
# PART 1: COT ABLATION PROMPTS
# ============================================================

COT_MINIMAL = """今天是2025年1月29日，星期三。

请按两步回答：
步骤1：这个日期对应的农历日期是什么？
步骤2：这个农历日期有什么节日？

最后用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}"""

COT_FULL = """请按步骤推理：

步骤1：将公历日期转换为农历日期
步骤2：根据农历日期判断是否为节日

已知映射（示例）：
2024-02-10 = 农历正月初一 = 春节
2024-06-10 = 农历五月初五 = 端午节
2024-09-17 = 农历八月十五 = 中秋节

现在，请分析 2025年1月29日，星期三：

步骤1：2025-01-29 的农历日期是？
步骤2：这个农历日期对应什么节日？

最后用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}"""

COT_RULES = """农历节日速查规则：
- 正月初一 = 春节（农历新年）
- 五月初五 = 端午节
- 八月十五 = 中秋节
- 正月十五 = 元宵节
- 九月初九 = 重阳节

农历日期换算提示：
- 2025年春节是1月29日（正月初一）
- 农历月份约29-30天，与公历有约1个月差异

今天是2025年1月29日，星期三。

请按步骤推理：
步骤1：根据上述规则，2025-01-29对应什么农历日期？
步骤2：这个农历日期对应什么节日？

最后用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}"""

# ============================================================
# PART 2: V6 PHRASE RECONCILIATION
# ============================================================

# Original v6 phrase (verbatim)
V6_ORIGINAL = """今天是农历正月初一。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# Best v6.5 synonym (大年初一 or similar)
V65_BEST = """今天是大年初一。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# ============================================================
# PART 3: ICL-WITH-COT (Worked Examples)
# ============================================================

ICL_WITH_COT = """以下是日期→节日的推理示例：

示例1：
问：2024年2月10日是什么节日？
答：步骤1：2024-02-10 = 农历正月初一。步骤2：正月初一 = 春节。
结果：{"holidays": ["春节"]}

示例2：
问：2024年6月10日是什么节日？
答：步骤1：2024-06-10 = 农历五月初五。步骤2：五月初五 = 端午节。
结果：{"holidays": ["端午节"]}

示例3：
问：2024年9月17日是什么节日？
答：步骤1：2024-09-17 = 农历八月十五。步骤2：八月十五 = 中秋节。
结果：{"holidays": ["中秋节"]}

示例4：
问：2024年7月15日是什么节日？
答：步骤1：2024-07-15 = 农历六月初十。步骤2：六月初十无重大节日。
结果：{"holidays": []}

示例5：
问：2023年1月22日是什么节日？
答：步骤1：2023-01-22 = 农历正月初一。步骤2：正月初一 = 春节。
结果：{"holidays": ["春节"]}

现在请回答：
问：2025年1月29日是什么节日？
答："""

# ============================================================
# PART 4: CROSS-FAMILY PROMPTS
# ============================================================

PROMPT_GREGORIAN = """今天是2025年1月29日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

PROMPT_LUNAR = """今天是农历正月初一。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

PROMPT_CHRISTMAS = """今天是2025年12月25日，星期四。

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
                return [str(h) for h in data["holidays"] if h]
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
    
    # Keyword fallback for CoT responses
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

def get_response_timed(prompt: str, model: str = None) -> Tuple[Optional[str], int, float]:
    """Get response with timing for latency measurement."""
    model = model or CONFIG["primary_model"]
    
    start_time = time.time()
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=CONFIG["temperature"],
            max_tokens=CONFIG["max_tokens"],
        )
        elapsed = time.time() - start_time
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        return text, tokens, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"API error: {e}")
        return None, 0, elapsed

# ============================================================
# TEST RUNNERS
# ============================================================

def run_cell_timed(cell_id: str, prompt: str, core_tokens: set, n_trials: int,
                   model: str = None) -> Dict:
    """Run cell with timing data."""
    logger.info(f"\n{'='*50}")
    logger.info(f"CELL: {cell_id}")
    logger.info(f"Model: {model or CONFIG['primary_model']}")
    logger.info(f"{'='*50}")
    
    results = []
    hits = 0
    total_tokens = 0
    total_latency = 0
    prompt_tokens = len(prompt)  # Rough estimate
    
    for i in range(n_trials):
        logger.info(f"Trial {i+1}/{n_trials}...")
        
        response, tokens, latency = get_response_timed(prompt, model)
        total_tokens += tokens
        total_latency += latency
        
        if response is None:
            results.append({"trial": i, "response": None, "error": True, "latency": latency})
            continue
        
        recognized, core_hits = check_recognition(response, core_tokens)
        results.append({
            "trial": i,
            "response": response,
            "recognized": recognized,
            "hits": core_hits,
            "tokens": tokens,
            "latency": latency,
        })
        
        if recognized:
            hits += 1
            logger.info(f"  → HIT: {core_hits} ({latency:.2f}s)")
        else:
            logger.info(f"  → Miss ({latency:.2f}s): {response[:50]}...")
        
        time.sleep(0.3)
    
    n_valid = len([r for r in results if not r.get("error")])
    ci_lower, ci_upper = wilson_ci(hits, n_valid) if n_valid > 0 else (0, 1)
    rate = hits / n_valid if n_valid > 0 else 0
    mean_latency = total_latency / n_trials if n_trials > 0 else 0
    mean_tokens = total_tokens / n_valid if n_valid > 0 else 0
    
    logger.info(f"\nResult: {hits}/{n_valid} = {rate:.1%}")
    logger.info(f"CI: [{ci_lower:.1%}, {ci_upper:.1%}]")
    logger.info(f"Mean latency: {mean_latency:.2f}s")
    logger.info(f"Mean tokens: {mean_tokens:.0f}")
    
    return {
        "cell_id": cell_id,
        "model": model or CONFIG["primary_model"],
        "n_valid": n_valid,
        "hits": hits,
        "rate": rate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "mean_latency": mean_latency,
        "mean_tokens": mean_tokens,
        "prompt_chars": prompt_tokens,
        "results": results,
    }

# ============================================================
# MAIN EXPERIMENTS
# ============================================================

def run_cot_ablation() -> Dict:
    """Part 1: CoT ablation to push to ≥98%."""
    logger.info("\n" + "="*60)
    logger.info("PART 1: COT ABLATION")
    logger.info("="*60)
    
    results = {}
    results["minimal"] = run_cell_timed("cot_minimal", COT_MINIMAL, CORE_LNY, CONFIG["trials_per_cell"])
    results["full"] = run_cell_timed("cot_full", COT_FULL, CORE_LNY, CONFIG["trials_per_cell"])
    results["rules"] = run_cell_timed("cot_rules", COT_RULES, CORE_LNY, CONFIG["trials_per_cell"])
    
    return results

def run_v6_reconciliation() -> Dict:
    """Part 2: Reconcile v6 70% vs v6.5 95%."""
    logger.info("\n" + "="*60)
    logger.info("PART 2: V6 PHRASE RECONCILIATION")
    logger.info("="*60)
    
    results = {}
    results["v6_original"] = run_cell_timed("v6_original", V6_ORIGINAL, CORE_LNY, 40)  # N=40 for tighter CI
    results["v65_best"] = run_cell_timed("v65_best", V65_BEST, CORE_LNY, 40)
    
    return results

def run_icl_with_cot() -> Dict:
    """Part 3: ICL with worked CoT examples."""
    logger.info("\n" + "="*60)
    logger.info("PART 3: ICL WITH COT EXAMPLES")
    logger.info("="*60)
    
    results = {}
    results["icl_cot"] = run_cell_timed("icl_with_cot", ICL_WITH_COT, CORE_LNY, CONFIG["trials_per_cell"])
    
    return results

def run_cross_family() -> Dict:
    """Part 4: Cross-family expansion."""
    logger.info("\n" + "="*60)
    logger.info("PART 4: CROSS-FAMILY EXPANSION")
    logger.info("="*60)
    
    results = {}
    
    for model in CONFIG["cross_family_models"]:
        model_key = model.split("/")[-1]
        logger.info(f"\nTesting {model_key}...")
        
        try:
            results[f"{model_key}_gregorian"] = run_cell_timed(
                f"{model_key}_gregorian", PROMPT_GREGORIAN, CORE_LNY, CONFIG["trials_per_cell"], model
            )
            results[f"{model_key}_lunar"] = run_cell_timed(
                f"{model_key}_lunar", PROMPT_LUNAR, CORE_LNY, CONFIG["trials_per_cell"], model
            )
            results[f"{model_key}_christmas"] = run_cell_timed(
                f"{model_key}_christmas", PROMPT_CHRISTMAS, {"圣诞节", "圣诞", "christmas"}, CONFIG["trials_per_cell"], model
            )
        except Exception as e:
            logger.error(f"Failed for {model_key}: {e}")
            results[f"{model_key}_error"] = str(e)
    
    return results

def build_latency_table(all_results: Dict) -> Dict:
    """Part 5: Build latency/cost comparison table."""
    logger.info("\n" + "="*60)
    logger.info("PART 5: LATENCY/COST TABLE")
    logger.info("="*60)
    
    # Gather data from various cells
    table = []
    
    # Baseline (from v6.5 or earlier)
    table.append({
        "method": "Baseline (Gregorian only)",
        "extra_tokens": "~0",
        "extra_calls": 0,
        "accuracy": "0%",
        "notes": "Fails completely"
    })
    
    # CoT variants
    for variant in ["minimal", "full", "rules"]:
        if variant in all_results.get("cot_ablation", {}):
            r = all_results["cot_ablation"][variant]
            table.append({
                "method": f"CoT ({variant})",
                "extra_tokens": f"+{r.get('prompt_chars', 0)//4}",  # Rough token estimate
                "extra_calls": 0,
                "mean_latency": f"{r.get('mean_latency', 0):.2f}s",
                "accuracy": f"{r.get('rate', 0):.0%}",
            })
    
    # Tool (from v6.4/v6.5)
    table.append({
        "method": "Resolver tool",
        "extra_tokens": "+10-20",
        "extra_calls": "+1 (lookup)",
        "accuracy": "100%",
        "notes": "Requires external API"
    })
    
    # Explicit naming
    table.append({
        "method": "Explicit naming",
        "extra_tokens": "~0",
        "extra_calls": 0,
        "accuracy": "98-100%",
        "notes": "Must know holiday name"
    })
    
    # Lunar phrase
    if "v65_best" in all_results.get("v6_reconciliation", {}):
        r = all_results["v6_reconciliation"]["v65_best"]
        table.append({
            "method": "Lunar phrase (best)",
            "extra_tokens": "~0",
            "extra_calls": 0,
            "mean_latency": f"{r.get('mean_latency', 0):.2f}s",
            "accuracy": f"{r.get('rate', 0):.0%}",
        })
    
    logger.info("\nLatency/Cost Table:")
    for row in table:
        logger.info(f"  {row}")
    
    return {"table": table}

# ============================================================
# MAIN
# ============================================================

def run_all():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 60)
    logger.info("MOVABLE FEAST 6 - FINAL POLISH SPRINT")
    logger.info("=" * 60)
    logger.info(f"Run ID: {run_id}")
    logger.info("")
    
    all_results = {}
    
    # Part 1: CoT ablation
    all_results["cot_ablation"] = run_cot_ablation()
    
    # Part 2: v6 reconciliation
    all_results["v6_reconciliation"] = run_v6_reconciliation()
    
    # Part 3: ICL with CoT
    all_results["icl_with_cot"] = run_icl_with_cot()
    
    # Part 4: Cross-family (may fail if models unavailable)
    try:
        all_results["cross_family"] = run_cross_family()
    except Exception as e:
        logger.warning(f"Cross-family failed: {e}")
        all_results["cross_family"] = {"error": str(e)}
    
    # Part 5: Build latency table
    all_results["latency_table"] = build_latency_table(all_results)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    
    logger.info("\nCoT ABLATION:")
    for name, result in all_results.get("cot_ablation", {}).items():
        if isinstance(result, dict) and "rate" in result:
            logger.info(f"  {name}: {result['rate']:.0%} (latency: {result.get('mean_latency', 0):.2f}s)")
    
    logger.info("\nV6 RECONCILIATION:")
    for name, result in all_results.get("v6_reconciliation", {}).items():
        if isinstance(result, dict) and "rate" in result:
            logger.info(f"  {name}: {result['rate']:.0%}")
    
    logger.info("\nICL WITH COT:")
    icl_cot = all_results.get("icl_with_cot", {}).get("icl_cot", {})
    if isinstance(icl_cot, dict) and "rate" in icl_cot:
        logger.info(f"  icl_with_cot: {icl_cot['rate']:.0%}")
    
    # Save
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "results": all_results,
        "timestamp": datetime.now().isoformat(),
    }
    
    path = os.path.join(SCRIPT_DIR, 'results', f"movable_feast_6_results_{run_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"\nSaved: {path}")
    
    try:
        output_path = f"/mnt/user-data/outputs/movable_feast_6_results_{run_id}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Also saved: {output_path}")
    except Exception as e:
        logger.warning(f"Could not save to outputs: {e}")
    
    return output

if __name__ == "__main__":
    run_all()
