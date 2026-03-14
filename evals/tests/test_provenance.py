"""Tests for provenance tracking."""

from unittest.mock import MagicMock

from evals.framework.prompt import ResolvedPrompt
from evals.framework.provenance import GitState, Provenance, hash_dataset


class TestGitState:
    """Tests for GitState capture."""

    def test_capture_returns_git_info(self):
        """GitState.capture() should return git state."""
        state = GitState.capture()

        # Should have values (may be 'unknown' if not in git repo)
        assert state.commit is not None
        assert state.branch is not None
        assert isinstance(state.dirty, bool)


class TestHashDataset:
    """Tests for dataset hashing."""

    def test_hash_is_deterministic(self):
        """Same dataset should produce same hash."""
        case1 = MagicMock()
        case1.inputs = MagicMock()
        case1.inputs.model_dump.return_value = {"message": "hello"}
        case1.expected_output = MagicMock()
        case1.expected_output.model_dump.return_value = {"task": "consult"}

        case2 = MagicMock()
        case2.inputs = MagicMock()
        case2.inputs.model_dump.return_value = {"message": "world"}
        case2.expected_output = MagicMock()
        case2.expected_output.model_dump.return_value = {"task": "reflect"}

        cases = [case1, case2]

        hash1 = hash_dataset(cases)
        hash2 = hash_dataset(cases)

        assert hash1 == hash2
        assert len(hash1) == 12

    def test_different_datasets_different_hash(self):
        """Different datasets should produce different hashes."""
        case_a = MagicMock()
        case_a.inputs = MagicMock()
        case_a.inputs.model_dump.return_value = {"message": "hello"}
        case_a.expected_output = None

        case_b = MagicMock()
        case_b.inputs = MagicMock()
        case_b.inputs.model_dump.return_value = {"message": "goodbye"}
        case_b.expected_output = None

        hash1 = hash_dataset([case_a])
        hash2 = hash_dataset([case_b])

        assert hash1 != hash2


class TestProvenance:
    """Tests for Provenance capture."""

    def test_capture_creates_provenance(self):
        """Provenance.capture should create full provenance."""
        prompt = ResolvedPrompt(
            content="test prompt",
            source="inline",
            ref=None,
            version=None,
            hash="abc123def456",
        )

        case = MagicMock()
        case.inputs = MagicMock()
        case.inputs.model_dump.return_value = {"message": "test"}
        case.expected_output = None

        provenance = Provenance.capture(
            prompt=prompt,
            dataset_name="test_dataset",
            cases=[case],
        )

        assert provenance.prompt == prompt
        assert provenance.dataset_name == "test_dataset"
        assert provenance.case_count == 1
        assert provenance.dataset_hash is not None

    def test_captures_git_state(self):
        """Provenance should capture git state."""
        prompt = ResolvedPrompt(
            content="test",
            source="inline",
            ref=None,
            version=None,
            hash="abc123",
        )

        case = MagicMock()
        case.inputs = MagicMock()
        case.inputs.model_dump.return_value = {}
        case.expected_output = None

        provenance = Provenance.capture(
            prompt=prompt,
            dataset_name="test",
            cases=[case],
        )

        assert provenance.git_commit is not None
        assert provenance.git_branch is not None
