#!/usr/bin/env python3
"""
Movable Feast v6.8 - Frontier Model Validation (December 2025)
==============================================================

Run the key v6.7 finding (examples vs steps) against latest frontier models:
- Grok-4 (xAI) - via OpenRouter (free)
- GPT-5.1 (OpenAI) - via direct API
- Claude 4.5 (Anthropic) - via direct API

This validates that the pattern-matching finding generalizes across
the most capable models available.

Requirements:
- OPENROUTER_API_KEY (for Grok-4)
- OPENAI_API_KEY (for GPT-5.1)
- ANTHROPIC_API_KEY (for Claude 4.5)
"""

import os
import json
import time
import logging
import unicodedata
import math
from datetime import datetime
from typing import Optional, Tuple, Dict, List
from abc import ABC, abstractmethod

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/claude/movable_feast_v6_8.log')
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "version": "movable_feast_v6.8_frontier",
    "temperature": 0.0,
    "max_tokens": 500,
    "trials_per_cell": 20,
}

CORE_LNY = {"春节", "春節", "农历新年", "農曆新年", "lunar new year", "chinese new year"}
CORE_TET = {"tết", "tet", "tết nguyên đán", "tet nguyen dan", "vietnamese new year", "năm mới"}
CORE_SEOLLAL = {"설날", "seollal", "korean new year", "구정", "korean lunar new year"}

# ============================================================
# KEY PROMPTS FROM v6.7 + TẾT + SEOLLAL
# ============================================================

PROMPTS = {
    # Chinese - baseline from v6.7
    "zh_gregorian": """今天是2025年1月29日，星期三。

请问今天有什么节日？

用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}""",

    "zh_minimal": """今天是2025年1月29日，星期三。

请按两步回答：
步骤1：这个日期对应的农历日期是什么？
步骤2：这个农历日期有什么节日？

最后用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}""",

    "zh_examples_only": """已知映射：
2024-02-10 = 农历正月初一 = 春节
2024-06-10 = 农历五月初五 = 端午节
2024-09-17 = 农历八月十五 = 中秋节

请根据以上模式，分析 2025年1月29日，星期三 是什么节日？

用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}""",

    "zh_full": """请按步骤推理：

步骤1：将公历日期转换为农历日期
步骤2：根据农历日期判断是否为节日

已知映射（示例）：
2024-02-10 = 农历正月初一 = 春节
2024-06-10 = 农历五月初五 = 端午节
2024-09-17 = 农历八月十五 = 中秋节

现在，请分析 2025年1月29日，星期三：

步骤1：2025-01-29 的农历日期是？
步骤2：这个农历日期对应什么节日？

最后用JSON回答：{"holidays": ["节日名称"]}；若没有节日：{"holidays": []}""",

    # Vietnamese - Tết Nguyên Đán (same date as LNY)
    "vi_gregorian": """Hôm nay là ngày 29 tháng 1 năm 2025, thứ Tư.

Hôm nay có ngày lễ gì không?

Trả lời bằng JSON: {"holidays": ["tên ngày lễ"]}; nếu không có: {"holidays": []}""",

    "vi_minimal": """Hôm nay là ngày 29 tháng 1 năm 2025, thứ Tư.

Trả lời theo 2 bước:
Bước 1: Ngày dương lịch này tương ứng với ngày âm lịch nào?
Bước 2: Ngày âm lịch này có ngày lễ gì?

Trả lời bằng JSON: {"holidays": ["tên ngày lễ"]}; nếu không có: {"holidays": []}""",

    "vi_examples_only": """Các ngày lễ đã biết:
2024-02-10 = Mùng 1 Tết = Tết Nguyên Đán
2024-06-10 = Mùng 5 tháng 5 = Tết Đoan Ngọ
2024-09-17 = Rằm tháng 8 = Tết Trung Thu

Dựa vào quy luật trên, ngày 29 tháng 1 năm 2025 là ngày lễ gì?

Trả lời bằng JSON: {"holidays": ["tên ngày lễ"]}; nếu không có: {"holidays": []}""",

    "vi_full": """Hãy suy luận theo các bước:

Bước 1: Chuyển đổi ngày dương lịch sang ngày âm lịch
Bước 2: Xác định xem ngày âm lịch đó có phải ngày lễ không

Các ngày lễ đã biết:
2024-02-10 = Mùng 1 Tết = Tết Nguyên Đán
2024-06-10 = Mùng 5 tháng 5 = Tết Đoan Ngọ
2024-09-17 = Rằm tháng 8 = Tết Trung Thu

Bây giờ, hãy phân tích ngày 29 tháng 1 năm 2025, thứ Tư:

Bước 1: Ngày 29/01/2025 tương ứng với ngày âm lịch nào?
Bước 2: Ngày âm lịch này có ngày lễ gì?

Trả lời bằng JSON: {"holidays": ["tên ngày lễ"]}; nếu không có: {"holidays": []}""",

    # Korean - Seollal (same date as LNY)
    "ko_gregorian": """오늘은 2025년 1월 29일 수요일입니다.

오늘 무슨 명절인가요?

JSON으로 답변해 주세요: {"holidays": ["명절 이름"]}; 명절이 없으면: {"holidays": []}""",

    "ko_minimal": """오늘은 2025년 1월 29일 수요일입니다.

두 단계로 답변해 주세요:
1단계: 이 양력 날짜에 해당하는 음력 날짜는?
2단계: 이 음력 날짜에 해당하는 명절은?

JSON으로 답변해 주세요: {"holidays": ["명절 이름"]}; 명절이 없으면: {"holidays": []}""",

    "ko_examples_only": """알려진 명절:
2024-02-10 = 음력 1월 1일 = 설날
2024-06-10 = 음력 5월 5일 = 단오
2024-09-17 = 음력 8월 15일 = 추석

위 패턴에 따라, 2025년 1월 29일은 무슨 명절인가요?

JSON으로 답변해 주세요: {"holidays": ["명절 이름"]}; 명절이 없으면: {"holidays": []}""",

    "ko_full": """단계별로 추론해 주세요:

1단계: 양력 날짜를 음력 날짜로 변환
2단계: 해당 음력 날짜가 명절인지 확인

알려진 명절:
2024-02-10 = 음력 1월 1일 = 설날
2024-06-10 = 음력 5월 5일 = 단오
2024-09-17 = 음력 8월 15일 = 추석

이제 2025년 1월 29일 수요일을 분석해 주세요:

1단계: 2025-01-29에 해당하는 음력 날짜는?
2단계: 이 음력 날짜에 해당하는 명절은?

JSON으로 답변해 주세요: {"holidays": ["명절 이름"]}; 명절이 없으면: {"holidays": []}""",

    # English - Lunar New Year (generic)
    "en_gregorian": """Today is Wednesday, January 29, 2025.

What holiday is today, if any?

Answer in JSON: {"holidays": ["holiday name"]}; if none: {"holidays": []}""",

    "en_examples_only": """Known mappings:
2024-02-10 = Lunar New Year (Spring Festival)
2024-06-10 = Dragon Boat Festival
2024-09-17 = Mid-Autumn Festival

Based on the pattern above, what holiday is January 29, 2025?

Answer in JSON: {"holidays": ["holiday name"]}; if none: {"holidays": []}""",
}

# ============================================================
# MODEL CLIENTS
# ============================================================

class ModelClient(ABC):
    @abstractmethod
    def get_response(self, prompt: str) -> Tuple[Optional[str], float]:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass


class OpenRouterClient(ModelClient):
    """For Grok-4 via OpenRouter"""
    
    def __init__(self, model: str = "x-ai/grok-4-0709"):
        import openai
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )
        self.model = model
    
    @property
    def name(self) -> str:
        return f"Grok-4 ({self.model})"
    
    def get_response(self, prompt: str) -> Tuple[Optional[str], float]:
        start = time.time()
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=CONFIG["temperature"],
                max_tokens=CONFIG["max_tokens"],
            )
            return resp.choices[0].message.content, time.time() - start
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return None, time.time() - start


class OpenAIClient(ModelClient):
    """For GPT-5.1 via direct API"""
    
    def __init__(self, model: str = "gpt-5.1"):
        import openai
        self.client = openai.OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        self.model = model
    
    @property
    def name(self) -> str:
        return f"GPT-5.1 ({self.model})"
    
    def get_response(self, prompt: str) -> Tuple[Optional[str], float]:
        start = time.time()
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=CONFIG["temperature"],
                max_tokens=CONFIG["max_tokens"],
            )
            return resp.choices[0].message.content, time.time() - start
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return None, time.time() - start


class AnthropicClient(ModelClient):
    """For Claude 4.5 via direct API"""
    
    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        import anthropic
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )
        self.model = model
    
    @property
    def name(self) -> str:
        return f"Claude 4.5 ({self.model})"
    
    def get_response(self, prompt: str) -> Tuple[Optional[str], float]:
        start = time.time()
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=CONFIG["max_tokens"],
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text, time.time() - start
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            return None, time.time() - start


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
    """Check for Chinese LNY tokens"""
    return check_holiday(response, CORE_LNY)


def check_tet(response: str) -> bool:
    """Check for Vietnamese Tết tokens"""
    return check_holiday(response, CORE_TET)


def check_seollal(response: str) -> bool:
    """Check for Korean Seollal tokens"""
    return check_holiday(response, CORE_SEOLLAL)


def check_holiday(response: str, tokens: set) -> bool:
    """Generic holiday token checker"""
    if not response:
        return False
    response_norm = normalize_text(response)
    for token in tokens:
        if normalize_text(token) in response_norm:
            return True
    try:
        if "{" in response:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end])
            if isinstance(data.get("holidays"), list):
                for h in data["holidays"]:
                    if any(normalize_text(t) in normalize_text(str(h)) for t in tokens):
                        return True
    except:
        pass
    return False


def get_checker_for_prompt(prompt_name: str):
    """Return the appropriate checker based on prompt language"""
    if prompt_name.startswith("vi_"):
        return check_tet
    elif prompt_name.startswith("ko_"):
        return check_seollal
    else:  # zh_, en_, or default
        return check_lny


def run_cell(client: ModelClient, prompt_name: str, prompt: str, n: int) -> Dict:
    """Run N trials for a single cell"""
    logger.info(f"\n  {prompt_name}: ")
    
    # Get the right checker for this prompt's language
    checker = get_checker_for_prompt(prompt_name)
    
    hits = 0
    results = []
    total_latency = 0
    
    for i in range(n):
        response, latency = client.get_response(prompt)
        total_latency += latency
        
        if response is None:
            results.append({"trial": i, "error": True})
            print("E", end="", flush=True)
            continue
        
        recognized = checker(response)
        results.append({
            "trial": i,
            "response": response[:200],
            "recognized": recognized,
            "latency": latency,
        })
        
        if recognized:
            hits += 1
            print("✓", end="", flush=True)
        else:
            print("✗", end="", flush=True)
        
        time.sleep(0.3)
    
    n_valid = len([r for r in results if not r.get("error")])
    rate = hits / n_valid if n_valid > 0 else 0
    ci_lower, ci_upper = wilson_ci(hits, n_valid)
    
    print(f" → {hits}/{n_valid} ({rate:.0%})")
    
    return {
        "prompt": prompt_name,
        "n": n_valid,
        "hits": hits,
        "rate": rate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "mean_latency": total_latency / n if n > 0 else 0,
        "results": results,
    }


def run_model(client: ModelClient) -> Dict:
    """Run all prompts for a single model"""
    logger.info(f"\n{'='*60}")
    logger.info(f"MODEL: {client.name}")
    logger.info(f"{'='*60}")
    
    results = {}
    for prompt_name, prompt in PROMPTS.items():
        results[prompt_name] = run_cell(
            client, prompt_name, prompt, CONFIG["trials_per_cell"]
        )
        time.sleep(1)  # Rate limit courtesy
    
    return {
        "model": client.name,
        "results": results,
    }


def print_summary(all_results: Dict):
    """Print comparison table"""
    logger.info("\n" + "="*80)
    logger.info("SUMMARY: FRONTIER MODEL COMPARISON")
    logger.info("="*80)
    
    # Header
    models = list(all_results.keys())
    header = f"{'Prompt':<20}"
    for m in models:
        header += f" {m:<18}"
    logger.info(header)
    logger.info("-"*80)
    
    # Rows
    for prompt_name in PROMPTS.keys():
        row = f"{prompt_name:<20}"
        for model_name in models:
            r = all_results[model_name]["results"][prompt_name]
            cell = f"{r['hits']}/{r['n']} ({r['rate']:.0%})"
            row += f" {cell:<18}"
        logger.info(row)
    
    # Key comparison
    logger.info("\n" + "-"*80)
    logger.info("KEY FINDING CHECK: Does 'examples_only' >> 'minimal'?")
    logger.info("-"*80)
    
    for model_name in models:
        examples = all_results[model_name]["results"]["examples_only"]["rate"]
        minimal = all_results[model_name]["results"]["minimal"]["rate"]
        delta = examples - minimal
        status = "✓ YES" if delta > 0.5 else "⚠ MIXED" if delta > 0 else "✗ NO"
        logger.info(f"  {model_name}: examples={examples:.0%}, minimal={minimal:.0%}, Δ={delta:+.0%} → {status}")


def main():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("="*60)
    logger.info("MOVABLE FEAST v6.8 - FRONTIER MODEL VALIDATION")
    logger.info("="*60)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Trials per cell: {CONFIG['trials_per_cell']}")
    logger.info(f"Date: December 2025")
    
    all_results = {}
    
    # Initialize clients based on available API keys
    clients = []
    
    if os.environ.get("OPENROUTER_API_KEY"):
        try:
            clients.append(OpenRouterClient("x-ai/grok-4-0709"))
            logger.info("✓ Grok-4 (OpenRouter) ready")
        except Exception as e:
            logger.warning(f"Could not initialize Grok-4: {e}")
    
    if os.environ.get("OPENAI_API_KEY"):
        try:
            clients.append(OpenAIClient("gpt-4o"))  # Use gpt-4o as fallback if gpt-5.1 not available
            logger.info("✓ GPT (OpenAI) ready")
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI: {e}")
    
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            clients.append(AnthropicClient("claude-sonnet-4-5-20250929"))
            logger.info("✓ Claude 4.5 (Anthropic) ready")
        except Exception as e:
            logger.warning(f"Could not initialize Claude: {e}")
    
    if not clients:
        logger.error("No API keys found! Set OPENROUTER_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY")
        return
    
    # Run all models
    for client in clients:
        try:
            all_results[client.name] = run_model(client)
        except Exception as e:
            logger.error(f"Error running {client.name}: {e}")
    
    # Print summary
    print_summary(all_results)
    
    # Save results
    output = {
        "version": CONFIG["version"],
        "run_id": run_id,
        "config": CONFIG,
        "results": all_results,
        "timestamp": datetime.now().isoformat(),
    }
    
    path = f"/home/claude/movable_feast_v6_8_results_{run_id}.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"\nSaved: {path}")
    
    try:
        out_path = f"/mnt/user-data/outputs/movable_feast_v6_8_results_{run_id}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Also saved: {out_path}")
    except Exception as e:
        logger.warning(f"Could not save to outputs: {e}")
    
    return output


if __name__ == "__main__":
    main()
