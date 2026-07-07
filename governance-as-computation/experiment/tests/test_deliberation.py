#!/usr/bin/env python3
"""
Tests for Persona Deliberation with Iteration and Retrieval

CRITICAL_LLM_CONTEXT:
    - Tests JSON session manager (read/write/update)
    - Tests retrieval utilities (past sessions, existing schemas)
    - Tests iteration loop logic (without calling Claude CLI)
    - Does NOT test actual Claude CLI calls (those are expensive)

WHY: Unit tests ensure core logic works before expensive LLM calls
EVIDENCE: Learning panel recommendation for testable components
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_library.json_session_manager import (
    DeliberationSessionSchema,
    read_session_schema,
    update_session_void,
    list_past_sessions_list,
    create_new_session_schema,
    delete_session_void,
    get_session_file_path,
    SESSIONS_DIR_PATH
)
from governance_library.retrieval_utilities import (
    read_existing_governance_schema_string,
    retrieve_past_successful_deliberations_list,
    format_past_deliberations_string
)
from governance_library.deliberation_ablation import (
    evaluate_schema_in_mock_env_dict
)


class TestJSONSessionManager:
    """Tests for JSON session read/write/update functionality"""

    def test_create_and_read_session(self):
        """
        SCENARIO: Create a new session and read it back
        EXPECTED: Session data matches what was created
        WHY: Core session persistence functionality
        """
        # Create session
        session_schema = create_new_session_schema(
            problem_statement_string="Test problem for unit test",
            max_iterations_int=2
        )

        assert session_schema.session_id_string.startswith("deliberation-")
        assert session_schema.problem_statement_string == "Test problem for unit test"
        assert session_schema.max_iterations_int == 2
        assert session_schema.status_string == "in_progress"
        assert session_schema.iteration_count_int == 0

        # Read back
        read_schema = read_session_schema(session_schema.session_id_string)

        assert read_schema.session_id_string == session_schema.session_id_string
        assert read_schema.problem_statement_string == session_schema.problem_statement_string

        # Cleanup
        delete_session_void(session_schema.session_id_string)

    def test_update_session_fields(self):
        """
        SCENARIO: Update session fields and verify persistence
        EXPECTED: Changes are saved to JSON and readable
        WHY: Iteration loop depends on updating session state
        """
        # Create session
        session_schema = create_new_session_schema(
            problem_statement_string="Test problem"
        )
        session_id = session_schema.session_id_string

        # Update fields
        session_schema.scientist_proposal_string = "My proposal"
        session_schema.iteration_count_int = 1
        session_schema.status_string = "scientist_done"
        update_session_void(session_schema)

        # Read back and verify
        read_schema = read_session_schema(session_id)
        assert read_schema.scientist_proposal_string == "My proposal"
        assert read_schema.iteration_count_int == 1
        assert read_schema.status_string == "scientist_done"

        # Cleanup
        delete_session_void(session_id)

    def test_session_not_found_raises_error(self):
        """
        SCENARIO: Try to read a non-existent session
        EXPECTED: FileNotFoundError raised
        WHY: Clear error handling for missing sessions
        """
        with pytest.raises(FileNotFoundError):
            read_session_schema("nonexistent-session-id")

    def test_list_past_sessions(self):
        """
        SCENARIO: Create multiple sessions and list them
        EXPECTED: All sessions returned, sorted by date
        WHY: Retrieval needs to list past sessions
        """
        # Create a few sessions
        session_ids = []
        for i in range(3):
            schema = create_new_session_schema(f"Problem {i}")
            session_ids.append(schema.session_id_string)

        # List sessions
        sessions_list = list_past_sessions_list()

        # Verify our sessions are in the list
        listed_ids = [s.session_id_string for s in sessions_list]
        for session_id in session_ids:
            assert session_id in listed_ids

        # Cleanup
        for session_id in session_ids:
            delete_session_void(session_id)

    def test_atomic_write_creates_valid_json(self):
        """
        SCENARIO: Verify session file is valid JSON after write
        EXPECTED: File can be parsed by json.load
        WHY: Atomic writes should prevent corruption
        """
        session_schema = create_new_session_schema("Test atomic write")

        file_path = get_session_file_path(session_schema.session_id_string)

        with open(file_path, 'r') as f:
            data = json.load(f)

        assert data["session_id_string"] == session_schema.session_id_string
        assert data["problem_statement_string"] == "Test atomic write"

        # Cleanup
        delete_session_void(session_schema.session_id_string)


class TestRetrievalUtilities:
    """Tests for retrieval functionality"""

    def test_read_existing_schema_returns_string(self):
        """
        SCENARIO: Read existing governance schema file
        EXPECTED: Returns non-empty string or placeholder
        WHY: Scientist needs to see existing work
        """
        schema_string = read_existing_governance_schema_string()

        # Should return something (either real schema or placeholder)
        assert isinstance(schema_string, str)
        assert len(schema_string) > 0

    def test_retrieve_past_deliberations_filters_approved(self):
        """
        SCENARIO: Only approved/complete sessions should be retrieved
        EXPECTED: in_progress sessions not returned
        WHY: Learn from successes, not incomplete work
        """
        # Create approved session
        approved_session = create_new_session_schema("Pasture collapse problem")
        approved_session.status_string = "approved"
        approved_session.scientist_proposal_string = "Approved solution"
        update_session_void(approved_session)

        # Create in_progress session
        incomplete_session = create_new_session_schema("Another pasture problem")
        incomplete_session.status_string = "in_progress"
        update_session_void(incomplete_session)

        # Retrieve should only return approved
        results = retrieve_past_successful_deliberations_list(
            "pasture collapse",
            limit_int=10
        )

        result_ids = [s.session_id_string for s in results]

        assert approved_session.session_id_string in result_ids
        assert incomplete_session.session_id_string not in result_ids

        # Cleanup
        delete_session_void(approved_session.session_id_string)
        delete_session_void(incomplete_session.session_id_string)

    def test_retrieve_matches_keywords(self):
        """
        SCENARIO: Retrieval should match keywords in problem statement
        EXPECTED: Sessions with matching keywords returned
        WHY: Relevant past deliberations should be found
        """
        # Create session with specific keywords
        session = create_new_session_schema("Commons collapse grass pasture simulation")
        session.status_string = "complete"
        update_session_void(session)

        # Search with matching keyword
        results = retrieve_past_successful_deliberations_list(
            "grass pasture",
            limit_int=5
        )

        assert len(results) > 0
        assert any(s.session_id_string == session.session_id_string for s in results)

        # Cleanup
        delete_session_void(session.session_id_string)

    def test_format_past_deliberations_empty(self):
        """
        SCENARIO: Format empty list of deliberations
        EXPECTED: Returns informative message
        WHY: Handle edge case gracefully
        """
        result = format_past_deliberations_string([])

        assert "None found" in result

    def test_format_past_deliberations_with_data(self):
        """
        SCENARIO: Format list of past deliberations
        EXPECTED: Returns formatted string with session details
        WHY: Scientist needs readable context
        """
        # Create a mock session
        session = DeliberationSessionSchema(
            session_id_string="test-session-123",
            problem_statement_string="Test problem",
            scientist_proposal_string="Test proposal",
            status_string="approved",
            iteration_count_int=2
        )

        result = format_past_deliberations_string([session])

        assert "test-session-123" in result
        assert "approved" in result
        assert "2" in result  # iteration count


class TestAblationEvaluation:
    """Tests for ablation study schema evaluation"""

    def test_evaluate_valid_python(self):
        """
        SCENARIO: Evaluate valid Python schema
        EXPECTED: valid_python_bool = True
        WHY: Need to verify generated code is syntactically correct
        """
        valid_schema = '''
from dataclasses import dataclass

@dataclass
class TestSchema:
    """CRITICAL_LLM_CONTEXT: Test"""
    value_int: int = 10

    def calculate_enforcement_int(self, x: int) -> int:
        return min(x, self.value_int)
'''
        result = evaluate_schema_in_mock_env_dict(valid_schema, "test_valid")

        assert result["valid_python_bool"] is True
        assert result["has_dataclass_bool"] is True
        assert result["has_critical_context_bool"] is True
        assert result["has_enforcement_method_bool"] is True

    def test_evaluate_invalid_python(self):
        """
        SCENARIO: Evaluate invalid Python code
        EXPECTED: valid_python_bool = False, error captured
        WHY: Need to catch syntax errors in generated schemas
        """
        invalid_schema = '''
@dataclass
class Broken:
    def bad_syntax(
        return "missing paren"
'''
        result = evaluate_schema_in_mock_env_dict(invalid_schema, "test_invalid")

        assert result["valid_python_bool"] is False
        assert result["error_string"] != ""

    def test_evaluate_missing_components(self):
        """
        SCENARIO: Schema missing key components
        EXPECTED: has_* flags reflect missing components
        WHY: Track schema quality metrics
        """
        minimal_schema = '''
class SimpleClass:
    value = 10
'''
        result = evaluate_schema_in_mock_env_dict(minimal_schema, "test_minimal")

        assert result["valid_python_bool"] is True
        assert result["has_dataclass_bool"] is False
        assert result["has_critical_context_bool"] is False
        assert result["has_enforcement_method_bool"] is False


class TestIterationLoopLogic:
    """Tests for iteration loop logic (without actual Claude CLI calls)"""

    def test_session_tracks_iterations(self):
        """
        SCENARIO: Session iteration_count_int increments correctly
        EXPECTED: Each update increments the counter
        WHY: Track refinement cycles
        """
        session = create_new_session_schema("Test iteration tracking")

        assert session.iteration_count_int == 0

        # Simulate iteration
        session.iteration_count_int += 1
        session.scientist_proposal_string = "Proposal v1"
        update_session_void(session)

        read_session = read_session_schema(session.session_id_string)
        assert read_session.iteration_count_int == 1

        # Second iteration
        read_session.iteration_count_int += 1
        read_session.scientist_proposal_string = "Proposal v2"
        update_session_void(read_session)

        read_session = read_session_schema(session.session_id_string)
        assert read_session.iteration_count_int == 2

        # Cleanup
        delete_session_void(session.session_id_string)

    def test_judge_verdict_stored(self):
        """
        SCENARIO: Judge verdict stored in session
        EXPECTED: judge_verdict_string reflects approval/rejection
        WHY: Controls iteration loop continuation
        """
        session = create_new_session_schema("Test verdict")

        # Simulate rejection
        session.judge_verdict_string = "rejected"
        session.judge_evaluation_string = "Math doesn't work"
        update_session_void(session)

        read_session = read_session_schema(session.session_id_string)
        assert read_session.judge_verdict_string == "rejected"
        assert "Math" in read_session.judge_evaluation_string

        # Simulate approval
        read_session.judge_verdict_string = "approved"
        update_session_void(read_session)

        read_session = read_session_schema(session.session_id_string)
        assert read_session.judge_verdict_string == "approved"

        # Cleanup
        delete_session_void(session.session_id_string)

    def test_status_transitions(self):
        """
        SCENARIO: Session status transitions through lifecycle
        EXPECTED: Status reflects deliberation progress
        WHY: Track deliberation state for resumption
        """
        session = create_new_session_schema("Test status")

        assert session.status_string == "in_progress"

        # Simulate approval
        session.status_string = "approved"
        update_session_void(session)
        read_session = read_session_schema(session.session_id_string)
        assert read_session.status_string == "approved"

        # Simulate completion
        read_session.status_string = "complete"
        update_session_void(read_session)
        read_session = read_session_schema(session.session_id_string)
        assert read_session.status_string == "complete"

        # Cleanup
        delete_session_void(session.session_id_string)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
