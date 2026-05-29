from dataclasses import dataclass

from backend.core.exceptions import InvalidChainError


@dataclass
class DeltaPair:
    left_index: int
    right_index: int
    left_name: str
    right_name: str
    pair_type: str      # "step" | "cumulative"
    step_number: int | None  # 1-based for "step", None for "cumulative"


def validate_chain(chain: list[int], available_indices: set[int]) -> None:
    """Raise InvalidChainError if the chain is structurally invalid.

    A valid chain:
    - has at least 2 elements (base + final)
    - has no duplicate indices
    - references only known scenario indices
    """
    if len(chain) < 2:
        raise InvalidChainError("Chain must contain at least 2 scenario indices.")
    if len(set(chain)) != len(chain):
        raise InvalidChainError("Chain contains duplicate scenario indices.")
    missing = sorted(i for i in chain if i not in available_indices)
    if missing:
        raise InvalidChainError(f"Scenario indices not found in upload: {missing}")


def build_delta_pairs(
    chain: list[int],
    index_to_name: dict[int, str],
) -> list[DeltaPair]:
    """Return the ordered list of delta pairs for an ordered scenario chain.

    Chain semantics (order matters):
      chain[0]   = base scenario  (reference — no delta to itself)
      chain[1:-1] = intermediate scenarios
      chain[-1]  = final scenario

    Pairs produced:
      Step deltas   — every consecutive transition (chain[i-1] → chain[i])
      Cumulative    — base → final (only when chain length > 2; otherwise
                      it would duplicate the single step delta)

    Example — chain [A, B, C]:
      (A→B, step 1), (B→C, step 2), (A→C, cumulative)
    """
    pairs: list[DeltaPair] = []

    for step, (left, right) in enumerate(zip(chain, chain[1:]), start=1):
        pairs.append(
            DeltaPair(
                left_index=left,
                right_index=right,
                left_name=index_to_name[left],
                right_name=index_to_name[right],
                pair_type="step",
                step_number=step,
            )
        )

    if len(chain) > 2:
        pairs.append(
            DeltaPair(
                left_index=chain[0],
                right_index=chain[-1],
                left_name=index_to_name[chain[0]],
                right_name=index_to_name[chain[-1]],
                pair_type="cumulative",
                step_number=None,
            )
        )

    return pairs
