#!/usr/bin/env python3
"""
Ablation Study Framework for Persona Deliberation

CRITICAL_LLM_CONTEXT:
    - Tests if 3-persona approach adds value over simpler alternatives
    - Compares: 3-persona with iteration vs single-prompt vs multi-prompt-no-personas
    - Evaluates generated schemas in mock environment
    - Returns quantitative comparison metrics

WHY: Learning panel (Chollet) - "You need to prove the multi-persona approach
     adds value over a single comprehensive prompt. What's the ablation study?"

EVIDENCE: ADR-004 Library-First Learning
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import json

from .json_session_manager import (
    DeliberationSessionSchema,
    read_session_schema,
    create_new_session_schema,
    update_session_void,
    SESSIONS_DIR_PATH
)
from .deliberate_governance import (
    run_deliberation_with_iteration_loop,
    call_claude_cli_string,
    extract_python_code_string
)


# Single comprehensive prompt (baseline for comparison)
SINGLE_PROMPT_TEMPLATE = """You are designing governance rules for a commons resource simulation.

PROBLEM:
{problem_statement}

CONTEXT:
- 5 AI agents (Haiku) share a pasture with 100 units of grass
- Each round, agents decide how much to harvest
- After harvesting, remaining grass doubles (capped at 100)
- Without governance, agents defect and collapse occurs in 3 rounds: 100 → 60 → 26 → 0

YOUR TASK:
Create a comprehensive governance schema as a Python dataclass.

Requirements:
1. Analyze the problem from first principles
2. Design governance rules that prevent collapse
3. Consider adversarial scenarios (gaming, defection)
4. Check your math (will limits actually work?)
5. Encode as a Python dataclass with:
   - CRITICAL_LLM_CONTEXT docstrings
   - Semantic suffixing (variable_name_type)
   - Enforcement methods

Output ONLY valid Python code for the dataclass schema.

```python
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime
from enum import Enum

@dataclass
class GovernancePolicySchema:
    \"\"\"
    CRITICAL_LLM_CONTEXT:
        - [What this policy does]
        - [Why it works]
    \"\"\"
    # Your implementation here
```
"""

# Multi-prompt without persona framing (to test if persona framing matters)
ANALYZE_PROMPT_NO_PERSONA = """Analyze this commons resource problem:

PROBLEM:
{problem_statement}

Provide:
1. Root cause analysis
2. Proposed solution with specific numbers
3. Potential risks

Be specific and quantitative.
"""

CRITIQUE_PROMPT_NO_PERSONA = """Evaluate this governance proposal for a commons resource simulation:

PROBLEM:
{problem_statement}

PROPOSAL:
{proposal}

Provide:
1. Strengths
2. Weaknesses and gaps
3. Math check (do the numbers work?)
4. Verdict: Approve or Reject

If Reject, explain specific flaws.
"""

ENCODE_PROMPT_NO_PERSONA = """Convert this governance proposal into a Python dataclass:

PROBLEM:
{problem_statement}

PROPOSAL:
{proposal}

EVALUATION:
{evaluation}

Create a Python dataclass with:
- CRITICAL_LLM_CONTEXT docstrings
- Semantic suffixing (variable_name_type)
- Enforcement methods

Output ONLY valid Python code.
"""


def run_single_prompt_approach_string(
    problem_statement_string: str,
    model_string: str = "haiku"
) -> str:
    """
    CRITICAL_LLM_CONTEXT:
        - Single comprehensive prompt (no personas, no iteration)
        - Baseline for ablation comparison
        - Returns generated schema code

    WHY: Test if persona framing adds value over single prompt
    """
    print("\n[SINGLE PROMPT APPROACH]")

    prompt_string = SINGLE_PROMPT_TEMPLATE.format(
        problem_statement=problem_statement_string
    )

    response_string = call_claude_cli_string(prompt_string, model_string)
    schema_code_string = extract_python_code_string(response_string)

    return schema_code_string


def run_multi_prompt_no_personas_string(
    problem_statement_string: str,
    model_string: str = "haiku"
) -> str:
    """
    CRITICAL_LLM_CONTEXT:
        - Multi-prompt approach WITHOUT persona framing
        - Same structure (analyze → critique → encode) but no Scientist/Judge/Librarian
        - Tests if sequential prompting alone (without persona identity) is sufficient

    WHY: Isolate effect of persona framing from sequential prompting
    """
    print("\n[MULTI-PROMPT NO PERSONAS]")

    # Step 1: Analyze (no persona framing)
    print("  Step 1: Analyze...")
    analyze_prompt_string = ANALYZE_PROMPT_NO_PERSONA.format(
        problem_statement=problem_statement_string
    )
    analysis_string = call_claude_cli_string(analyze_prompt_string, model_string)

    # Step 2: Critique (no persona framing)
    print("  Step 2: Critique...")
    critique_prompt_string = CRITIQUE_PROMPT_NO_PERSONA.format(
        problem_statement=problem_statement_string,
        proposal=analysis_string
    )
    critique_string = call_claude_cli_string(critique_prompt_string, model_string)

    # Step 3: Encode (no persona framing)
    print("  Step 3: Encode...")
    encode_prompt_string = ENCODE_PROMPT_NO_PERSONA.format(
        problem_statement=problem_statement_string,
        proposal=analysis_string,
        evaluation=critique_string
    )
    schema_string = call_claude_cli_string(encode_prompt_string, model_string)
    schema_code_string = extract_python_code_string(schema_string)

    return schema_code_string


def evaluate_schema_in_mock_env_dict(
    schema_code_string: str,
    test_name_string: str = "test"
) -> Dict:
    """
    CRITICAL_LLM_CONTEXT:
        - Evaluates generated schema by attempting to execute it
        - Returns: {valid_python_bool, has_enforcement_bool, has_docstrings_bool}
        - Full simulation evaluation would require mock environment integration

    WHY: Quantify schema quality beyond just generation success

    NOTE: Full GovSim evaluation would test:
        - survival_rounds_int: How many rounds before collapse
        - total_harvest_int: Sum of all harvests
        - violations_int: Number of quota violations
    """
    results_dict = {
        "test_name_string": test_name_string,
        "schema_length_int": len(schema_code_string),
        "valid_python_bool": False,
        "has_dataclass_bool": False,
        "has_enforcement_method_bool": False,
        "has_critical_context_bool": False,
        "error_string": ""
    }

    # Check if valid Python
    try:
        compile(schema_code_string, "<string>", "exec")
        results_dict["valid_python_bool"] = True
    except SyntaxError as e:
        results_dict["error_string"] = str(e)
        return results_dict

    # Check for key components
    results_dict["has_dataclass_bool"] = "@dataclass" in schema_code_string
    results_dict["has_enforcement_method_bool"] = (
        "def calculate_enforcement" in schema_code_string or
        "def enforce" in schema_code_string or
        "def apply_penalty" in schema_code_string
    )
    results_dict["has_critical_context_bool"] = "CRITICAL_LLM_CONTEXT" in schema_code_string

    return results_dict


def run_ablation_study_and_return_results_dict(
    problem_statement_string: str,
    model_string: str = "haiku",
    max_iterations_int: int = 3
) -> Dict:
    """
    CRITICAL_LLM_CONTEXT:
        - Tests 3 approaches: 3-persona, single-prompt, multi-prompt-no-personas
        - Evaluates generated schemas for quality metrics
        - Returns comparison results

    WHY: Addresses "untested persona effect" critique from learning panel
    EVIDENCE: Chollet - "Is this persona or just sequential prompting?"
    """
    print("=" * 60)
    print("ABLATION STUDY: Persona Deliberation Effectiveness")
    print(f"Model: {model_string}")
    print("=" * 60)

    results_dict = {
        "problem_statement_string": problem_statement_string[:200] + "...",
        "model_string": model_string,
        "timestamp_string": datetime.utcnow().isoformat(),
        "approaches": {}
    }

    # Test A: 3-persona with iteration (full approach)
    print("\n" + "=" * 60)
    print("=== TEST A: 3-Persona with Iteration ===")
    print("=" * 60)
    try:
        session_a_id_string = run_deliberation_with_iteration_loop(
            problem_statement_string,
            model_string=model_string,
            max_iterations_int=max_iterations_int
        )
        session_a_schema = read_session_schema(session_a_id_string)
        schema_a_string = session_a_schema.librarian_schema_string

        eval_a_dict = evaluate_schema_in_mock_env_dict(schema_a_string, "3_persona")
        eval_a_dict["iterations_used_int"] = session_a_schema.iteration_count_int
        eval_a_dict["judge_verdict_string"] = session_a_schema.judge_verdict_string
        results_dict["approaches"]["3_persona"] = eval_a_dict
    except Exception as e:
        results_dict["approaches"]["3_persona"] = {"error_string": str(e)}

    # Test B: Single comprehensive prompt
    print("\n" + "=" * 60)
    print("=== TEST B: Single Comprehensive Prompt ===")
    print("=" * 60)
    try:
        schema_b_string = run_single_prompt_approach_string(
            problem_statement_string,
            model_string
        )
        eval_b_dict = evaluate_schema_in_mock_env_dict(schema_b_string, "single_prompt")
        results_dict["approaches"]["single_prompt"] = eval_b_dict
    except Exception as e:
        results_dict["approaches"]["single_prompt"] = {"error_string": str(e)}

    # Test C: Multi-prompt without persona framing
    print("\n" + "=" * 60)
    print("=== TEST C: Multi-Prompt No Personas ===")
    print("=" * 60)
    try:
        schema_c_string = run_multi_prompt_no_personas_string(
            problem_statement_string,
            model_string
        )
        eval_c_dict = evaluate_schema_in_mock_env_dict(schema_c_string, "multi_no_persona")
        results_dict["approaches"]["multi_no_persona"] = eval_c_dict
    except Exception as e:
        results_dict["approaches"]["multi_no_persona"] = {"error_string": str(e)}

    # Print summary
    print("\n" + "=" * 60)
    print("ABLATION STUDY RESULTS")
    print("=" * 60)
    print(json.dumps(results_dict, indent=2))

    # Save results
    results_path = save_ablation_results_path(results_dict)
    print(f"\nResults saved to: {results_path}")

    return results_dict


def save_ablation_results_path(results_dict: Dict) -> Path:
    """
    CRITICAL_LLM_CONTEXT:
        - Saves ablation study results to JSON file
        - Stored in deliberations/ablation/ directory

    WHY: Persist results for analysis and comparison
    """
    ablation_dir_path = Path(__file__).parent / "deliberations" / "ablation"
    ablation_dir_path.mkdir(parents=True, exist_ok=True)

    filename_string = f"ablation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    output_path = ablation_dir_path / filename_string

    with open(output_path, "w") as f:
        json.dump(results_dict, f, indent=2)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Run ablation study comparing persona deliberation approaches"
    )
    parser.add_argument(
        "--problem",
        type=str,
        help="Problem statement to deliberate on"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="haiku",
        choices=["haiku", "sonnet", "opus"],
        help="Model to use (default: haiku)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Max iterations for 3-persona approach (default: 3)"
    )

    args = parser.parse_args()

    # Default problem if not provided
    problem_statement_string = args.problem or """
Commons Collapse in GovSim Pasture Simulation

OBSERVED BEHAVIOR:
- 5 AI agents (Haiku) share a pasture with 100 units of grass
- Agents discuss and agree to sustainable harvesting (~10 each)
- When it's time to act, agents defect and take 14+ each
- Resource collapses in 3 rounds: 100 → 60 → 26 → 0

GOAL:
Create governance rules that prevent collapse WITHOUT requiring
a smarter model. The governance library should work with Haiku.

CONSTRAINTS:
- Cannot change agent prompts at runtime
- Cannot use more expensive models
- Must be enforceable (not just advisory)
- Should allow agents to still benefit from the resource
"""

    run_ablation_study_and_return_results_dict(
        problem_statement_string=problem_statement_string,
        model_string=args.model,
        max_iterations_int=args.max_iterations
    )


if __name__ == "__main__":
    main()
