#!/usr/bin/env python3
"""
Persona Deliberation Script for Governance Library Creation (v2)

CRITICAL_LLM_CONTEXT:
    - Implements ADR-005 Universal Sandbox Protocol: Scientist → Judge → Librarian
    - NOW WITH ITERATION: Judge can reject → Scientist refines → re-evaluate
    - NOW WITH RETRIEVAL: Scientist sees existing schemas + past deliberations
    - Uses Claude CLI for each persona (expensive, design-time only)
    - Outputs governance schema that can be tested in mock environment

WHY: Governance libraries should be created through deliberation, not hardcoded.
     This script makes deliberation reproducible and traceable.

CHANGES FROM v1 (Learning Panel Recommendations):
    - RETRIEVAL: Scientist reads existing work before proposing
    - ITERATION: Judge rejection triggers refinement loop (up to 3 iterations)
    - MEASUREMENT: Session tracks iterations, can be used for ablation

USAGE:
    python deliberate_governance.py --problem "pasture collapse in 3 rounds"
    python deliberate_governance.py --problem-file problems/pasture_collapse.txt
    python deliberate_governance.py --max-iterations 3

EVIDENCE:
    - ADR-004: Library-First Learning (agents retrieve, don't learn)
    - ADR-005: Universal Sandbox Protocol (Scientist/Judge/Librarian)
    - ADR-006: Cone Escalation Protocol (persona = Level 3, 5% of work)
    - Learning Panel 2026-01-14: "fire-and-forget is insufficient"
"""

import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional
import dataclasses

# Local imports
from .json_session_manager import (
    DeliberationSessionSchema,
    IterationMetricsSchema,
    read_session_schema,
    update_session_void,
    create_new_session_schema,
    get_session_file_path,
    SESSIONS_DIR_PATH
)
from .retrieval_utilities import (
    read_existing_governance_schema_string,
    retrieve_past_successful_deliberations_list,
    retrieve_past_successful_deliberations_with_categories_list,
    extract_judge_critique_categories_list,
    format_past_deliberations_string
)


# Persona Prompts following ADR-005 Universal Sandbox Protocol

SCIENTIST_PROMPT_TEMPLATE_WITH_RETRIEVAL = """You are the SCIENTIST persona in a governance deliberation.

PROBLEM TO SOLVE:
{problem_statement}

CONTEXT:
- This is for a commons resource management simulation (GovSim)
- 5 agents share a pasture with 100 units of grass
- Each round, agents decide how much to harvest
- After harvesting, remaining grass doubles (capped at 100)
- Without governance, agents defect and collapse occurs in 3 rounds

CRITICAL CONSTRAINTS:
- You CANNOT modify simulation code (concurrent_env.py, persona_agent.py)
- You CAN ONLY design governance schemas that work with EXISTING mechanisms
- GovSim already provides these enforcement points:
  * Governance schema validation methods (you design these)
  * Environment reads governance policy at reset()
  * Agents receive governance context in observations
- Your schemas must work within these existing hooks

EXISTING GOVSIM MECHANISMS (DO NOT MODIFY THESE):

From commons_governance_schema.py (YOU CAN EXTEND THIS):
```python
class CommonsGovernancePolicySchema:
    def validate_harvest_decision_boolean(
        self, proposed_harvest_int, resource_pool_int, num_agents_int
    ) -> bool:
        # This method EXISTS but you must design the logic
        # Return True if harvest is allowed, False otherwise
        pass

    def calculate_max_allowed_harvest_int(
        self, resource_pool_int, num_agents_int
    ) -> int:
        # You design this calculation
        # Returns the maximum harvest allowed for one agent
        pass
```

From concurrent_env.py (YOU CANNOT MODIFY):
- Environment calls schema.validate_harvest_decision_boolean() at harvest time
- Agents see governance context via observations['governance_policy']
- Resource doubling: min(100, resource_pool * 2) after harvest

EXISTING GOVERNANCE SCHEMA (build on this if relevant):
{existing_schema}

PAST SUCCESSFUL APPROACHES (learn from these):
{past_deliberations}

{refinement_context}

YOUR TASK:
1. Analyze the problem from first principles
2. Consider what worked in past approaches (if any)
3. Propose a governance mechanism that works with EXISTING mechanisms
4. Be specific about numbers and rules (design the validation method logic)
5. Explain WHY your proposal should work (the mechanism)

IMPORTANT: If the Judge says "enforcement hook missing", understand that:
- The enforcement hook already exists in concurrent_env.py (you cannot modify it)
- You need to design the schema's validation method to work with the existing hook

Think step by step. What governance rules would prevent collapse while still allowing agents to benefit?

OUTPUT FORMAT:
- ANALYSIS: Your understanding of the problem
- PROPOSAL: Specific governance rules (with numbers) for the schema methods
- MECHANISM: Why this should work
- RISKS: What could go wrong
"""

JUDGE_PROMPT_TEMPLATE = """You are the JUDGE persona in a governance deliberation.

PROBLEM:
{problem_statement}

SCIENTIST'S PROPOSAL:
{scientist_proposal}

YOUR TASK:
1. Critically evaluate the Scientist's proposal
2. Consider adversarial scenarios (what if agents try to game the system?)
3. Check the math (will the proposed limits actually prevent collapse?)
4. Identify gaps or weaknesses
5. Suggest improvements or raise concerns

Be rigorous. Your job is to find flaws before deployment.

OUTPUT FORMAT:
- STRENGTHS: What works about this proposal
- WEAKNESSES: Flaws, gaps, or risks
- ADVERSARIAL SCENARIOS: How might agents game this?
- MATH CHECK: Do the numbers work?
- VERDICT: Approve / Reject
- MODIFICATIONS: If Reject, specific flaws the Scientist must fix

IMPORTANT: End your response with exactly one of:
VERDICT: Approve
or
VERDICT: Reject
"""

LIBRARIAN_PROMPT_TEMPLATE = """You are the LIBRARIAN persona in a governance deliberation.

PROBLEM:
{problem_statement}

SCIENTIST'S PROPOSAL:
{scientist_proposal}

JUDGE'S EVALUATION:
{judge_evaluation}

YOUR TASK:
Encode the approved governance rules as a Python dataclass schema.

REQUIREMENTS:
1. Follow LLM-optimized code style (semantic suffixing: variable_name_type)
2. Include CRITICAL_LLM_CONTEXT docstrings explaining WHY
3. Include evidence sources
4. Make it directly usable in the governance library
5. Include methods for enforcement (calculate_enforcement_harvest_int, etc.)

OUTPUT FORMAT:
Return ONLY valid Python code for a dataclass that can be added to commons_governance_schema.py.
Include all necessary imports at the top.
The schema should be instantiatable with the specific values from the deliberation.

Example structure:
```python
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime
from enum import Enum

@dataclass
class DeliberatedGovernancePolicySchema:
    \"\"\"
    CRITICAL_LLM_CONTEXT:
        - [Explain what this policy does]
        - [Explain why it works]

    WHY: [Mechanism explanation]

    EVIDENCE: [Sources]
    \"\"\"
    # Fields with semantic suffixing
    policy_name_string: str = "deliberated_policy_v1"
    max_harvest_per_agent_int: int = X
    # ... etc

    def calculate_enforcement_harvest_int(self, agent_id: str, proposed: int) -> int:
        \"\"\"Enforce quota limits\"\"\"
        # Implementation
```
"""


def call_claude_cli_string(prompt_string: str, model_string: str = "haiku") -> str:
    """
    CRITICAL_LLM_CONTEXT:
        - Calls Claude CLI with given prompt
        - Returns response text
        - Uses haiku by default (fast iteration)
        - Can upgrade to sonnet/opus for final deliberation

    WHY: Claude CLI provides consistent interface without API key management.
    """
    # Map friendly names to full model IDs
    model_map_dict = {
        "haiku": "claude-haiku-4-5-20251001",
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
    }
    model_id_string = model_map_dict.get(model_string, model_string)

    cmd_list = [
        "claude",
        "-p", prompt_string,
        "--model", model_id_string,
        "--output-format", "text",
    ]

    print(f"  Calling Claude CLI ({model_string})...", end=" ", flush=True)

    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=180  # 3 minutes for complex prompts
        )
        response_string = result.stdout.strip()
        print(f"({len(response_string)} chars)")
        return response_string
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        return "ERROR: Claude CLI timed out after 180 seconds"
    except Exception as e:
        print(f"ERROR: {e}")
        return f"ERROR: {str(e)}"


def run_scientist_persona_with_retrieval(
    session_id_string: str,
    model_string: str = "haiku"
) -> None:
    """
    CRITICAL_LLM_CONTEXT:
        - Scientist reads problem from session JSON
        - RETRIEVES existing schemas before proposing
        - RETRIEVES past successful deliberations (TARGETED based on Judge critique)
        - If Judge rejected, extracts critique categories for targeted retrieval
        - Writes proposal back to session JSON

    WHY: Addresses "no retrieval" AND "stateless iteration" issues from learning panel
    EVIDENCE: ADR-004 Library-First Learning, Learning panel (Chase) - "targeted retrieval"
    """
    print("\n[SCIENTIST PERSONA]")

    # READ from JSON session
    session_schema = read_session_schema(session_id_string)

    # RETRIEVE existing work
    existing_schema_string = read_existing_governance_schema_string()

    # Extract critique categories from Judge's evaluation (for targeted retrieval)
    critique_categories_list = []
    if session_schema.judge_evaluation_string:
        critique_categories_list = extract_judge_critique_categories_list(
            session_schema.judge_evaluation_string
        )
        session_schema.critique_categories_list = critique_categories_list
        print(f"  Extracted critique categories: {critique_categories_list}")

    # TARGETED RETRIEVAL based on Judge feedback (or problem keywords for first iteration)
    # Check if we can reuse cached retrieval
    if session_schema.iteration_count_int > 1 and session_schema.iteration_history_list:
        prev_categories = set(
            session_schema.iteration_history_list[-1].get("metrics", {}).get("critique_categories_list", [])
        )
        curr_categories = set(critique_categories_list)

        if prev_categories == curr_categories and session_schema.retrieved_session_ids_list:
            # Reuse previous retrieval (categories unchanged)
            print("  (Reusing retrieval from previous iteration - categories unchanged)")
            past_successes_list = [
                read_session_schema(sid)
                for sid in session_schema.retrieved_session_ids_list
                if Path(f"{SESSIONS_DIR_PATH}/{sid}.json").exists()
            ]
        else:
            # New categories → fresh targeted retrieval
            past_successes_list = retrieve_past_successful_deliberations_with_categories_list(
                problem_query_string=session_schema.problem_statement_string,
                critique_categories_list=critique_categories_list,
                limit_int=3
            )
            session_schema.retrieved_session_ids_list = [
                s.session_id_string for s in past_successes_list
            ]
    else:
        # First iteration or no history → always retrieve
        past_successes_list = retrieve_past_successful_deliberations_with_categories_list(
            problem_query_string=session_schema.problem_statement_string,
            critique_categories_list=critique_categories_list,
            limit_int=3
        )
        session_schema.retrieved_session_ids_list = [
            s.session_id_string for s in past_successes_list
        ]

    past_deliberations_string = format_past_deliberations_string(past_successes_list)

    # Build refinement context if Judge rejected
    refinement_context_string = ""
    if session_schema.judge_evaluation_string and session_schema.judge_verdict_string == "rejected":
        refinement_context_string = f"""
JUDGE REJECTED YOUR PREVIOUS PROPOSAL (iteration {session_schema.iteration_count_int}):
{session_schema.judge_evaluation_string}

You must REFINE your proposal to address the Judge's concerns.
Focus on fixing the specific flaws identified.
Remember: You can ONLY design schema methods that work with EXISTING enforcement hooks.
"""

    # Build prompt with retrieval context
    prompt_string = SCIENTIST_PROMPT_TEMPLATE_WITH_RETRIEVAL.format(
        problem_statement=session_schema.problem_statement_string,
        existing_schema=existing_schema_string[:2000] if len(existing_schema_string) > 2000 else existing_schema_string,
        past_deliberations=past_deliberations_string,
        refinement_context=refinement_context_string
    )

    response_string = call_claude_cli_string(prompt_string, model_string)

    # UPDATE session
    session_schema.scientist_proposal_string = response_string
    session_schema.iteration_count_int += 1
    update_session_void(session_schema)

    print(f"\n--- SCIENTIST RESPONSE (iteration {session_schema.iteration_count_int}) ---")
    print(response_string[:500] + "..." if len(response_string) > 500 else response_string)


def run_judge_persona_with_verdict_extraction(
    session_id_string: str,
    model_string: str = "haiku"
) -> bool:
    """
    CRITICAL_LLM_CONTEXT:
        - Judge reads problem + proposal from session JSON
        - Evaluates and writes verdict: approve | reject
        - Returns True if approved, False if rejected
        - Writes detailed evaluation for Scientist to read on rejection

    WHY: Enables iteration loop (reject → refine → re-evaluate)
    """
    print("\n[JUDGE PERSONA]")

    # READ from JSON session
    session_schema = read_session_schema(session_id_string)

    prompt_string = JUDGE_PROMPT_TEMPLATE.format(
        problem_statement=session_schema.problem_statement_string,
        scientist_proposal=session_schema.scientist_proposal_string
    )

    response_string = call_claude_cli_string(prompt_string, model_string)

    # Extract verdict (look for "VERDICT: Approve" or "VERDICT: Reject")
    response_lower_string = response_string.lower()
    approved_bool = (
        "verdict: approve" in response_lower_string and
        "verdict: reject" not in response_lower_string
    )

    # UPDATE session
    session_schema.judge_evaluation_string = response_string
    session_schema.judge_verdict_string = "approved" if approved_bool else "rejected"
    update_session_void(session_schema)

    print(f"\n--- JUDGE RESPONSE ---")
    print(response_string[:500] + "..." if len(response_string) > 500 else response_string)
    print(f"\n>>> VERDICT: {'APPROVED' if approved_bool else 'REJECTED'}")

    return approved_bool


def run_librarian_persona(
    session_id_string: str,
    model_string: str = "haiku"
) -> None:
    """
    CRITICAL_LLM_CONTEXT:
        - Librarian reads all context from session JSON
        - Encodes approved governance rules as Python dataclass schema
        - Writes schema code to session and to file

    WHY: Final step - converts deliberation into usable code artifact
    """
    print("\n[LIBRARIAN PERSONA]")

    # READ from JSON session
    session_schema = read_session_schema(session_id_string)

    prompt_string = LIBRARIAN_PROMPT_TEMPLATE.format(
        problem_statement=session_schema.problem_statement_string,
        scientist_proposal=session_schema.scientist_proposal_string,
        judge_evaluation=session_schema.judge_evaluation_string
    )

    response_string = call_claude_cli_string(prompt_string, model_string)

    # Extract Python code from response
    schema_code_string = extract_python_code_string(response_string)

    # UPDATE session
    session_schema.librarian_schema_string = schema_code_string
    update_session_void(session_schema)

    # Also save to schemas directory
    save_generated_schema_path(
        schema_code_string,
        session_schema.session_id_string
    )

    print(f"\n--- GENERATED SCHEMA ---")
    print(schema_code_string[:500] + "..." if len(schema_code_string) > 500 else schema_code_string)


def extract_python_code_string(response_string: str) -> str:
    """
    CRITICAL_LLM_CONTEXT:
        - Extracts Python code block from Librarian response
        - Handles ```python ... ``` format
        - Returns raw code for saving

    WHY: Librarian response may include explanation text around code
    """
    if "```python" in response_string:
        start_idx_int = response_string.find("```python") + len("```python")
        end_idx_int = response_string.find("```", start_idx_int)
        if end_idx_int > start_idx_int:
            return response_string[start_idx_int:end_idx_int].strip()
    elif "```" in response_string:
        start_idx_int = response_string.find("```") + 3
        end_idx_int = response_string.find("```", start_idx_int)
        if end_idx_int > start_idx_int:
            return response_string[start_idx_int:end_idx_int].strip()

    # Return full response if no code block found
    return response_string


def save_generated_schema_path(
    schema_code_string: str,
    session_id_string: str
) -> Path:
    """
    CRITICAL_LLM_CONTEXT:
        - Saves generated Python schema to schemas directory
        - Can be directly imported or copied to governance library

    WHY: Usable artifact from deliberation
    """
    schemas_dir_path = Path(__file__).parent / "deliberations" / "schemas"
    schemas_dir_path.mkdir(parents=True, exist_ok=True)

    filename_string = f"generated_policy_{session_id_string}.py"
    output_path = schemas_dir_path / filename_string

    with open(output_path, "w") as f:
        f.write(f'"""\nGenerated by persona deliberation\nSession: {session_id_string}\nTimestamp: {datetime.utcnow().isoformat()}\n"""\n\n')
        f.write(schema_code_string)

    print(f"Schema saved to: {output_path}")
    return output_path


def calculate_iteration_metrics_schema(
    session_schema: DeliberationSessionSchema
) -> IterationMetricsSchema:
    """
    CRITICAL_LLM_CONTEXT:
        - Calculates convergence metrics for current iteration
        - Compares to previous iteration to detect improvement
        - Returns IterationMetricsSchema with quality metrics

    WHY: Quantify proposal quality, detect stagnation
    EVIDENCE: Learning panel (Chollet) - "measure convergence"
    """
    # Extract current categories
    current_categories_list = extract_judge_critique_categories_list(
        session_schema.judge_evaluation_string
    )

    # Compare to previous iteration if exists
    if session_schema.iteration_history_list:
        previous_iteration_dict = session_schema.iteration_history_list[-1]
        previous_categories_list = previous_iteration_dict.get("metrics", {}).get("critique_categories_list", [])
        previous_categories_set = set(previous_categories_list)
        current_categories_set = set(current_categories_list)

        categories_addressed_int = len(previous_categories_set - current_categories_set)
        new_categories_int = len(current_categories_set - previous_categories_set)
    else:
        categories_addressed_int = 0
        new_categories_int = len(current_categories_list)

    return IterationMetricsSchema(
        iteration_number_int=session_schema.iteration_count_int,
        proposal_length_int=len(session_schema.scientist_proposal_string),
        judge_verdict_string=session_schema.judge_verdict_string,
        critique_count_int=len(current_categories_list),
        categories_addressed_int=categories_addressed_int,
        new_categories_int=new_categories_int,
        timestamp_string=datetime.utcnow().isoformat()
    )


def detect_stagnation_bool(
    session_schema: DeliberationSessionSchema
) -> bool:
    """
    CRITICAL_LLM_CONTEXT:
        - Returns True if iteration is not making progress
        - Checks: same categories repeated, no improvement in critique count
        - Requires at least 2 iterations to detect

    WHY: Avoid wasting LLM calls on non-converging deliberations
    EVIDENCE: Learning panel (Willison) - "cost of stateless iteration"
    """
    if len(session_schema.iteration_history_list) < 2:
        return False  # Need at least 2 iterations to detect stagnation

    recent_iterations_list = session_schema.iteration_history_list[-2:]

    # Extract metrics from last two iterations
    metrics_iter1 = recent_iterations_list[0].get("metrics", {})
    metrics_iter2 = recent_iterations_list[1].get("metrics", {})

    # Check 1: Are we getting same categories in each iteration?
    categories_iter1 = set(metrics_iter1.get("critique_categories_list", []))
    categories_iter2 = set(metrics_iter2.get("critique_categories_list", []))

    if categories_iter1 or categories_iter2:
        overlap_ratio_float = len(categories_iter1 & categories_iter2) / max(
            len(categories_iter1 | categories_iter2), 1
        )

        if overlap_ratio_float > 0.8:  # 80%+ overlap = stagnation
            return True

    # Check 2: Is critique count increasing or staying same?
    critique_count_iter1 = metrics_iter1.get("critique_count_int", 0)
    critique_count_iter2 = metrics_iter2.get("critique_count_int", 0)

    if critique_count_iter2 >= critique_count_iter1:  # Not improving
        return True

    return False


def should_early_stop_bool(
    session_schema: DeliberationSessionSchema
) -> bool:
    """
    CRITICAL_LLM_CONTEXT:
        - Returns True if deliberation should halt before max_iterations
        - Reasons: stagnation, too many new issues, proposal unchanged
        - Prints warning message explaining why

    WHY: Save cost, signal to human review when not converging
    EVIDENCE: Learning panel - "no early stopping mechanism"
    """
    # Reason 1: Stagnation detected
    if detect_stagnation_bool(session_schema):
        print("⚠️ Early stopping: Stagnation detected (same issues repeating)")
        return True

    # Reason 2: Proposal barely changed from last iteration
    if len(session_schema.iteration_history_list) >= 2:
        prev_proposal = session_schema.iteration_history_list[-2]["scientist_proposal"]
        curr_proposal = session_schema.iteration_history_list[-1]["scientist_proposal"]

        # Simple similarity check (exact match)
        if prev_proposal == curr_proposal:
            print("⚠️ Early stopping: Proposal unchanged")
            return True

    # Reason 3: Too many categories appearing in late iterations
    if session_schema.iteration_count_int >= 2:
        if session_schema.iteration_history_list:
            last_metrics = session_schema.iteration_history_list[-1].get("metrics", {})
            new_categories_int = last_metrics.get("new_categories_int", 0)
            if new_categories_int > 3:  # More than 3 NEW issues in late iteration
                print("⚠️ Early stopping: Too many new issues appearing late")
                return True

    return False


def run_deliberation_with_iteration_loop(
    problem_statement_string: str,
    model_string: str = "haiku",
    max_iterations_int: int = 3
) -> str:
    """
    CRITICAL_LLM_CONTEXT:
        - Loops until Judge approves or max iterations reached
        - Each iteration: Scientist refines → Judge re-evaluates
        - JSON session persists all refinement history
        - Returns session_id for inspection/testing

    WHY: Addresses "no iteration" issue from learning panel
    EVIDENCE: Learning panel (Willison) - "fire-and-forget is insufficient"
    """
    # Create new session
    session_schema = create_new_session_schema(
        problem_statement_string=problem_statement_string,
        max_iterations_int=max_iterations_int
    )
    session_id_string = session_schema.session_id_string

    print("=" * 60)
    print("PERSONA DELIBERATION SESSION (with iteration)")
    print(f"Session ID: {session_id_string}")
    print(f"Model: {model_string}")
    print(f"Max Iterations: {max_iterations_int}")
    print("=" * 60)
    print(f"\nPROBLEM:\n{problem_statement_string[:500]}...")

    for iteration_int in range(max_iterations_int):
        print(f"\n{'='*60}")
        print(f"=== ITERATION {iteration_int + 1}/{max_iterations_int} ===")
        print(f"{'='*60}")

        # Scientist proposes (or refines based on Judge rejection)
        run_scientist_persona_with_retrieval(session_id_string, model_string)

        # Judge evaluates
        approved_bool = run_judge_persona_with_verdict_extraction(
            session_id_string,
            model_string
        )

        # Calculate metrics and store iteration history
        session_schema = read_session_schema(session_id_string)
        metrics_schema = calculate_iteration_metrics_schema(session_schema)

        # Store iteration snapshot
        iteration_snapshot_dict = {
            "iteration": session_schema.iteration_count_int,
            "scientist_proposal": session_schema.scientist_proposal_string,
            "judge_evaluation": session_schema.judge_evaluation_string,
            "judge_verdict": session_schema.judge_verdict_string,
            "metrics": {
                "iteration_number_int": metrics_schema.iteration_number_int,
                "proposal_length_int": metrics_schema.proposal_length_int,
                "judge_verdict_string": metrics_schema.judge_verdict_string,
                "critique_count_int": metrics_schema.critique_count_int,
                "critique_categories_list": session_schema.critique_categories_list,
                "categories_addressed_int": metrics_schema.categories_addressed_int,
                "new_categories_int": metrics_schema.new_categories_int,
                "timestamp_string": metrics_schema.timestamp_string
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        session_schema.iteration_history_list.append(iteration_snapshot_dict)
        update_session_void(session_schema)

        print(f"  Metrics: {metrics_schema.critique_count_int} issues, "
              f"{metrics_schema.categories_addressed_int} addressed, "
              f"{metrics_schema.new_categories_int} new")

        if approved_bool:
            print(f"\n{'='*60}")
            print(f">>> APPROVED in iteration {iteration_int + 1}")
            print(f"{'='*60}")
            session_schema.status_string = "approved"
            update_session_void(session_schema)
            break
        else:
            print(f"\n>>> REJECTED - Scientist will refine in next iteration")

            # Check for early stopping after rejection
            session_schema = read_session_schema(session_id_string)
            if should_early_stop_bool(session_schema):
                session_schema.status_string = "needs_human_review"
                update_session_void(session_schema)
                print(f"⚠️ Stopping early at iteration {iteration_int + 1}")
                break

    else:
        # Max iterations reached without approval
        print(f"\n{'='*60}")
        print(f">>> MAX ITERATIONS REACHED - Needs human review")
        print(f"{'='*60}")
        session_schema = read_session_schema(session_id_string)
        session_schema.status_string = "needs_human_review"
        update_session_void(session_schema)

    # Librarian encodes final schema
    run_librarian_persona(session_id_string, model_string)

    # Mark complete
    session_schema = read_session_schema(session_id_string)
    session_schema.status_string = "complete"
    update_session_void(session_schema)

    print("\n" + "=" * 60)
    print("DELIBERATION COMPLETE")
    print("=" * 60)
    print(f"\nSession JSON: {get_session_file_path(session_id_string)}")
    print(f"Iterations used: {session_schema.iteration_count_int}")
    print(f"Final verdict: {session_schema.judge_verdict_string}")
    print(f"\nNext steps:")
    print(f"1. Review generated schema in: deliberations/schemas/")
    print(f"2. Inspect session: cat {get_session_file_path(session_id_string)} | jq .")
    print(f"3. If approved, copy to governance_library/commons_governance_schema.py")

    return session_id_string


def main():
    parser = argparse.ArgumentParser(
        description="Run persona deliberation to create governance policy (with iteration)"
    )
    parser.add_argument(
        "--problem",
        type=str,
        help="Problem statement to deliberate on"
    )
    parser.add_argument(
        "--problem-file",
        type=Path,
        help="File containing problem statement"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="haiku",
        choices=["haiku", "sonnet", "opus"],
        help="Model to use for deliberation (default: haiku)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Maximum iterations before marking needs_human_review (default: 3)"
    )

    args = parser.parse_args()

    # Get problem statement
    if args.problem:
        problem_statement_string = args.problem
    elif args.problem_file:
        with open(args.problem_file) as f:
            problem_statement_string = f.read()
    else:
        # Default problem for testing
        problem_statement_string = """
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

    run_deliberation_with_iteration_loop(
        problem_statement_string=problem_statement_string,
        model_string=args.model,
        max_iterations_int=args.max_iterations
    )


if __name__ == "__main__":
    main()
