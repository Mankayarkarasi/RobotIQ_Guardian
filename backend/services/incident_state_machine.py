"""
RoboIQ Guardian Incident State Machine

Controls valid incident lifecycle transitions.

The state machine prevents the API from jumping
directly between unrelated recovery states.
"""

from typing import Dict


VALID_TRANSITIONS = {
    "NORMAL": {
        "FAILURE_DETECTED",
    },

    "FAILURE_DETECTED": {
        "INVESTIGATING",
    },

    "INVESTIGATING": {
        "ROOT_CAUSE_IDENTIFIED",
    },

    "ROOT_CAUSE_IDENTIFIED": {
        "RECOVERY_PROPOSED",
    },

    "RECOVERY_PROPOSED": {
        "RECOVERY_APPROVED",
    },

    "RECOVERY_APPROVED": {
        "RECOVERING",
    },

    "RECOVERING": {
        "VERIFYING",
        "RECOVERY_FAILED",
    },

    "VERIFYING": {
        "RECOVERED",
        "RECOVERY_FAILED",
    },

    # Terminal states
    "RECOVERED": set(),
    "RECOVERY_FAILED": set(),
}


def transition_state(
    current_state: str,
    next_state: str
) -> Dict:
    """
    Validate a requested incident-state transition.

    Returns:
        {
            "status": "STATE_TRANSITION_SUCCESS",
            "from_state": "...",
            "to_state": "..."
        }

    or:

        {
            "status": "INVALID_STATE_TRANSITION",
            ...
        }
    """

    if current_state not in VALID_TRANSITIONS:
        return {
            "status": "INVALID_STATE",
            "message":
                f"Unknown current state: {current_state}",
            "from_state": current_state,
            "to_state": next_state,
        }

    if next_state not in VALID_TRANSITIONS:
        return {
            "status": "INVALID_STATE",
            "message":
                f"Unknown target state: {next_state}",
            "from_state": current_state,
            "to_state": next_state,
        }

    allowed_next_states = VALID_TRANSITIONS[
        current_state
    ]

    if next_state not in allowed_next_states:
        return {
            "status":
                "INVALID_STATE_TRANSITION",
            "message":
                (
                    f"Transition from "
                    f"{current_state} to "
                    f"{next_state} is not allowed."
                ),
            "from_state":
                current_state,
            "to_state":
                next_state,
            "allowed_next_states":
                sorted(
                    allowed_next_states
                ),
        }

    return {
        "status":
            "STATE_TRANSITION_SUCCESS",
        "from_state":
            current_state,
        "to_state":
            next_state,
    }


if __name__ == "__main__":

    print(
        "--- RoboIQ Guardian "
        "Incident State Machine ---"
    )

    test_sequence = [
        "NORMAL",
        "FAILURE_DETECTED",
        "INVESTIGATING",
        "ROOT_CAUSE_IDENTIFIED",
        "RECOVERY_PROPOSED",
        "RECOVERY_APPROVED",
        "RECOVERING",
        "VERIFYING",
        "RECOVERED",
    ]

    current_state = test_sequence[0]

    print(
        f"Initial State: {current_state}"
    )

    for next_state in test_sequence[1:]:

        result = transition_state(
            current_state,
            next_state,
        )

        print(
            f"{current_state} "
            f"-> {next_state}: "
            f"{result['status']}"
        )

        if (
            result["status"]
            == "STATE_TRANSITION_SUCCESS"
        ):
            current_state = next_state

        else:
            print(result)
            break

    print(
        f"Final State: {current_state}"
    )