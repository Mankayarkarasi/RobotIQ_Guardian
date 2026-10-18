
import asyncio

from google.genai import types
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.events.event_actions import EventActions

class OfflinePredictionAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        # This is a no-cost Runner test, not yet telemetry analysis.
        yield Event(
    author=self.name,
    content=types.Content(
        role="model",
        parts=[
            types.Part(text="Offline prediction stage executed")
        ],
    ),
    actions=EventActions(
        state_delta={
            "prediction_stage": "COMPLETED"
        }
    ),
)


async def main():
    app_name = "roboiq_offline_test"
    user_id = "local_test"
    session_id = "adk_smoke_001"

    session_service = InMemorySessionService()

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )

    runner = Runner(
        agent=OfflinePredictionAgent(name="PredictionAgentOffline"),
        app_name=app_name,
        session_service=session_service,
    )

    events = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Run offline prediction stage")],
        ),
    ):
        events.append(event)
        print("ADK EVENT:", event.author)

    session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )

    assert events, "No ADK Runner events emitted"
    assert session is not None
    assert session.state.get("prediction_stage") == "COMPLETED"

    print("ADK_RUNNER_TEST: PASS")


if __name__ == "__main__":
    asyncio.run(main())
