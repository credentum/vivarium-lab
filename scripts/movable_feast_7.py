#!/usr/bin/env python3
"""
Project Vivarium v6.7 - CoT Step Ablation
=========================================

Why does CoT-rules get 90% but CoT-full gets 100%?

Hypothesis: The worked examples in CoT-full provide the conversion pattern.

Test:
- CoT-full (baseline): 100%
- CoT-full minus examples: ?
- CoT-scaffold only (no examples, no rules): ?

If minus-examples drops to ~90%, examples are doing the work.
If it stays 100%, something else in the scaffold matters.
"""

import os
import json
import time
import logging
import unicodedata
import math
from datetime import datetime
from typing import Optional, Tuple, List, Dict
import openai
from dotenv import load_dotenv

# Load .env from project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, '..', '..', '..', '.env'))

os.makedirs(os.path.join(SCRIPT_DIR, 'results'), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'results', 'movable_feast_7.log'))
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "version": "movable_feast_7_cot_ablation",
    "model": "qwen/qwen-2.5-72b-instruct",
    "temperature": 0.0,
    "max_tokens": 500,
    "trials_per_cell": 30,
}

CORE_LNY = {"春节", "春節", "农历新年", "農曆新年", "lunar new year", "chinese new year"}

# ============================================================
# COT VARIANTS TO ABLATE
# ============================================================

# Baseline: CoT-full (what got 100%)
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

# Ablation 1: CoT-full MINUS examples (scaffold + instructions only)
COT_NO_EXAMPLES = """请按步骤推理：

步骤1：将公历日期转换为农历日期
步骤2：根据农历日期判断是否为节日

现在，请分析 2025年1月29日，星期三：

步骤1：2025-01-29 的农历日期是？
步骤2：这个农历日期对应什么节日？

最后用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}"""

# Ablation 2: Scaffold only (bare minimum structure)
COT_SCAFFOLD_ONLY = """请分析 2025年1月29日，星期三：

步骤1：这个公历日期对应的农历日期是？
步骤2：这个农历日期对应什么节日？

用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}"""

# Ablation 3: Examples but no explicit steps
COT_EXAMPLES_NO_STEPS = """已知映射：
2024-02-10 = 农历正月初一 = 春节
2024-06-10 = 农历五月初五 = 端午节
2024-09-17 = 农历八月十五 = 中秋节

请根据以上模式，分析 2025年1月29日，星期三 是什么节日？

用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}"""

# Ablation 4: Rules only (what got 90%)
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

# Ablation 5: Minimal (what got 0%)
COT_MINIMAL = """今天是2025年1月29日，星期三。

请按两步回答：
步骤1：这个日期对应的农历日期是什么？
步骤2：这个农历日期有什么节日？

最后用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}"""

VARIANTS = {
    "full": COT_FULL,
    "no_examples": COT_NO_EXAMPLES,
    "scaffold_only": COT_SCAFFOLD_ONLY,
    "examples_no_steps": COT_EXAMPLES_NO_STEPS,
    "rules": COT_RULES,
    "minimal": COT_MINIMAL,
}

# ============================================================
# HELPERS
# ============================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFKC', text.lower().strip())

def wilson_ci(successes: int, n: int) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    z = 1.96
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = z * math.sqrt((p*(1-p) + z**2/(4*n)) / n) / denom
    return (max(0, center - margin), min(1, center + margin))

def check_lny(response: str) -> bool:
    if not response:
        return False
    response_norm = normalize_text(response)
    for token in CORE_LNY:
        if normalize_text(token) in response_norm:
            return True
    # Check JSON
    try:
        if "{" in response:
            data = json.loads(response[response.find("{"):response.rfind("}")+1])
            if isinstance(data.get("holidays"), list):
                for h in data["holidays"]:
                    if any(normalize_text(t) in normalize_text(str(h)) for t in CORE_LNY):
                        return True
    except:
        pass
    return False

_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        _client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    return _client

def get_response(prompt: str) -> Tuple[Optional[str], float]:
    start = time.time()
    try:
        client = get_client()
        resp = client.chat.completions.create(
            model=CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=CONFIG["temperature"],
            max_tokens=CONFIG["max_tokens"],
        )
        return resp.choices[0].message.content, time.time() - start
    except Exception as e:
        logger.error(f"API error: {e}")
        return None, time.time() - start

def run_variant(name: str, prompt: str) -> Dict:
    logger.info(f"\n{'='*50}")
    logger.info(f"VARIANT: {name}")
    logger.info(f"{'='*50}")
    
    hits = 0
    results = []
    total_latency = 0
    
    for i in range(CONFIG["trials_per_cell"]):
        response, latency = get_response(prompt)
        total_latency += latency
        
        if response is None:
            results.append({"trial": i, "error": True})
            continue
        
        recognized = check_lny(response)
        results.append({
            "trial": i,
            "response": response[:200],
            "recognized": recognized,
            "latency": latency,
        })
        
        if recognized:
            hits += 1
            logger.info(f"  Trial {i+1}: HIT ({latency:.2f}s)")
        else:
            logger.info(f"  Trial {i+1}: Miss ({latency:.2f}s) - {response[:50]}...")
        
        time.sleep(0.3)
    
    n_valid = len([r for r in results if not r.get("error")])
    rate = hits / n_valid if n_valid > 0 else 0
    ci_lower, ci_upper = wilson_ci(hits, n_valid)
    mean_latency = total_latency / CONFIG["trials_per_cell"]
    
    logger.info(f"\nResult: {hits}/{n_valid} = {rate:.0%}")
    logger.info(f"Wilson 95% CI: [{ci_lower:.1%}, {ci_upper:.1%}]")
    
    return {
        "variant": name,
        "n": n_valid,
        "hits": hits,
        "rate": rate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "mean_latency": mean_latency,
        "results": results,
    }

def main():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("="*60)
    logger.info("MOVABLE FEAST 7 - COT STEP ABLATION")
    logger.info("="*60)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Model: {CONFIG['model']}")
    logger.info(f"N per variant: {CONFIG['trials_per_cell']}")
    
    all_results = {}
    
    for name, prompt in VARIANTS.items():
        all_results[name] = run_variant(name, prompt)
    
    # Summary table
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    logger.info(f"\n{'Variant':<20} {'Rate':>8} {'N':>5} {'CI':>20} {'Latency':>10}")
    logger.info("-"*65)
    
    for name in ["full", "no_examples", "scaffold_only", "examples_no_steps", "rules", "minimal"]:
        r = all_results[name]
        ci_str = f"[{r['ci_lower']:.1%}, {r['ci_upper']:.1%}]"
        logger.info(f"{name:<20} {r['rate']:>7.0%} {r['n']:>5} {ci_str:>20} {r['mean_latency']:>9.2f}s")
    
    # Analysis
    logger.info("\n" + "="*60)
    logger.info("ANALYSIS")
    logger.info("="*60)
    
    full_rate = all_results["full"]["rate"]
    no_ex_rate = all_results["no_examples"]["rate"]
    scaffold_rate = all_results["scaffold_only"]["rate"]
    examples_rate = all_results["examples_no_steps"]["rate"]
    
    logger.info(f"\nCoT-full: {full_rate:.0%}")
    logger.info(f"CoT-full minus examples: {no_ex_rate:.0%}")
    logger.info(f"Scaffold only: {scaffold_rate:.0%}")
    logger.info(f"Examples without steps: {examples_rate:.0%}")
    
    if no_ex_rate < full_rate - 0.05:
        logger.info("\n→ EXAMPLES MATTER: Removing examples drops performance.")
    elif no_ex_rate >= full_rate - 0.05:
        logger.info("\n→ SCAFFOLD SUFFICIENT: Examples may not be critical.")
    
    if examples_rate > scaffold_rate:
        logger.info("→ EXAMPLES ALONE HELP: Pattern recognition works.")
    else:
        logger.info("→ EXAMPLES ALONE INSUFFICIENT: Need the scaffold structure.")
    
    # Save
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "model": CONFIG["model"],
        "results": all_results,
        "timestamp": datetime.now().isoformat(),
    }
    
    path = os.path.join(SCRIPT_DIR, 'results', f"movable_feast_7_results_{run_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"\nSaved: {path}")
    
    try:
        out_path = f"/mnt/user-data/outputs/movable_feast_7_results_{run_id}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Also saved: {out_path}")
    except Exception as e:
        logger.warning(f"Could not save to outputs: {e}")
    
    return output

if __name__ == "__main__":
    main()
