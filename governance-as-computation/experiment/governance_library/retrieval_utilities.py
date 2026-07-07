#!/usr/bin/env python3
"""
Retrieval Utilities for Persona Deliberation

CRITICAL_LLM_CONTEXT:
    - Provides retrieval functions for Scientist persona
    - Retrieves existing governance schemas
    - Retrieves past successful deliberations
    - Simple keyword matching for MVP (can upgrade to semantic search)

WHY: Addresses learning panel critique "no retrieval"
     Scientist should see existing work before proposing
EVIDENCE: ADR-004 Library-First Learning
"""

from pathlib import Path
from typing import List, Optional
import re

from .json_session_manager import (
    DeliberationSessionSchema,
    list_past_sessions_list
)


def read_existing_governance_schema_string() -> str:
    """
    CRITICAL_LLM_CONTEXT:
        - Reads current commons_governance_schema.py
        - Returns as string for Scientist to review
        - Returns placeholder if file doesn't exist

    WHY: Scientist should see what already exists before proposing
    EVIDENCE: Learning panel - "linear pipeline, not retrieval-augmented"
    """
    schema_path = Path(__file__).parent / "commons_governance_schema.py"

    if schema_path.exists():
        return schema_path.read_text()

    return "# No existing governance schema found"


def retrieve_past_successful_deliberations_list(
    problem_query_string: str,
    limit_int: int = 3
) -> List[DeliberationSessionSchema]:
    """
    CRITICAL_LLM_CONTEXT:
        - Searches past session JSON files for similar problems
        - Returns list of DeliberationSessionSchema objects
        - Filters for approved/complete deliberations only
        - Uses simple keyword matching for MVP

    WHY: Learn from past successes instead of starting fresh
    EVIDENCE: ADR-004 Library-First Learning

    MATCHING STRATEGY (MVP):
        - Tokenize query into keywords (split on whitespace)
        - Match if ANY keyword appears in problem_statement_string
        - Case-insensitive matching
        - Can upgrade to semantic search later
    """
    # List all past deliberation sessions
    all_sessions_list = list_past_sessions_list()

    # Tokenize query into keywords
    query_keywords_list = [
        kw.lower().strip()
        for kw in problem_query_string.split()
        if len(kw.strip()) > 2  # Skip very short words
    ]

    # Filter for approved/complete + similar problems
    relevant_sessions_list = []

    for session_schema in all_sessions_list:
        # Only include successful deliberations
        if session_schema.status_string not in ("approved", "complete"):
            continue

        # Check for keyword matches in problem statement
        problem_lower_string = session_schema.problem_statement_string.lower()

        has_match_bool = any(
            keyword in problem_lower_string
            for keyword in query_keywords_list
        )

        if has_match_bool:
            relevant_sessions_list.append(session_schema)

    # Return top N matches (already sorted by date, newest first)
    return relevant_sessions_list[:limit_int]


def format_past_deliberations_string(
    sessions_list: List[DeliberationSessionSchema]
) -> str:
    """
    CRITICAL_LLM_CONTEXT:
        - Formats past deliberations for inclusion in Scientist prompt
        - Shows problem, solution summary, and key governance rules
        - Returns "None found" if empty list

    WHY: Scientist needs context to build on, not just raw data
    """
    if not sessions_list:
        return "None found - this may be the first deliberation on this topic."

    formatted_parts_list = []

    for idx_int, session_schema in enumerate(sessions_list, start=1):
        # Extract summary (first 200 chars of librarian schema or proposal)
        solution_string = session_schema.librarian_schema_string or session_schema.scientist_proposal_string
        solution_summary_string = solution_string[:500] + "..." if len(solution_string) > 500 else solution_string

        part_string = f"""
--- Past Deliberation #{idx_int} (Session: {session_schema.session_id_string}) ---
PROBLEM: {session_schema.problem_statement_string[:300]}...
STATUS: {session_schema.status_string}
ITERATIONS: {session_schema.iteration_count_int}
SOLUTION APPROACH:
{solution_summary_string}
"""
        formatted_parts_list.append(part_string)

    return "\n".join(formatted_parts_list)


def extract_judge_critique_categories_list(
    judge_evaluation_string: str
) -> List[str]:
    """
    CRITICAL_LLM_CONTEXT:
        - Extracts issue categories from Judge's critique using regex
        - Returns list like ["enforcement", "validation", "config_coupling"]
        - Used for targeted retrieval in next iteration
        - Empty evaluation returns empty list

    WHY: Targeted retrieval based on actual Judge concerns (not just problem keywords)
    EVIDENCE: Learning panel (Chase) - "stateless iteration, no targeted retrieval"

    PATTERN MATCHING STRATEGY:
        - Searches for common critique themes using regex
        - One category per theme (deduplicated)
        - Case-insensitive matching
    """
    if not judge_evaluation_string:
        return []

    critique_categories_list = []

    # Pattern matching for common critique themes
    patterns_dict = {
        "enforcement": ["enforcement", "enforc", "hook", "where.*applied", "mechanism.*not.*implement"],
        "validation": ["validation", "validate", "check.*invalid", "ensure.*comply"],
        "perception": ["agent.*perception", "agent.*see", "agent.*aware", "feedback loop"],
        "configuration": ["hardcoded", "coupling", "config", "parameteriz"],
        "math_errors": ["math.*wrong", "calculation.*incorrect", "formula.*error"],
        "adversarial": ["adversarial", "gaming", "exploit", "loophole"],
        "boundary_cases": ["edge case", "boundary", "threshold", "corner case"]
    }

    judge_lower_string = judge_evaluation_string.lower()

    for category_string, patterns_list in patterns_dict.items():
        for pattern_string in patterns_list:
            if re.search(pattern_string, judge_lower_string):
                critique_categories_list.append(category_string)
                break  # One match per category

    return list(set(critique_categories_list))  # Deduplicate


def retrieve_past_successful_deliberations_with_categories_list(
    problem_query_string: str,
    critique_categories_list: Optional[List[str]] = None,
    limit_int: int = 3
) -> List[DeliberationSessionSchema]:
    """
    CRITICAL_LLM_CONTEXT:
        - Retrieves past deliberations matching problem AND critique categories
        - If categories provided, prioritizes sessions that addressed those issues
        - Falls back to keyword matching if no category matches found
        - Returns top N sessions sorted by relevance

    WHY: Iteration-specific retrieval based on Judge feedback
         More targeted than just problem keywords
    EVIDENCE: Learning panel (Chase) - "no targeted retrieval between iterations"

    MATCHING STRATEGY:
        - If categories provided: prioritize sessions with matching categories
        - Sort by category match count (most matches first)
        - If no category matches: fall back to keyword matching (existing logic)
    """
    all_sessions_list = list_past_sessions_list()

    # Filter for approved/complete sessions only
    approved_sessions_list = [
        s for s in all_sessions_list
        if s.status_string in ("approved", "complete")
    ]

    # If categories provided, prioritize sessions with those themes
    if critique_categories_list:
        targeted_sessions_list = []

        for session_schema in approved_sessions_list:
            # Check if past session addressed similar categories
            # Search in problem statement + proposal + judge evaluation
            session_text_string = (
                session_schema.problem_statement_string + " " +
                session_schema.scientist_proposal_string + " " +
                session_schema.judge_evaluation_string
            ).lower()

            # Count how many categories match
            category_match_count_int = sum(
                1 for category in critique_categories_list
                if category in session_text_string
            )

            if category_match_count_int > 0:
                targeted_sessions_list.append((session_schema, category_match_count_int))

        # Sort by match count (descending), return top results
        targeted_sessions_list.sort(key=lambda x: x[1], reverse=True)

        if targeted_sessions_list:
            return [s[0] for s in targeted_sessions_list[:limit_int]]

    # Fallback to keyword matching (existing implementation)
    return retrieve_past_successful_deliberations_list(
        problem_query_string,
        limit_int
    )
