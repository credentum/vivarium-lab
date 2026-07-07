#!/usr/bin/env python3
"""
JSON Session Manager for Persona Deliberation

CRITICAL_LLM_CONTEXT:
    - Manages deliberation session state as JSON files
    - One JSON file per session in deliberations/sessions/
    - Enables iteration (Judge rejects → Scientist reads → refines)
    - Enables retrieval (list past sessions for similar problems)

WHY: Simple file-based persistence for MVP (no API dependencies)
EVIDENCE: Learning panel recommendation for iteration + retrieval support
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import tempfile
import os


# Default sessions directory relative to this file
SESSIONS_DIR_PATH = Path(__file__).parent / "deliberations" / "sessions"


@dataclass
class IterationMetricsSchema:
    """
    CRITICAL_LLM_CONTEXT:
        - Tracks quality metrics for one iteration
        - Used to measure convergence across iterations
        - iteration_number_int: Which iteration (1, 2, 3...)
        - proposal_length_int: Length of Scientist's proposal (chars)
        - judge_verdict_string: "approved" | "rejected"
        - critique_count_int: Number of issue categories Judge identified
        - categories_addressed_int: How many prior categories did Scientist fix?
        - new_categories_int: How many NEW issues did Judge find?
        - timestamp_string: ISO timestamp when iteration completed

    WHY: Quantify improvement across iterations, detect stagnation
    EVIDENCE: Learning panel (Chollet) - "measure convergence"
    """
    iteration_number_int: int
    proposal_length_int: int
    judge_verdict_string: str
    critique_count_int: int
    categories_addressed_int: int
    new_categories_int: int
    timestamp_string: str


@dataclass
class DeliberationSessionSchema:
    """
    CRITICAL_LLM_CONTEXT:
        - session_id_string: Unique identifier (deliberation-YYYYMMDD_HHMMSS)
        - problem_statement_string: Original problem (immutable after creation)
        - scientist_proposal_string: Current proposal (updated each iteration)
        - judge_evaluation_string: Judge's feedback (used by Scientist to refine)
        - judge_verdict_string: "approved" | "rejected" | "" (empty = not evaluated)
        - librarian_schema_string: Final schema code (set after approval)
        - status_string: "in_progress" | "approved" | "complete" | "needs_human_review"
        - iteration_count_int: Current iteration number (0 = not started)
        - max_iterations_int: Stop condition (default 3)
        - created_at_string: ISO timestamp (when session started)
        - updated_at_string: ISO timestamp (last modification)
        - critique_categories_list: Categories extracted from Judge critique (for targeted retrieval)
        - retrieved_session_ids_list: Session IDs retrieved from past deliberations (cache)
        - iteration_history_list: Full history of all iterations with metrics

    WHY: Single JSON file per session with all state in one place
         Enables: iteration, retrieval, resumption, audit trail, convergence tracking
    EVIDENCE: Learning panel - "fire-and-forget is insufficient", "stateless iteration", "no convergence metrics"
    """
    session_id_string: str
    problem_statement_string: str
    scientist_proposal_string: str = ""
    judge_evaluation_string: str = ""
    judge_verdict_string: str = ""
    librarian_schema_string: str = ""
    status_string: str = "in_progress"
    iteration_count_int: int = 0
    max_iterations_int: int = 3
    created_at_string: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at_string: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    critique_categories_list: List[str] = field(default_factory=list)
    retrieved_session_ids_list: List[str] = field(default_factory=list)
    iteration_history_list: List[Dict[str, Any]] = field(default_factory=list)


def get_session_file_path(session_id_string: str) -> Path:
    """
    CRITICAL_LLM_CONTEXT:
        - Returns path to session JSON file
        - Path: deliberations/sessions/{session_id}.json

    WHY: Centralized path logic prevents path construction errors
    """
    return SESSIONS_DIR_PATH / f"{session_id_string}.json"


def read_session_schema(session_id_string: str) -> DeliberationSessionSchema:
    """
    CRITICAL_LLM_CONTEXT:
        - Reads session JSON from deliberations/sessions/{session_id}.json
        - Returns parsed DeliberationSessionSchema
        - Raises FileNotFoundError if session doesn't exist
        - Raises json.JSONDecodeError if JSON is corrupted

    WHY: Personas read session state from file before acting
    EVIDENCE: Enables iteration loop (Scientist reads Judge rejection)
    """
    file_path = get_session_file_path(session_id_string)

    if not file_path.exists():
        raise FileNotFoundError(f"Session not found: {session_id_string}")

    with open(file_path, "r") as f:
        data_dict = json.load(f)

    return DeliberationSessionSchema(**data_dict)


def update_session_void(session_schema: DeliberationSessionSchema) -> None:
    """
    CRITICAL_LLM_CONTEXT:
        - Writes session schema to JSON file
        - Updates updated_at_string timestamp automatically
        - Creates parent directory if needed
        - Uses atomic write (temp file + rename) to prevent corruption

    WHY: Personas update session state after each step
    EVIDENCE: Atomic writes prevent corruption on crash
    """
    # Ensure directory exists
    SESSIONS_DIR_PATH.mkdir(parents=True, exist_ok=True)

    # Update timestamp
    session_schema.updated_at_string = datetime.utcnow().isoformat()

    # Convert to dict
    data_dict = asdict(session_schema)

    # Atomic write: temp file then rename
    file_path = get_session_file_path(session_schema.session_id_string)

    # Write to temp file first
    fd, temp_path = tempfile.mkstemp(
        dir=SESSIONS_DIR_PATH,
        suffix=".json.tmp"
    )
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data_dict, f, indent=2)
        # Atomic rename
        os.replace(temp_path, file_path)
    except Exception:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def list_past_sessions_list() -> List[DeliberationSessionSchema]:
    """
    CRITICAL_LLM_CONTEXT:
        - Lists all sessions in deliberations/sessions/
        - Returns list of parsed session schemas
        - Skips corrupted JSON files (logs warning)
        - Sorted by created_at (newest first)

    WHY: Enable retrieval of past deliberations for learning
    EVIDENCE: ADR-004 Library-First Learning
    """
    if not SESSIONS_DIR_PATH.exists():
        return []

    sessions_list = []

    for json_file_path in SESSIONS_DIR_PATH.glob("*.json"):
        try:
            with open(json_file_path, "r") as f:
                data_dict = json.load(f)
            session_schema = DeliberationSessionSchema(**data_dict)
            sessions_list.append(session_schema)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            # Skip corrupted files but log
            print(f"Warning: Skipping corrupted session file {json_file_path}: {e}")
            continue

    # Sort by created_at descending (newest first)
    sessions_list.sort(
        key=lambda s: s.created_at_string,
        reverse=True
    )

    return sessions_list


def create_new_session_schema(
    problem_statement_string: str,
    max_iterations_int: int = 3
) -> DeliberationSessionSchema:
    """
    CRITICAL_LLM_CONTEXT:
        - Creates a new deliberation session with unique ID
        - Session ID format: deliberation-YYYYMMDD_HHMMSS
        - Saves to JSON file immediately
        - Returns the created session schema

    WHY: Convenience function for creating and persisting sessions
    """
    session_id_string = f"deliberation-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    session_schema = DeliberationSessionSchema(
        session_id_string=session_id_string,
        problem_statement_string=problem_statement_string,
        max_iterations_int=max_iterations_int
    )

    update_session_void(session_schema)

    return session_schema


def delete_session_void(session_id_string: str) -> None:
    """
    CRITICAL_LLM_CONTEXT:
        - Deletes session JSON file
        - Raises FileNotFoundError if session doesn't exist

    WHY: Cleanup function for tests
    """
    file_path = get_session_file_path(session_id_string)

    if not file_path.exists():
        raise FileNotFoundError(f"Session not found: {session_id_string}")

    file_path.unlink()
