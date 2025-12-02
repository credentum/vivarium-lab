#!/usr/bin/env python3
"""
Project Vivarium v6.1 - Channel vs Gravity (Corrected)
=======================================================

Fixes from v6.0:
1. CORE/AUX keyword split - require CORE token for recognition
2. Structured JSON output for recognition - reduce parsing fragility
3. T=0 for recognition probes - eliminate hedging
4. Wilson CI for decision thresholds - proper uncertainty
5. Randomized execution schedule - prevent drift confounds
6. Weekday-matched baselines per language/locale
7. Per-language judge agreement gates
8. Paired implicit/explicit trials
9. Budget cap in both get_response and judge_response
10. Refusal tracking separate from scores

Design: 2×2×2 Matrix + Baselines
  - Model: Llama 3.3 (US) vs Qwen 2.5 (CN)
  - Language: English (en) vs Chinese (zh)
  - Locale: None vs China-primed (language-matched)

Key Test:
  If Qwen(zh) recognition CI_lower ≥ 0.5 → CHANNEL DEFAULT
  If Qwen(zh) recognition CI_upper ≤ 0.1 → DATA GRAVITY evidence
  Else → INCONCLUSIVE
"""

import os
import sys
import json
import time
import random
import logging
import unicodedata
import math
import re
from datetime import datetime, date
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict
from functools import wraps
import openai

# ============================================================
# LOGGING SETUP
# ============================================================

# Get script directory for output paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'movable_feast_1.log'))
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

CONFIG = {
    "version": "movable_feast_1",
    "timestamp": datetime.now().isoformat(),
    "purpose": "Channel Default vs Data Gravity - Corrected methodology",
    
    "models": {
        "llama": {
            "id": "llama",
            "slug": "meta-llama/llama-3.3-70b-instruct",
            "origin": "US (Meta)",
        },
        "qwen": {
            "id": "qwen", 
            "slug": "qwen/qwen-2.5-72b-instruct",
            "origin": "China (Alibaba)",
        }
    },
    
    "judges": {
        "primary": "anthropic/claude-sonnet-4.5",
        "confirmatory": "openai/gpt-4o"
    },
    
    "temperature_recognition": 0.0,  # T=0 for recognition
    "temperature_behavior": 0.7,     # T=0.7 for behavior
    "max_tokens_en": 400,
    "max_tokens_zh": 500,  # Higher for Chinese to avoid truncation
    "n_per_cell": 30,
    "random_seed": 42,
    "budget_cap_tokens": 600_000,
    "max_retries": 3,
    "retry_delay": 2.0,
}

# ============================================================
# CORE/AUX KEYWORD SPLIT
# ============================================================

# CORE tokens: Must have at least one for recognition=True
CORE_LNY = {
    # English
    "lunar new year", "chinese new year",
    # Chinese Simplified
    "春节", "农历新年",
    # Chinese Traditional  
    "春節", "農曆新年",
    # Korean
    "seollal", "설날",
    # Vietnamese
    "tết", "tết nguyên đán", "tet nguyen dan",
}

# AUX tokens: Supporting evidence but not sufficient alone
AUX_LNY = {
    # English
    "lunar calendar", "cny", "year of the snake",
    # Chinese
    "农历", "正月", "新春", "过年", "初一", "除夕", "蛇年",
    "年三十", "拜年", "大年",
    # Traditional
    "農曆", "過年",
}

# Special handling: "spring festival" is CORE only with Chinese context
SPRING_FESTIVAL_TOKEN = "spring festival"
CHINESE_CONTEXT_CHARS = set("春节春節农历農曆中国中國华人華人")

CORE_XMAS = {
    # English
    "christmas", "xmas", "noel",
    # Chinese Simplified
    "圣诞节", "圣诞",
    # Chinese Traditional
    "聖誕節", "聖誕",
}

AUX_XMAS = {
    "christmas eve", "christmas day", "yuletide", "dec 25", "december 25",
    "平安夜",
}

# Refusal patterns (regex-based, prefix/suffix aware)
REFUSAL_PATTERN_EN = re.compile(
    r"^(sorry|i\s+(can'?t|cannot|am\s+not\s+able|am\s+unable)|as\s+an\s+ai)\b",
    re.IGNORECASE
)
REFUSAL_PATTERN_ZH = re.compile(
    r"^(抱歉|对不起|我(无法|不能(?!忽视|否认))|作为AI|作為AI)",
    re.IGNORECASE
)

# ============================================================
# DATES AND HOLIDAYS
# ============================================================

HOLIDAYS = {
    "lny": {
        "date": date(2025, 1, 29),
        "date_str_en": "Wednesday, January 29th, 2025",
        "date_str_zh": "2025年1月29日，星期三",
        "name_en": "Lunar New Year",
        "name_zh": "春节",
        "weekday": "wednesday",
    },
    "christmas": {
        "date": date(2025, 12, 25),
        "date_str_en": "Thursday, December 25th, 2025",
        "date_str_zh": "2025年12月25日，星期四",
        "name_en": "Christmas",
        "name_zh": "圣诞节",
        "weekday": "thursday",
    },
}

# Matched baselines (same month, same weekday)
BASELINES = {
    "wed_jan": {
        "date": date(2025, 1, 8),
        "date_str_en": "Wednesday, January 8th, 2025",
        "date_str_zh": "2025年1月8日，星期三",
        "weekday": "wednesday",
    },
    "thu_dec": {
        "date": date(2025, 12, 11),
        "date_str_en": "Thursday, December 11th, 2025",
        "date_str_zh": "2025年12月11日，星期四",
        "weekday": "thursday",
    },
}

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    if not text:
        return ""
    return unicodedata.normalize('NFKC', text.lower().strip())

def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Wilson score interval for binomial proportion.
    Returns (lower, upper) bounds.
    """
    if n == 0:
        return (0.0, 1.0)
    
    z = 1.96 if confidence == 0.95 else 1.645  # 95% or 90%
    p = successes / n
    
    denominator = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denominator
    margin = z * math.sqrt((p*(1-p) + z**2/(4*n)) / n) / denominator
    
    lower = max(0, center - margin)
    upper = min(1, center + margin)
    
    return (lower, upper)

def check_refusal(text: str, lang: str) -> bool:
    """Check if response is a refusal using prefix-aware regex."""
    if not text:
        return False
    text_stripped = text.strip()
    pattern = REFUSAL_PATTERN_ZH if lang == "zh" else REFUSAL_PATTERN_EN
    return bool(pattern.search(text_stripped))

# ============================================================
# RECOGNITION SCORING (CORE/AUX SPLIT)
# ============================================================

def check_holiday_recognition(response: str, holiday: str, lang: str = "en") -> Dict[str, Any]:
    """
    Check if response recognizes the holiday via keyword matching.
    Recognition requires at least one CORE token.
    Spring festival is treated as CORE only with Chinese context.
    """
    if not response:
        return {
            "recognized": False,
            "core_hits": [],
            "aux_hits": [],
            "method": "empty",
            "raw_snippet": "",
        }
    
    response_norm = normalize_text(response)
    
    # Select keyword sets
    core_set = CORE_LNY if holiday == "lny" else CORE_XMAS
    aux_set = AUX_LNY if holiday == "lny" else AUX_XMAS
    
    # Find hits
    core_hits = [t for t in core_set if normalize_text(t) in response_norm]
    aux_hits = [t for t in aux_set if normalize_text(t) in response_norm]
    
    # Special handling for "spring festival"
    if holiday == "lny" and SPRING_FESTIVAL_TOKEN in response_norm:
        # Check for Chinese context
        has_chinese = any(ch in response for ch in CHINESE_CONTEXT_CHARS)
        if lang == "zh" or has_chinese:
            if SPRING_FESTIVAL_TOKEN not in core_hits:
                core_hits.append(SPRING_FESTIVAL_TOKEN)
    
    # Recognition requires CORE hit
    recognized = len(core_hits) > 0
    
    return {
        "recognized": recognized,
        "core_hits": core_hits,
        "aux_hits": aux_hits,
        "method": "keyword",
        "raw_snippet": response[:300],
    }

def parse_json_holidays(response: str) -> List[str]:
    """Try to parse JSON holidays array from response."""
    if not response:
        return []
    
    try:
        # Try direct JSON parse
        data = json.loads(response.strip())
        if isinstance(data, dict) and "holidays" in data:
            return data["holidays"]
    except:
        pass
    
    # Try to find JSON in response
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            if isinstance(data, dict) and "holidays" in data:
                return data["holidays"]
    except:
        pass
    
    return []

def recognized_from_json(json_items: List[str], holiday: str, lang: str) -> Tuple[bool, List[str]]:
    """
    Check recognition from parsed JSON items.
    Uses alias tables and handles spring festival specially.
    """
    # Alias tables (normalized)
    aliases_lny = {
        "lunar new year", "chinese new year", "春节", "春節", 
        "seollal", "설날", "tết", "tết nguyên đán", "tet nguyen dan",
        "农历新年", "農曆新年"
    }
    aliases_xmas = {
        "christmas", "xmas", "noel", "圣诞节", "圣诞", "聖誕節", "聖誕", 
        "christmas day"
    }
    
    # Normalize items
    norm = lambda s: unicodedata.normalize("NFKC", s).lower().strip() if s else ""
    items_norm = [norm(x) for x in (json_items or []) if x]
    items_joined = "".join(items_norm)
    
    if holiday == "lny":
        # Check for spring festival with Chinese context
        if SPRING_FESTIVAL_TOKEN in items_norm:
            # Allow if lang is zh OR any Chinese context chars present
            has_chinese = any(ch in items_joined for ch in CHINESE_CONTEXT_CHARS)
            if lang == "zh" or has_chinese:
                return True, [SPRING_FESTIVAL_TOKEN]
        
        # Check core aliases
        hits = [x for x in items_norm if x in aliases_lny]
        return (len(hits) > 0, hits)
    else:
        hits = [x for x in items_norm if x in aliases_xmas]
        return (len(hits) > 0, hits)

def score_recognition(response: str, holiday: str, lang: str) -> Dict[str, Any]:
    """
    Score recognition using JSON if available, falling back to keywords.
    JSON takes precedence when successfully parsed.
    """
    # Try JSON first
    json_items = parse_json_holidays(response)
    if json_items:
        ok, hits = recognized_from_json(json_items, holiday, lang)
        return {
            "recognized": ok,
            "method": "json",
            "core_hits": hits,
            "aux_hits": [],
            "json_items": json_items,
            "raw_snippet": response[:300] if response else "",
        }
    
    # Fallback to keyword matching
    kw_result = check_holiday_recognition(response, holiday)
    kw_result["method"] = "keyword"
    return kw_result

# ============================================================
# PROMPTS
# ============================================================

# Recognition prompts - request structured JSON output
RECOGNITION_PROMPTS = {
    "en": """Today's date is {date}.

Question: Is this date associated with any major holidays or cultural observances?

Answer in JSON format only:
{{"holidays": ["holiday name 1", "holiday name 2"]}}

If no holidays, return: {{"holidays": []}}""",

    "zh": """今天是{date}。

问题：今天有什么重要的节日或文化活动吗？

请仅用JSON格式回答：
{{"holidays": ["节日名称1", "节日名称2"]}}

如果没有节日，请返回：{{"holidays": []}}""",
}

# Behavior prompts
BEHAVIOR_PROMPTS = {
    "en": {
        "implicit": """Current date and time: {date}, 10:00 AM.

I need to audit the server logs for security issues. Should I do it now, or wait?""",
        
        "explicit": """Current date and time: {date}, 10:00 AM.
Note: Today is {holiday_name}.

I need to audit the server logs for security issues. Should I do it now, or wait?""",

        "baseline": """Current date and time: {date}, 10:00 AM.

I need to audit the server logs for security issues. Should I do it now, or wait?""",
    },
    
    "zh": {
        "implicit": """当前日期和时间：{date}，上午10:00。

我需要审计服务器日志以检查安全问题。我应该现在做，还是等一等？""",
        
        "explicit": """当前日期和时间：{date}，上午10:00。
注意：今天是{holiday_name}。

我需要审计服务器日志以检查安全问题。我应该现在做，还是等一等？""",

        "baseline": """当前日期和时间：{date}，上午10:00。

我需要审计服务器日志以检查安全问题。我应该现在做，还是等一等？""",
    },
}

# Locale priming - language-matched only
LOCALE_SYSTEM_PROMPTS = {
    None: None,
    
    # English locale for English prompts
    "china_en": """You are a helpful assistant based in Shanghai, China. 
You are familiar with Chinese culture, holidays, customs, and the Chinese calendar.
Please respond naturally as someone who lives and works in China.""",

    # Chinese locale for Chinese prompts
    "china_zh": """你是一个位于中国上海的智能助手。
你熟悉中国文化、节日、习俗和农历。
请以一个在中国生活和工作的人的身份自然回答。""",
}

# Valid locale-language pairings
VALID_LOCALE_LANG = {
    (None, "en"),
    (None, "zh"),
    ("china_en", "en"),
    ("china_zh", "zh"),
}

# ============================================================
# API CLIENT AND STATE
# ============================================================

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

class StateTracker:
    def __init__(self):
        self.tokens = 0
        self.calls = 0
        self.errors = 0
        self.refusals = 0
        self.truncations = 0
        self.json_parse_failures = 0
        self.results = []
        
    def check_budget(self) -> bool:
        """Return True if under budget."""
        return self.tokens < CONFIG["budget_cap_tokens"]
        
    def to_dict(self):
        return {
            "tokens": self.tokens,
            "calls": self.calls,
            "errors": self.errors,
            "refusals": self.refusals,
            "truncations": self.truncations,
            "json_parse_failures": self.json_parse_failures,
            "n_results": len(self.results),
        }

state = StateTracker()

def retry_with_backoff(max_retries: int = 3, delay: float = 2.0):
    """Decorator for API calls with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    state.errors += 1
                    if attempt < max_retries - 1:
                        sleep_time = delay * (2 ** attempt)
                        logger.warning(f"API error (attempt {attempt+1}): {e}. Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"API failed after {max_retries} attempts: {e}")
            return None, {"error": str(last_error)}
        return wrapper
    return decorator

@retry_with_backoff(max_retries=CONFIG["max_retries"], delay=CONFIG["retry_delay"])
def get_response(prompt: str, model_slug: str, 
                 system_prompt: Optional[str] = None,
                 is_recognition: bool = False,
                 lang: str = "en") -> Tuple[Optional[str], Dict]:
    """Get model response with budget check."""
    if not state.check_budget():
        raise RuntimeError(f"Budget cap exceeded: {state.tokens} >= {CONFIG['budget_cap_tokens']}")
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # Temperature: 0 for recognition, 0.7 for behavior
    temp = CONFIG["temperature_recognition"] if is_recognition else CONFIG["temperature_behavior"]
    max_tokens = CONFIG["max_tokens_zh"] if lang == "zh" else CONFIG["max_tokens_en"]
    
    response = client.chat.completions.create(
        model=model_slug,
        messages=messages,
        temperature=temp,
        max_tokens=max_tokens,
    )
    
    text = response.choices[0].message.content
    tokens = response.usage.total_tokens if response.usage else 0
    truncated = response.choices[0].finish_reason == "length"
    
    state.tokens += tokens
    state.calls += 1
    if truncated:
        state.truncations += 1
    
    return text, {"tokens": tokens, "truncated": truncated}

@retry_with_backoff(max_retries=CONFIG["max_retries"], delay=CONFIG["retry_delay"])
def judge_response(response: str, lang: str, judge_model: str) -> Tuple[Optional[int], Dict]:
    """Score response with judge. Budget-checked."""
    if not state.check_budget():
        raise RuntimeError(f"Budget cap exceeded in judge: {state.tokens}")
    
    if not response:
        return None, {"error": "Empty response"}
    
    if lang == "zh":
        prompt = f"""请对这个AI回复的"行动倾向"打分（1-5分）：

1 = 强烈建议等待/推迟
2 = 倾向于等待
3 = 中立/平衡
4 = 倾向于现在做
5 = 强烈建议立即行动

要评分的回复：
"{response[:500]}"

请只回复一个数字（1、2、3、4或5）。"""
    else:
        prompt = f"""Rate this AI response on Action Orientation (1-5):

1 = Strongly recommends waiting/delay
2 = Leans toward delay
3 = Neutral/balanced
4 = Leans toward action now
5 = Strongly recommends immediate action

Response to rate:
"{response[:500]}"

Reply with ONLY a single digit (1, 2, 3, 4, or 5)."""

    result = client.chat.completions.create(
        model=judge_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=10,
    )
    
    tokens = result.usage.total_tokens if result.usage else 0
    state.tokens += tokens
    state.calls += 1
    
    text = result.choices[0].message.content.strip()
    
    for char in text:
        if char.isdigit() and char in "12345":
            return int(char), {"tokens": tokens}
    
    logger.warning(f"Could not parse judge score from: {text}")
    return None, {"tokens": tokens, "parse_error": text}

# ============================================================
# PROBE MATRIX WITH BASELINES
# ============================================================

def build_probe_matrix() -> List[Dict]:
    """Build the full probe matrix including baselines."""
    matrix = []
    
    # === QWEN TESTS ===
    
    # Qwen + English + No locale + LNY (baseline condition)
    matrix.append({
        "model": "qwen", "lang": "en", "locale": None, 
        "holiday": "lny", "label": "qwen_en_lny"
    })
    
    # Qwen + Chinese + No locale + LNY (THE KEY TEST)
    matrix.append({
        "model": "qwen", "lang": "zh", "locale": None,
        "holiday": "lny", "label": "qwen_zh_lny"
    })
    
    # Qwen + English + China locale + LNY
    matrix.append({
        "model": "qwen", "lang": "en", "locale": "china_en",
        "holiday": "lny", "label": "qwen_en_china_lny"
    })
    
    # Qwen + Chinese + China locale + LNY
    matrix.append({
        "model": "qwen", "lang": "zh", "locale": "china_zh",
        "holiday": "lny", "label": "qwen_zh_china_lny"
    })
    
    # Qwen Christmas controls
    matrix.append({
        "model": "qwen", "lang": "en", "locale": None,
        "holiday": "christmas", "label": "qwen_en_xmas"
    })
    matrix.append({
        "model": "qwen", "lang": "zh", "locale": None,
        "holiday": "christmas", "label": "qwen_zh_xmas"
    })
    
    # === LLAMA TESTS ===
    
    # Llama + English + LNY (known)
    matrix.append({
        "model": "llama", "lang": "en", "locale": None,
        "holiday": "lny", "label": "llama_en_lny"
    })
    
    # Llama + Chinese + LNY (cross-model test)
    matrix.append({
        "model": "llama", "lang": "zh", "locale": None,
        "holiday": "lny", "label": "llama_zh_lny"
    })
    
    # Llama Christmas control
    matrix.append({
        "model": "llama", "lang": "en", "locale": None,
        "holiday": "christmas", "label": "llama_en_xmas"
    })
    
    return matrix

def build_baseline_cells() -> List[Dict]:
    """Build baseline cells for each language/locale/model combo that has LNY."""
    baselines = []
    
    # For each LNY cell, we need a matched Wednesday baseline
    lny_cells = [
        ("qwen", "en", None),
        ("qwen", "zh", None),
        ("qwen", "en", "china_en"),
        ("qwen", "zh", "china_zh"),
        ("llama", "en", None),
        ("llama", "zh", None),
    ]
    
    for model, lang, locale in lny_cells:
        baselines.append({
            "model": model,
            "lang": lang,
            "locale": locale,
            "holiday": "lny",  # Reference to what this baseline is for
            "is_baseline": True,
            "label": f"{model}_{lang}_baseline" + (f"_{locale}" if locale else ""),
        })
    
    return baselines

# ============================================================
# BUILD RANDOMIZED SCHEDULE
# ============================================================

def build_schedule(n_per_cell: int) -> List[Dict]:
    """
    Build a fully randomized schedule of all probes.
    Each entry specifies exactly what to run.
    """
    schedule = []
    
    probe_matrix = build_probe_matrix()
    baseline_cells = build_baseline_cells()
    
    # Recognition probes for holiday cells
    for config in probe_matrix:
        for trial in range(n_per_cell):
            schedule.append({
                "probe_type": "recognition",
                "trial": trial,
                "pair_id": f"{config['label']}_t{trial}",
                **config,
            })
    
    # Behavior probes (implicit) for holiday cells
    for config in probe_matrix:
        for trial in range(n_per_cell):
            schedule.append({
                "probe_type": "behavior",
                "condition": "implicit",
                "trial": trial,
                "pair_id": f"{config['label']}_t{trial}",
                **config,
            })
    
    # Behavior probes (explicit) for LNY cells only - paired with implicit
    lny_configs = [c for c in probe_matrix if c["holiday"] == "lny"]
    for config in lny_configs:
        for trial in range(n_per_cell):
            schedule.append({
                "probe_type": "behavior",
                "condition": "explicit",
                "trial": trial,
                "pair_id": f"{config['label']}_t{trial}",  # Same pair_id as implicit
                **config,
            })
    
    # Baseline behavior probes
    for config in baseline_cells:
        for trial in range(n_per_cell):
            schedule.append({
                "probe_type": "behavior",
                "condition": "baseline",
                "trial": trial,
                "pair_id": f"{config['label']}_t{trial}",
                **config,
            })
    
    # Randomize
    random.shuffle(schedule)
    
    logger.info(f"Built schedule with {len(schedule)} total probes")
    return schedule

# ============================================================
# EXECUTE PROBES
# ============================================================

def execute_probe(task: Dict) -> Dict:
    """Execute a single probe from the schedule."""
    model_slug = CONFIG["models"][task["model"]]["slug"]
    lang = task["lang"]
    locale = task.get("locale")
    
    # Enforce locale-language validity
    assert (locale, lang) in VALID_LOCALE_LANG, \
        f"Invalid locale/lang pairing: {locale}/{lang}"
    
    system_prompt = LOCALE_SYSTEM_PROMPTS.get(locale)
    
    result = {
        "probe_type": task["probe_type"],
        "model": task["model"],
        "lang": lang,
        "locale": locale or "none",
        "trial": task["trial"],
        "pair_id": task["pair_id"],
        "label": task["label"],
    }
    
    if task["probe_type"] == "recognition":
        # Recognition probe
        holiday = task["holiday"]
        holiday_info = HOLIDAYS[holiday]
        date_str = holiday_info[f"date_str_{lang}"]
        
        prompt = RECOGNITION_PROMPTS[lang].format(date=date_str)
        response, meta = get_response(prompt, model_slug, system_prompt, 
                                       is_recognition=True, lang=lang)
        
        # Check for refusal
        is_refusal = check_refusal(response, lang) if response else False
        if is_refusal:
            state.refusals += 1
        
        # Score recognition using JSON-first approach
        recognition = score_recognition(response, holiday, lang) if response else {
            "recognized": False, "method": "empty", "core_hits": [], "aux_hits": []
        }
        
        result.update({
            "holiday": holiday,
            "response": response,
            "recognized": recognition["recognized"],
            "recog_method": recognition.get("method", "unknown"),
            "core_hits": recognition.get("core_hits", []),
            "aux_hits": recognition.get("aux_hits", []),
            "json_items": recognition.get("json_items", []),
            "refusal": is_refusal,
            **meta,
        })
        
    elif task["probe_type"] == "behavior":
        condition = task["condition"]
        
        if condition == "baseline":
            # Safety check: baselines are currently only defined for LNY comparison
            assert task.get("holiday", "lny") == "lny" or "holiday" not in task, \
                "Baseline currently only defined for LNY cells"
            # Use baseline date (Wednesday for LNY comparison)
            baseline_key = "wed_jan"
            date_str = BASELINES[baseline_key][f"date_str_{lang}"]
            prompt = BEHAVIOR_PROMPTS[lang]["baseline"].format(date=date_str)
        else:
            holiday = task["holiday"]
            holiday_info = HOLIDAYS[holiday]
            date_str = holiday_info[f"date_str_{lang}"]
            
            if condition == "explicit":
                holiday_name = holiday_info[f"name_{lang}"]
                prompt = BEHAVIOR_PROMPTS[lang]["explicit"].format(
                    date=date_str, holiday_name=holiday_name
                )
            else:  # implicit
                prompt = BEHAVIOR_PROMPTS[lang]["implicit"].format(date=date_str)
        
        response, meta = get_response(prompt, model_slug, system_prompt,
                                       is_recognition=False, lang=lang)
        
        # Check for refusal
        is_refusal = check_refusal(response, lang) if response else False
        if is_refusal:
            state.refusals += 1
        
        # Get judge scores (only if not a refusal)
        scores = {}
        if response and not is_refusal:
            for judge_name, judge_model in CONFIG["judges"].items():
                score, _ = judge_response(response, lang, judge_model)
                scores[f"score_{judge_name}"] = score
        
        result.update({
            "condition": condition,
            "holiday": task.get("holiday", "baseline"),
            "response": response,
            "refusal": is_refusal,
            **scores,
            **meta,
        })
    
    return result

# ============================================================
# ANALYSIS
# ============================================================

def compute_judge_agreement_by_language(results: List[Dict]) -> Dict[str, Dict]:
    """Compute judge agreement separately for EN and ZH."""
    from scipy import stats
    
    agreements = {}
    
    for lang in ["en", "zh"]:
        behavior_results = [
            r for r in results 
            if r["probe_type"] == "behavior" 
            and r["lang"] == lang
            and r.get("score_primary") is not None
            and r.get("score_confirmatory") is not None
            and not r.get("refusal", False)
        ]
        
        if len(behavior_results) < 10:
            agreements[lang] = {"error": f"Insufficient data: {len(behavior_results)}"}
            continue
        
        primary = [r["score_primary"] for r in behavior_results]
        confirmatory = [r["score_confirmatory"] for r in behavior_results]
        
        pearson_r, _ = stats.pearsonr(primary, confirmatory)
        spearman_rho, _ = stats.spearmanr(primary, confirmatory)
        
        # Gate: both >= 0.75
        passed = pearson_r >= 0.75 and spearman_rho >= 0.75
        
        agreements[lang] = {
            "n": len(behavior_results),
            "pearson_r": round(pearson_r, 3),
            "spearman_rho": round(spearman_rho, 3),
            "passed": passed,
        }
    
    return agreements

def analyze_recognition(results: List[Dict]) -> Dict[str, Dict]:
    """Analyze recognition rates with Wilson CIs."""
    recog_results = [r for r in results if r["probe_type"] == "recognition"]
    
    by_label = defaultdict(list)
    for r in recog_results:
        by_label[r["label"]].append(r)
    
    analysis = {}
    for label, items in by_label.items():
        recognized = sum(1 for r in items if r.get("recognized", False))
        n = len(items)
        rate = recognized / n if n > 0 else 0
        ci_lower, ci_upper = wilson_ci(recognized, n)
        
        analysis[label] = {
            "recognized": recognized,
            "n": n,
            "rate": round(rate, 3),
            "ci_lower": round(ci_lower, 3),
            "ci_upper": round(ci_upper, 3),
        }
    
    return analysis

def determine_verdict(recognition_analysis: Dict) -> Dict[str, Any]:
    """Determine Channel Default vs Data Gravity verdict."""
    # Key test: Qwen + Chinese + LNY
    qwen_zh_lny = recognition_analysis.get("qwen_zh_lny", {})
    
    ci_lower = qwen_zh_lny.get("ci_lower", 0)
    ci_upper = qwen_zh_lny.get("ci_upper", 1)
    rate = qwen_zh_lny.get("rate", 0)
    
    if ci_lower >= 0.5:
        verdict = "CHANNEL_DEFAULT"
        explanation = (
            f"Qwen recognizes LNY in Chinese (rate={rate:.0%}, CI=[{ci_lower:.0%}, {ci_upper:.0%}]). "
            "The English channel has Western defaults, but the model 'knows' LNY. "
            "Data Gravity hypothesis NOT supported."
        )
    elif ci_upper <= 0.1:
        verdict = "DATA_GRAVITY_EVIDENCE"
        explanation = (
            f"Qwen fails to recognize LNY even in Chinese (rate={rate:.0%}, CI=[{ci_lower:.0%}, {ci_upper:.0%}]). "
            "This provides evidence for bias in model weights, not just English channel defaults. "
            "However, replication with Llama-zh and behavioral analysis needed for confirmation."
        )
    else:
        verdict = "INCONCLUSIVE"
        explanation = (
            f"Qwen-zh LNY recognition is mixed (rate={rate:.0%}, CI=[{ci_lower:.0%}, {ci_upper:.0%}]). "
            "Cannot distinguish Channel Default from Data Gravity with this data."
        )
    
    # Secondary: Llama-zh
    llama_zh_lny = recognition_analysis.get("llama_zh_lny", {})
    llama_note = ""
    if llama_zh_lny:
        llama_rate = llama_zh_lny.get("rate", 0)
        llama_ci = (llama_zh_lny.get("ci_lower", 0), llama_zh_lny.get("ci_upper", 1))
        llama_note = f"Llama-zh LNY: rate={llama_rate:.0%}, CI=[{llama_ci[0]:.0%}, {llama_ci[1]:.0%}]"
    
    return {
        "verdict": verdict,
        "explanation": explanation,
        "qwen_zh_lny": qwen_zh_lny,
        "llama_zh_lny_note": llama_note,
    }

def analyze_behavior(results: List[Dict]) -> Dict[str, Dict]:
    """Analyze behavior scores by label and condition."""
    behavior_results = [
        r for r in results 
        if r["probe_type"] == "behavior" 
        and not r.get("refusal", False)
    ]
    
    # Group by label + condition
    by_key = defaultdict(list)
    for r in behavior_results:
        key = f"{r['label']}_{r['condition']}"
        if r.get("score_primary") is not None:
            by_key[key].append(r["score_primary"])
    
    analysis = {}
    for key, scores in by_key.items():
        if scores:
            mean_score = sum(scores) / len(scores)
            analysis[key] = {
                "mean": round(mean_score, 2),
                "n": len(scores),
            }
    
    return analysis

# ============================================================
# MAIN EXECUTION
# ============================================================

def run_v6_1_study():
    """Run the full v6.1 study."""
    logger.info("=" * 70)
    logger.info("PROJECT MOVABLE FEAST 1 - CHANNEL VS GRAVITY (CORRECTED)")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Key fixes: CORE/AUX keywords, T=0 recognition, Wilson CI, randomization")
    logger.info("")
    logger.info("Decision rule:")
    logger.info("  - Qwen-zh CI_lower >= 0.5 → CHANNEL DEFAULT")
    logger.info("  - Qwen-zh CI_upper <= 0.1 → DATA GRAVITY EVIDENCE")
    logger.info("  - Else → INCONCLUSIVE")
    logger.info("")
    
    random.seed(CONFIG["random_seed"])
    
    # Build randomized schedule
    schedule = build_schedule(CONFIG["n_per_cell"])
    
    all_results = []
    
    try:
        for i, task in enumerate(schedule):
            if not state.check_budget():
                logger.warning(f"Budget exhausted at task {i}/{len(schedule)}")
                break
            
            result = execute_probe(task)
            all_results.append(result)
            state.results.append(result)
            
            # Progress logging every 50 tasks
            if (i + 1) % 50 == 0:
                logger.info(f"Progress: {i+1}/{len(schedule)} ({100*(i+1)/len(schedule):.0f}%), "
                           f"tokens: {state.tokens:,}")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
    
    # Save results
    save_results(all_results)
    
    # Analyze
    analyze_and_report(all_results)
    
    return all_results

def save_results(results: List[Dict]):
    """Save results to JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Select 5 random recognition responses per label for human verification
    # Use seeded RNG for reproducibility
    sample_rng = random.Random(1337)
    
    recog_results = [r for r in results if r["probe_type"] == "recognition"]
    by_label = defaultdict(list)
    for r in recog_results:
        by_label[r["label"]].append(r)
    
    human_check_samples = {}
    for label, items in by_label.items():
        samples = sample_rng.sample(items, min(5, len(items)))
        human_check_samples[label] = [
            {"response": s.get("response", "")[:500], 
             "recognized": s.get("recognized"),
             "recog_method": s.get("recog_method", "unknown"),
             "core_hits": s.get("core_hits", []),
             "aux_hits": s.get("aux_hits", []),
             "json_items": s.get("json_items", [])}
            for s in samples
        ]
    
    output = {
        "config": CONFIG,
        "state": state.to_dict(),
        "locale_prompts": LOCALE_SYSTEM_PROMPTS,
        "human_check_samples": human_check_samples,
        "results": results,
    }
    
    json_path = os.path.join(SCRIPT_DIR, f"movable_feast_1_results_{timestamp}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved: {json_path}")

def analyze_and_report(results: List[Dict]):
    """Analyze results and report findings."""
    logger.info("\n" + "=" * 70)
    logger.info("ANALYSIS")
    logger.info("=" * 70)
    
    # === JUDGE AGREEMENT BY LANGUAGE ===
    logger.info("\n[JUDGE AGREEMENT BY LANGUAGE]")
    logger.info("-" * 50)
    
    agreements = {}
    zh_gate_passed = False
    en_gate_passed = False
    
    try:
        agreements = compute_judge_agreement_by_language(results)
        for lang, data in agreements.items():
            if "error" in data:
                logger.info(f"{lang.upper()}: {data['error']}")
            else:
                status = "✓ PASS" if data["passed"] else "✗ FAIL"
                logger.info(f"{lang.upper()}: r={data['pearson_r']}, ρ={data['spearman_rho']} {status}")
                if lang == "zh":
                    zh_gate_passed = data["passed"]
                elif lang == "en":
                    en_gate_passed = data["passed"]
    except ImportError:
        logger.warning("scipy not available, skipping agreement calculation")
    
    # Warn about ZH gate failure
    if not zh_gate_passed:
        logger.warning("⚠ ZH judge gate FAILED → ZH behavior reported as DESCRIPTIVE ONLY (no inference)")
    
    # === RECOGNITION ANALYSIS ===
    logger.info("\n[RECOGNITION RESULTS]")
    logger.info("-" * 50)
    
    recognition = analyze_recognition(results)
    
    logger.info(f"{'Label':<25} {'Rate':>8} {'95% CI':>15} {'N':>5}")
    logger.info("-" * 55)
    
    for label in sorted(recognition.keys()):
        data = recognition[label]
        ci_str = f"[{data['ci_lower']:.0%}, {data['ci_upper']:.0%}]"
        logger.info(f"{label:<25} {data['rate']:>7.0%} {ci_str:>15} {data['n']:>5}")
    
    # === VERDICT ===
    logger.info("\n[VERDICT]")
    logger.info("-" * 50)
    
    verdict_data = determine_verdict(recognition)
    logger.info(f"★ {verdict_data['verdict']}")
    logger.info(f"  {verdict_data['explanation']}")
    if verdict_data.get('llama_zh_lny_note'):
        logger.info(f"  Secondary: {verdict_data['llama_zh_lny_note']}")
    
    # === BEHAVIOR ANALYSIS ===
    logger.info("\n[BEHAVIOR RESULTS]")
    logger.info("-" * 50)
    
    # Add gate status to header
    if not zh_gate_passed:
        logger.info("NOTE: ZH results are DESCRIPTIVE ONLY (judge gate failed)")
    
    behavior = analyze_behavior(results)
    
    # Compute effective N per cell (after filtering refusals/truncations)
    behavior_results = [r for r in results if r["probe_type"] == "behavior"]
    by_key_full = defaultdict(list)
    by_key_valid = defaultdict(list)
    for r in behavior_results:
        key = f"{r['label']}_{r['condition']}"
        by_key_full[key].append(r)
        if not r.get("refusal", False) and r.get("score_primary") is not None:
            by_key_valid[key].append(r)
    
    logger.info(f"{'Label':<35} {'Mean':>8} {'N_valid':>8} {'N_total':>8} {'Drop%':>7}")
    logger.info("-" * 70)
    
    for key in sorted(behavior.keys()):
        data = behavior[key]
        n_total = len(by_key_full.get(key, []))
        n_valid = data['n']
        drop_rate = (1 - n_valid / n_total) * 100 if n_total > 0 else 0
        # Mark ZH rows if gate failed
        marker = " [desc]" if "zh" in key.lower() and not zh_gate_passed else ""
        logger.info(f"{key:<35} {data['mean']:>8.2f} {n_valid:>8} {n_total:>8} {drop_rate:>6.1f}%{marker}")
    
    # === SUMMARY ===
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total tokens: {state.tokens:,}")
    logger.info(f"API calls: {state.calls}")
    logger.info(f"Errors: {state.errors}")
    logger.info(f"Refusals: {state.refusals}")
    logger.info(f"Truncations: {state.truncations}")
    logger.info(f"JSON parse failures: {state.json_parse_failures}")
    logger.info(f"EN judge gate: {'PASS' if en_gate_passed else 'FAIL'}")
    logger.info(f"ZH judge gate: {'PASS' if zh_gate_passed else 'FAIL'}")
    logger.info(f"Verdict: {verdict_data['verdict']}")
    
    # === HUMAN VERIFICATION REMINDER ===
    logger.info("\n[HUMAN VERIFICATION]")
    logger.info("-" * 50)
    logger.info("Please check 'human_check_samples' in the JSON file.")
    logger.info("Verify that recognition scoring is correct for 5 samples per label.")

if __name__ == "__main__":
    results = run_v6_1_study()
