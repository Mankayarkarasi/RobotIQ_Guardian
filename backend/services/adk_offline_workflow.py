
"""
RoboIQ Guardian — offline Google ADK orchestration.

Runs five deterministic, evidence-backed stages through
the genuine ADK Runner and SequentialAgent.

No LLM calls. No physical control or recovery execution.
"""

import asyncio
import json
from typing import Any, Dict, List

from pydantic import Field
from google.genai import types
from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from backend.services.adk_tools import (
    get_robot_telemetry,
    get_video_observations,
    get_incident_evidence,
    get_root_cause_hypotheses,
    get_recovery_plan,
    assess_recovery_risk,
    get_recovery_outcome,
)


class OfflineGuardianStage(BaseAgent):
    stage: str = Field(description="Guardian workflow stage")

    async def _run_async_impl(self, ctx: InvocationContext):
        incident_id = ctx.session.state.get("incident_id")
        if not incident_id:
            raise ValueError("Incident ID is required")

        # Deliberately omit simulate_recovery_option.
        # Recovery execution requires separate backend approval.
        stage_tools = {
            "prediction": [get_robot_telemetry],
            "prevention": [get_robot_telemetry],
            "investigation": [
                get_video_observations,
                get_incident_evidence,
                get_root_cause_hypotheses,
            ],
            "recovery": [
                get_recovery_plan,
                assess_recovery_risk,
            ],
            "learning": [get_recovery_outcome],
        }

        results = {}
        for tool in stage_tools[self.stage]:
            results[tool.__name__] = tool(incident_id)

        record = {
            "agent": self.name,
            "stage": self.stage,
            "incident_id": incident_id,
            "status": "COMPLETED",
            "tools": list(results.keys()),
            "results": results,
            "execution_mode": "adk_offline_runner",
        }

        previous_trace = ctx.session.state.get(
            "guardian_trace", []
        )
        updated_trace = previous_trace + [record]

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=json.dumps(
                            {
                                "agent": self.name,
                                "status": "COMPLETED",
                                "tools": record["tools"],
                            }
                        )
                    )
                ],
            ),
            actions=EventActions(
                state_delta={
                    "guardian_trace": updated_trace,
                    f"{self.stage}_status": "COMPLETED",
                }
            ),
        )


def create_guardian_workflow() -> SequentialAgent:
    stages = [
        ("PredictionOffline", "prediction"),
        ("PreventionOffline", "prevention"),
        ("InvestigationOffline", "investigation"),
        ("RecoveryOffline", "recovery"),
        ("LearningOffline", "learning"),
    ]

    agents = [
        OfflineGuardianStage(name=name, stage=stage)
        for name, stage in stages
    ]

    return SequentialAgent(
        name="RoboIQGuardianOfflineWorkflow",
        sub_agents=agents,
        description=(
            "Five-stage evidence-backed recovery investigation "
            "using ADK without model inference."
        ),
    )


async def run_guardian_workflow(
    incident_id: str,
) -> Dict[str, Any]:
    app_name = "roboiq_guardian_offline"
    user_id = "backend"
    session_id = "incident_workflow"

    session_service = InMemorySessionService()

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={"incident_id": incident_id},
    )

    runner = Runner(
        agent=create_guardian_workflow(),
        app_name=app_name,
        session_service=session_service,
    )

    event_authors: List[str] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[
                types.Part(
                    text=f"Analyze incident {incident_id}"
                )
            ],
        ),
    ):
        event_authors.append(event.author)
        print("ADK EVENT:", event.author)

    session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )

    if session is None:
        raise RuntimeError("ADK session not found")

    trace = session.state.get("guardian_trace", [])

    if len(trace) != 5:
        raise RuntimeError(
            f"Expected 5 completed stages, got {len(trace)}"
        )

    expected = [
        "prediction",
        "prevention",
        "investigation",
        "recovery",
        "learning",
    ]

    assert [r["stage"] for r in trace] == expected
    assert all(r["status"] == "COMPLETED" for r in trace)

    return {
        "incident_id": incident_id,
        "status": "COMPLETED",
        "execution_mode": "adk_offline_runner",
        "framework": "Google ADK",
        "model_calls": 0,
        "agent_events": event_authors,
        "trace": trace,
    }


async def main():
    # Replace with an incident accessible to this Python process.
    result = await run_guardian_workflow(
        "INC-C54A7B70"
    )

    print(
        "ADK_WORKFLOW_TEST:",
        "PASS" if result["status"] == "COMPLETED" else "FAIL",
    )
    print("AGENT_STAGES:", len(result["trace"]))
    print("MODEL_CALLS:", result["model_calls"])


if __name__ == "__main__":
    asyncio.run(main())
