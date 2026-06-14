import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))  # all imports rooted here: `from src.X`, `from tests.helpers`

import pytest
from tests.helpers import MockAdapter, make_triage_response
from src.inference.adapter import STRUCTURED_COLS


@pytest.fixture
def mock_adapter():
    return MockAdapter()


@pytest.fixture
def zero_features() -> dict:
    return {col: 0.0 for col in STRUCTURED_COLS}


@pytest.fixture
def sample_triage_response():
    return make_triage_response()


@pytest.fixture
def review_triage_response():
    return make_triage_response(
        email_id="test-id-002",
        label="analyst_review",
        predicted_class="phishing",
        spam_probability=0.48,
        phishing_probability=0.52,
        trust_score=60.0,
        routed_to_review=True,
    )
