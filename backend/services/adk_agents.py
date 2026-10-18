"""
RoboIQ Guardian - Google ADK Agents
Defines genuine Google ADK Agent instances for failure investigation and recovery.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from backend.services.adk_tools import (
    get_robot_telemetry,
    get_video_observations,
    get_incident_evidence,
    get_root_cause_hypotheses,
    get_recovery_plan,
    assess_recovery_risk,
    simulate_recovery_option,
    get_recovery_outcome,
)

# =========================================================
# WRAP FUNCTIONS AS GOOGLE ADK FUNCTION TOOLS
# =========================================================

tool_get_telemetry = FunctionTool(get_robot_telemetry)
tool_get_video = FunctionTool(get_video_observations)
tool_get_evidence = FunctionTool(get_incident_evidence)
tool_get_hypotheses = FunctionTool(get_root_cause_hypotheses)
tool_get_recovery_plan = FunctionTool(get_recovery_plan)
tool_assess_risk = FunctionTool(assess_recovery_risk)
tool_simulate_recovery = FunctionTool(simulate_recovery_option)
tool_get_outcome = FunctionTool(get_recovery_outcome)

ADK_TOOLS_LIST = [
    tool_get_telemetry,
    tool_get_video,
    tool_get_evidence,
    tool_get_hypotheses,
    tool_get_recovery_plan,
    tool_assess_risk,
    tool_simulate_recovery,
    tool_get_outcome,
]

# =========================================================
# 1. PREDICTION AGENT
# Reviews recorded telemetry and identifies failure indicators.
# =========================================================

prediction_agent = Agent(
    name="PredictionAgent",
    description="Reviews recorded manipulator sensor telemetry and identifies threshold breaches.",
    instruction=(
        "You are the RoboIQ Guardian Prediction Agent. Your responsibility is to analyze "
        "industrial robot telemetry (cycle_time, position_error, joint_3_vibration, "
        "motor_current, temperature) against configured baseline thresholds and identify "
        "operational failure indicators."
    ),
    tools=[tool_get_telemetry],
)

# =========================================================
# 2. PREVENTION AGENT
# Recommends preventive containment actions.
# =========================================================

prevention_agent = Agent(
    name="PreventionAgent",
    description="Recommends preventive containment actions to safeguard robotic workcells.",
    instruction=(
        "You are the RoboIQ Guardian Prevention Agent. When anomalies or threshold breaches "
        "are detected, your role is to recommend immediate protective containment actions, "
        "including halting production cell cycles (PAUSED state) and engaging safety interlocks."
    ),
    tools=[tool_get_telemetry],
)

# =========================================================
# 3. INVESTIGATION AGENT
# Correlates telemetry with Gemini Robotics ER 2 visual observations
# and ranks root-cause hypotheses.
# =========================================================

investigation_agent = Agent(
    name="InvestigationAgent",
    description=(
        "Correlates deterministic telemetry with Gemini Robotics ER 2 visual observations "
        "and evaluates competing root-cause hypotheses."
    ),
    instruction=(
        "You are the RoboIQ Guardian Investigation Agent. You synthesize multimodal evidence "
        "(telemetry threshold breaches T1-T5 and Gemini Robotics ER 2 observations V6-V10), "
        "correlate sensor signals with physical visual behaviors, and rank competing root-cause "
        "hypotheses based on empirical evidence scores (not calibrated probabilities)."
    ),
    tools=[
        tool_get_telemetry,
        tool_get_video,
        tool_get_evidence,
        tool_get_hypotheses,
    ],
)

# =========================================================
# 4. RECOVERY AGENT
# Evaluates recovery options, residual risk, and required validation.
# =========================================================

recovery_agent = Agent(
    name="RecoveryAgent",
    description="Evaluates governed recovery sequences, residual risk, and validation criteria.",
    instruction=(
        "You are the RoboIQ Guardian Recovery Agent. You inspect AI-proposed recovery action "
        "sequences, evaluate residual operational risk under simulated maintenance constraints, "
        "enforce mandatory human authorization gates, and prescribe rigorous post-recovery "
        "verification criteria. Never authorize production resumption from simulated repair alone."
    ),
    tools=[
        tool_get_recovery_plan,
        tool_assess_risk,
        tool_simulate_recovery,
    ],
)

# =========================================================
# 5. LEARNING AGENT
# Captures validated incident outcomes and calculates PSR when data is available.
# =========================================================

learning_agent = Agent(
    name="LearningAgent",
    description="Captures closed-loop incident outcomes and computes empirical PSR metrics.",
    instruction=(
        "You are the RoboIQ Guardian Learning Agent. You record audit trail events for "
        "longitudinal reliability analytics, inspect post-recovery verification results, and "
        "derive empirical Predicted/Post Success Ratio (PSR) metrics when verified outcomes "
        "are available. If verification is incomplete, mark PSR as pending."
    ),
    tools=[tool_get_outcome],
)

# =========================================================
# GUARDIAN COORDINATOR
# Orchestrates all 5 sub-agents using Google ADK.
# =========================================================

guardian_coordinator = Agent(
    name="GuardianCoordinator",
    description="Root orchestrator managing multi-agent failure investigation and recovery.",
    instruction=(
        "You are the Guardian Coordinator. You orchestrate the Prediction, Prevention, "
        "Investigation, Recovery, and Learning agents into an end-to-end evidence-grounded "
        "failure diagnosis and safe recovery workflow for manufacturing robotics."
    ),
    sub_agents=[
        prediction_agent,
        prevention_agent,
        investigation_agent,
        recovery_agent,
        learning_agent,
    ],
)
