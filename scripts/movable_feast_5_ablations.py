#!/usr/bin/env python3
"""
Project Vivarium v6.5 - Ablations & Robustness
==============================================

Addresses reviewer critiques with targeted experiments:

1. 30% LUNAR MISS ABLATIONS
   - Synonym panel: 大年初一, 春节第一天, 阴历正月初一, 岁首, 新春初一
   - Format panel: JSON-only vs minimal text vs bullet list
   - Temperature panel: T=0, T=0.2, T=0.7

2. ICL EXPANSION
   - 10-shot structured table
   - 20-shot structured table
   - CoT scaffold variant

3. TOOL WRONG-MAPPING CONTROL
   - Resolver gives WRONG lunar date → should fail or flip to wrong holiday

4. ADDITIONAL MODEL FAMILY
   - Yi-34B or DeepSeek-V2 (3 cells: zh Gregorian, zh lunar, Christmas)

5. EASTER EXACT COUNTS
   - Multiple years pooled, exact N and CIs
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
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'results', 'movable_feast_5.log'))
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================

CONFIG = {
    "version": "movable_feast_5_ablations",
    "primary_model": "qwen/qwen-2.5-72b-instruct",
    "secondary_models": [
        "deepseek/deepseek-chat",  # DeepSeek-V2
        # "01-ai/yi-34b-chat",  # Yi-34B (uncomment if available)
    ],
    "temperature_default": 0.0,
    "max_tokens": 500,
    "trials_per_cell": 20,
}

# ============================================================
# CORE TOKENS
# ============================================================

CORE_LNY = {"春节", "春節", "农历新年", "農曆新年", "lunar new year", "chinese new year"}
CORE_EASTER = {"easter", "easter sunday", "resurrection sunday", "pascha"}

# ============================================================
# PART 1: 30% LUNAR MISS ABLATIONS
# ============================================================

# Synonym variants for 农历正月初一
SYNONYM_PROMPTS = {
    "农历正月初一": "今天是农历正月初一。",
    "大年初一": "今天是大年初一。",
    "春节第一天": "今天是春节的第一天。",
    "阴历正月初一": "今天是阴历正月初一。",
    "岁首": "今天是农历岁首。",
    "新春初一": "今天是新春初一。",
}

SYNONYM_SUFFIX = """
问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# Format variants
FORMAT_PROMPTS = {
    "json_only": """今天是农历正月初一。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}""",

    "minimal_text": """今天是农历正月初一。

问题：今天有什么重要的节日或文化活动吗？

只回答节日名，无需解释。""",

    "bullet_list": """今天是农历正月初一。

问题：今天有什么重要的节日或文化活动吗？

请用列表格式回答：
- 节日1
- 节日2

如果没有节日，请回答"无"。""",
}

# ============================================================
# PART 2: ICL EXPANSION
# ============================================================

ICL_10_SHOT = """已知映射（示例）：
| 公历日期       | 农历日期  | 节日   |
|----------------|-----------|--------|
| 2024-02-10     | 正月初一  | 春节   |
| 2024-06-10     | 五月初五  | 端午节 |
| 2024-09-17     | 八月十五  | 中秋节 |
| 2023-01-22     | 正月初一  | 春节   |
| 2023-06-22     | 五月初五  | 端午节 |
| 2023-09-29     | 八月十五  | 中秋节 |
| 2022-02-01     | 正月初一  | 春节   |
| 2022-06-03     | 五月初五  | 端午节 |
| 2022-09-10     | 八月十五  | 中秋节 |
| 2025-10-06     | 八月十五  | 中秋节 |

请根据以上示例推断下方日期的节日：
| 公历日期       | 农历日期  | 节日   |
|----------------|-----------|--------|
| 2025-01-29     |    ?      |   ?    |

仅用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}"""

ICL_20_SHOT = """已知映射（示例）：
| 公历日期       | 农历日期  | 节日   |
|----------------|-----------|--------|
| 2024-02-10     | 正月初一  | 春节   |
| 2024-06-10     | 五月初五  | 端午节 |
| 2024-09-17     | 八月十五  | 中秋节 |
| 2023-01-22     | 正月初一  | 春节   |
| 2023-06-22     | 五月初五  | 端午节 |
| 2023-09-29     | 八月十五  | 中秋节 |
| 2022-02-01     | 正月初一  | 春节   |
| 2022-06-03     | 五月初五  | 端午节 |
| 2022-09-10     | 八月十五  | 中秋节 |
| 2021-02-12     | 正月初一  | 春节   |
| 2021-06-14     | 五月初五  | 端午节 |
| 2021-09-21     | 八月十五  | 中秋节 |
| 2020-01-25     | 正月初一  | 春节   |
| 2020-06-25     | 五月初五  | 端午节 |
| 2020-10-01     | 八月十五  | 中秋节 |
| 2019-02-05     | 正月初一  | 春节   |
| 2019-06-07     | 五月初五  | 端午节 |
| 2019-09-13     | 八月十五  | 中秋节 |
| 2025-05-31     | 五月初五  | 端午节 |
| 2025-10-06     | 八月十五  | 中秋节 |

请根据以上示例推断下方日期的节日：
| 公历日期       | 农历日期  | 节日   |
|----------------|-----------|--------|
| 2025-01-29     |    ?      |   ?    |

仅用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}"""

ICL_COT = """请按步骤推理：

步骤1：将公历日期转换为农历日期
步骤2：根据农历日期判断是否为节日

已知映射（示例）：
2024-02-10 = 农历正月初一 = 春节
2024-06-10 = 农历五月初五 = 端午节
2024-09-17 = 农历八月十五 = 中秋节
2023-01-22 = 农历正月初一 = 春节
2025-10-06 = 农历八月十五 = 中秋节

现在，请分析 2025-01-29：

步骤1：2025-01-29 的农历日期是？
步骤2：这个农历日期对应什么节日？

最后用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}"""

# ============================================================
# PART 3: TOOL WRONG-MAPPING CONTROL
# ============================================================

TOOL_CORRECT = """[日历解析器] 2025-01-29 = 农历正月初一（春节）

今天是2025年1月29日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

TOOL_WRONG = """[日历解析器] 2025-01-29 = 农历三月十五（无节日）

今天是2025年1月29日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""

# ============================================================
# PART 4: EASTER EXACT (Multiple Years)
# ============================================================

EASTER_DATES = [
    {"year": 2023, "gregorian": "2023-04-09", "weekday": "Sunday"},
    {"year": 2024, "gregorian": "2024-03-31", "weekday": "Sunday"},
    {"year": 2025, "gregorian": "2025-04-20", "weekday": "Sunday"},
]

def make_easter_prompt(date_info: dict, variant: str) -> str:
    if variant == "gregorian":
        return f"""Today's date is {date_info['gregorian']}, {date_info['weekday']}.

Question: Are there any important holidays or cultural events today?

Please respond only in JSON format:
{{"holidays": ["holiday1", "holiday2"]}}

If there are no holidays, respond: {{"holidays": []}}"""
    
    elif variant == "name_control":
        return f"""Today's date is {date_info['gregorian']}, {date_info['weekday']}. Today is Easter Sunday.

Question: Are there any important holidays or cultural events today?

Please respond only in JSON format:
{{"holidays": ["holiday1", "holiday2"]}}

If there are no holidays, respond: {{"holidays": []}}"""
    
    elif variant == "computus":
        return f"""Today's date is {date_info['gregorian']}, {date_info['weekday']}. 
Today is the first Sunday after the first full moon on or after March 21.

Question: Are there any important holidays or cultural events today?

Please respond only in JSON format:
{{"holidays": ["holiday1", "holiday2"]}}

If there are no holidays, respond: {{"holidays": []}}"""

# ============================================================
# SCORING
# ============================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFKC', text.lower().strip())

def parse_response_for_holidays(response: str) -> List[str]:
    """Extract holiday names from various response formats."""
    if not response:
        return []
    
    # Try JSON first
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
    
    # Try bullet list format
    lines = response.strip().split('\n')
    bullets = [l.strip().lstrip('-•').strip() for l in lines if l.strip().startswith(('-', '•'))]
    if bullets:
        return bullets
    
    # Return raw if short enough (minimal text format)
    if len(response.strip()) < 50 and response.strip() not in ["无", "没有", "none", ""]:
        return [response.strip()]
    
    return []

def check_recognition(response: str, core_tokens: set) -> Tuple[bool, List[str]]:
    if not response:
        return False, []
    
    items = parse_response_for_holidays(response)
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

def get_response(prompt: str, model: str = None, temperature: float = None) -> Tuple[Optional[str], int]:
    model = model or CONFIG["primary_model"]
    temperature = temperature if temperature is not None else CONFIG["temperature_default"]
    
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
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
             model: str = None, temperature: float = None) -> Dict:
    """Run a single test cell."""
    logger.info(f"\n{'='*50}")
    logger.info(f"CELL: {cell_id}")
    logger.info(f"Model: {model or CONFIG['primary_model']}")
    logger.info(f"Temperature: {temperature if temperature is not None else CONFIG['temperature_default']}")
    logger.info(f"{'='*50}")
    
    results = []
    hits = 0
    total_tokens = 0
    
    for i in range(n_trials):
        logger.info(f"Trial {i+1}/{n_trials}...")
        
        response, tokens = get_response(prompt, model, temperature)
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
        "model": model or CONFIG["primary_model"],
        "temperature": temperature if temperature is not None else CONFIG["temperature_default"],
        "n_valid": n_valid,
        "hits": hits,
        "rate": rate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "results": results,
        "total_tokens": total_tokens,
    }

# ============================================================
# ABLATION RUNNERS
# ============================================================

def run_synonym_ablation() -> Dict:
    """Part 1a: Synonym panel for lunar phrase."""
    logger.info("\n" + "="*60)
    logger.info("ABLATION 1a: SYNONYM PANEL")
    logger.info("="*60)
    
    results = {}
    for name, prefix in SYNONYM_PROMPTS.items():
        prompt = prefix + SYNONYM_SUFFIX
        results[name] = run_cell(
            f"synonym_{name}",
            prompt,
            CORE_LNY,
            CONFIG["trials_per_cell"]
        )
    return results

def run_format_ablation() -> Dict:
    """Part 1b: Format panel."""
    logger.info("\n" + "="*60)
    logger.info("ABLATION 1b: FORMAT PANEL")
    logger.info("="*60)
    
    results = {}
    for name, prompt in FORMAT_PROMPTS.items():
        results[name] = run_cell(
            f"format_{name}",
            prompt,
            CORE_LNY,
            CONFIG["trials_per_cell"]
        )
    return results

def run_temperature_ablation() -> Dict:
    """Part 1c: Temperature panel."""
    logger.info("\n" + "="*60)
    logger.info("ABLATION 1c: TEMPERATURE PANEL")
    logger.info("="*60)
    
    prompt = FORMAT_PROMPTS["json_only"]  # Use standard prompt
    results = {}
    for temp in [0.0, 0.2, 0.7]:
        results[f"T={temp}"] = run_cell(
            f"temp_{temp}",
            prompt,
            CORE_LNY,
            CONFIG["trials_per_cell"],
            temperature=temp
        )
    return results

def run_icl_expansion() -> Dict:
    """Part 2: ICL expansion (10-shot, 20-shot, CoT)."""
    logger.info("\n" + "="*60)
    logger.info("PART 2: ICL EXPANSION")
    logger.info("="*60)
    
    results = {}
    
    results["10_shot"] = run_cell("icl_10shot", ICL_10_SHOT, CORE_LNY, CONFIG["trials_per_cell"])
    results["20_shot"] = run_cell("icl_20shot", ICL_20_SHOT, CORE_LNY, CONFIG["trials_per_cell"])
    results["cot"] = run_cell("icl_cot", ICL_COT, CORE_LNY, CONFIG["trials_per_cell"])
    
    return results

def run_tool_control() -> Dict:
    """Part 3: Tool wrong-mapping control."""
    logger.info("\n" + "="*60)
    logger.info("PART 3: TOOL WRONG-MAPPING CONTROL")
    logger.info("="*60)
    
    results = {}
    results["correct_mapping"] = run_cell("tool_correct", TOOL_CORRECT, CORE_LNY, CONFIG["trials_per_cell"])
    results["wrong_mapping"] = run_cell("tool_wrong", TOOL_WRONG, CORE_LNY, CONFIG["trials_per_cell"])
    
    return results

def run_easter_exact() -> Dict:
    """Part 4: Easter exact counts across years."""
    logger.info("\n" + "="*60)
    logger.info("PART 4: EASTER EXACT COUNTS")
    logger.info("="*60)
    
    results = {"gregorian": [], "name_control": [], "computus": []}
    
    for date_info in EASTER_DATES:
        for variant in ["gregorian", "name_control", "computus"]:
            prompt = make_easter_prompt(date_info, variant)
            cell_result = run_cell(
                f"easter_{date_info['year']}_{variant}",
                prompt,
                CORE_EASTER,
                CONFIG["trials_per_cell"]
            )
            cell_result["year"] = date_info["year"]
            results[variant].append(cell_result)
    
    # Pool results
    for variant in list(results.keys()):
        total_hits = sum(r["hits"] for r in results[variant])
        total_n = sum(r["n_valid"] for r in results[variant])
        pooled_rate = total_hits / total_n if total_n > 0 else 0
        ci_lower, ci_upper = wilson_ci(total_hits, total_n)
        results[f"{variant}_pooled"] = {
            "total_hits": total_hits,
            "total_n": total_n,
            "rate": pooled_rate,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
        }
    
    return results

def run_cross_family() -> Dict:
    """Part 5: Cross-family validation (DeepSeek)."""
    logger.info("\n" + "="*60)
    logger.info("PART 5: CROSS-FAMILY (DeepSeek)")
    logger.info("="*60)
    
    results = {}
    
    for model in CONFIG["secondary_models"]:
        model_key = model.split("/")[-1]
        
        # ZH Gregorian LNY
        prompt_greg = """今天是2025年1月29日，星期三。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""
        
        results[f"{model_key}_gregorian"] = run_cell(
            f"{model_key}_gregorian",
            prompt_greg,
            CORE_LNY,
            CONFIG["trials_per_cell"],
            model=model
        )
        
        # ZH Lunar phrase
        prompt_lunar = """今天是农历正月初一。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""
        
        results[f"{model_key}_lunar"] = run_cell(
            f"{model_key}_lunar",
            prompt_lunar,
            CORE_LNY,
            CONFIG["trials_per_cell"],
            model=model
        )
        
        # Christmas control
        prompt_xmas = """今天是2025年12月25日，星期四。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{"holidays": ["节日名称1", "节日名称2"]}

如果没有节日，请返回：{"holidays": []}"""
        
        results[f"{model_key}_christmas"] = run_cell(
            f"{model_key}_christmas",
            prompt_xmas,
            {"圣诞节", "圣诞", "christmas"},
            CONFIG["trials_per_cell"],
            model=model
        )
    
    return results

# ============================================================
# MAIN
# ============================================================

def run_all():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 60)
    logger.info("MOVABLE FEAST 5 - ABLATIONS & ROBUSTNESS")
    logger.info("=" * 60)
    logger.info(f"Run ID: {run_id}")
    logger.info("")
    
    all_results = {}
    total_tokens = 0
    
    # Part 1: 30% miss ablations
    all_results["synonym_ablation"] = run_synonym_ablation()
    all_results["format_ablation"] = run_format_ablation()
    all_results["temperature_ablation"] = run_temperature_ablation()
    
    # Part 2: ICL expansion
    all_results["icl_expansion"] = run_icl_expansion()
    
    # Part 3: Tool control
    all_results["tool_control"] = run_tool_control()
    
    # Part 4: Easter exact
    all_results["easter_exact"] = run_easter_exact()
    
    # Part 5: Cross-family (if models available)
    try:
        all_results["cross_family"] = run_cross_family()
    except Exception as e:
        logger.warning(f"Cross-family tests failed: {e}")
        all_results["cross_family"] = {"error": str(e)}
    
    # Calculate total tokens
    def sum_tokens(d):
        total = 0
        if isinstance(d, dict):
            if "total_tokens" in d:
                total += d["total_tokens"]
            for v in d.values():
                total += sum_tokens(v)
        elif isinstance(d, list):
            for item in d:
                total += sum_tokens(item)
        return total
    
    total_tokens = sum_tokens(all_results)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    
    # Synonym results
    logger.info("\nSYNONYM PANEL:")
    for name, result in all_results.get("synonym_ablation", {}).items():
        if isinstance(result, dict) and "rate" in result:
            logger.info(f"  {name}: {result['rate']:.1%}")
    
    # Format results
    logger.info("\nFORMAT PANEL:")
    for name, result in all_results.get("format_ablation", {}).items():
        if isinstance(result, dict) and "rate" in result:
            logger.info(f"  {name}: {result['rate']:.1%}")
    
    # Temperature results
    logger.info("\nTEMPERATURE PANEL:")
    for name, result in all_results.get("temperature_ablation", {}).items():
        if isinstance(result, dict) and "rate" in result:
            logger.info(f"  {name}: {result['rate']:.1%}")
    
    # ICL results
    logger.info("\nICL EXPANSION:")
    for name, result in all_results.get("icl_expansion", {}).items():
        if isinstance(result, dict) and "rate" in result:
            logger.info(f"  {name}: {result['rate']:.1%}")
    
    # Tool control
    logger.info("\nTOOL CONTROL:")
    for name, result in all_results.get("tool_control", {}).items():
        if isinstance(result, dict) and "rate" in result:
            logger.info(f"  {name}: {result['rate']:.1%}")
    
    # Easter pooled
    logger.info("\nEASTER (POOLED):")
    easter = all_results.get("easter_exact", {})
    for variant in ["gregorian_pooled", "name_control_pooled", "computus_pooled"]:
        if variant in easter:
            r = easter[variant]
            logger.info(f"  {variant}: {r['total_hits']}/{r['total_n']} = {r['rate']:.1%}")
    
    logger.info(f"\nTotal tokens: {total_tokens:,}")
    
    # Save
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "results": all_results,
        "total_tokens": total_tokens,
        "timestamp": datetime.now().isoformat(),
    }
    
    path = os.path.join(SCRIPT_DIR, 'results', f"movable_feast_5_results_{run_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved: {path}")

    return output

if __name__ == "__main__":
    run_all()
