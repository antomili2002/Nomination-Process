"""Unit tests for backend/processing/chain_builder.py"""
import pytest

from backend.core.exceptions import InvalidChainError
from backend.processing.chain_builder import DeltaPair, build_delta_pairs, validate_chain

# Fixture scenario map matching conftest.py sample workbook
# index 0-5: Base_IV, Outage_IV, Final_IV, Base_EV, Outage_EV, Final_EV
INDEX_TO_NAME: dict[int, str] = {
    0: "Base_IV",
    1: "Outage_IV",
    2: "Final_IV",
    3: "Base_EV",
    4: "Outage_EV",
    5: "Final_EV",
}
AVAILABLE = set(INDEX_TO_NAME)


# validate_chain

def test_validate_raises_when_chain_too_short():
    with pytest.raises(InvalidChainError, match="at least 2"):
        validate_chain([0], AVAILABLE)


def test_validate_raises_on_duplicates():
    with pytest.raises(InvalidChainError, match="duplicate"):
        validate_chain([0, 0, 1], AVAILABLE)


def test_validate_raises_on_unknown_index():
    with pytest.raises(InvalidChainError, match="not found"):
        validate_chain([0, 99], AVAILABLE)


def test_validate_passes_for_two_element_chain():
    validate_chain([0, 1], AVAILABLE)  # must not raise


def test_validate_passes_for_three_element_chain():
    validate_chain([3, 4, 5], AVAILABLE)  # must not raise


# build_delta_pairs — two-element chain

def test_two_element_chain_yields_one_step():
    pairs = build_delta_pairs([0, 2], INDEX_TO_NAME)
    assert len(pairs) == 1
    assert pairs[0].pair_type == "step"
    assert pairs[0].step_number == 1


def test_two_element_chain_has_no_cumulative():
    pairs = build_delta_pairs([0, 2], INDEX_TO_NAME)
    assert all(p.pair_type != "cumulative" for p in pairs)


# build_delta_pairs — three-element chain

def test_three_element_chain_yields_two_steps_and_one_cumulative():
    pairs = build_delta_pairs([3, 4, 5], INDEX_TO_NAME)
    steps = [p for p in pairs if p.pair_type == "step"]
    cumulatives = [p for p in pairs if p.pair_type == "cumulative"]
    assert len(steps) == 2
    assert len(cumulatives) == 1


def test_step_numbers_are_sequential():
    pairs = build_delta_pairs([3, 4, 5], INDEX_TO_NAME)
    steps = [p for p in pairs if p.pair_type == "step"]
    assert [s.step_number for s in steps] == [1, 2]


def test_step_order_matches_chain():
    pairs = build_delta_pairs([3, 4, 5], INDEX_TO_NAME)
    steps = [p for p in pairs if p.pair_type == "step"]
    # step 1: Base_EV → Outage_EV
    assert steps[0].left_index == 3
    assert steps[0].right_index == 4
    # step 2: Outage_EV → Final_EV
    assert steps[1].left_index == 4
    assert steps[1].right_index == 5


def test_cumulative_spans_base_to_final():
    pairs = build_delta_pairs([3, 4, 5], INDEX_TO_NAME)
    cum = next(p for p in pairs if p.pair_type == "cumulative")
    assert cum.left_index == 3   # Base_EV
    assert cum.right_index == 5  # Final_EV
    assert cum.step_number is None


def test_names_are_resolved_correctly():
    pairs = build_delta_pairs([0, 1, 2], INDEX_TO_NAME)
    steps = [p for p in pairs if p.pair_type == "step"]
    assert steps[0].left_name == "Base_IV"
    assert steps[0].right_name == "Outage_IV"
    assert steps[1].left_name == "Outage_IV"
    assert steps[1].right_name == "Final_IV"
    cum = next(p for p in pairs if p.pair_type == "cumulative")
    assert cum.left_name == "Base_IV"
    assert cum.right_name == "Final_IV"
