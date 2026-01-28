"""Workflow definition for Nexus EquityGraph."""

from functools import partial
from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph
from loguru import logger

from nexus_equitygraph.agents import (
    fundamentalist_node,
    quantitative_node,
    reviewer_node,
    risk_manager_node,
    sentiment_node,
    supervisor_node,
)
from nexus_equitygraph.domain.state import MarketAgentState

# Define specialist agents dynamically
SPECIALIST_NODES = {
    "fundamentalist": fundamentalist_node,
    "quantitative": quantitative_node,
    "risk_manager": risk_manager_node,
    "sentiment": sentiment_node,
}


def entry_node(state: MarketAgentState) -> Dict[str, Any]:
    """Initialization node. Ensures iteration starts at 1.

    Args:
        state: Current MarketAgentState.

    Returns:
        Updated state with iteration initialized.
    """

    current_iter = state.iteration

    return {"iteration": 1 if not current_iter else current_iter}


def gated_reviewer_node(state: MarketAgentState, specialist_count: int) -> Dict[str, Any]:
    """Wrapper for Reviewer Node with Barrier Logic.

    Only runs review if all specialists have submitted analyses for the current iteration.

    Args:
        state: Current MarketAgentState.
        specialist_count: Number of specialist nodes expected.

    Returns:
        Either empty dict (to continue waiting) or the result of reviewer_node.
    """

    current_iter = state.iteration
    analyses = state.analyses

    # Dynamic barrier based on registered specialists
    expected_count = specialist_count * current_iter

    current_count = len(analyses)

    logger.info(
        f"Synchronizing specialists: {current_count}/{expected_count} analyses ready. (Iteration {current_iter})"
    )

    if current_count < expected_count:
        # Not all ready. Return empty to continue graph (but don't change feedback)
        logger.info("Waiting for other specialists...")
        return {}

    # All arrived: Execute real review
    logger.info("All analyses received. Starting consolidated review.")

    return reviewer_node(state)


def loop_update(state: MarketAgentState) -> Dict[str, Any]:
    """Updates iteration counter before looping back.

    Args:
        state: Current MarketAgentState.

    Returns:
        Updated state with incremented iteration.
    """

    return {"iteration": state.iteration + 1}


def router(state: MarketAgentState, specialist_count: int) -> Literal["supervisor_final", "loop_update", "__end__"]:
    """Routing logic after Reviewer.

    Args:
        state: Current MarketAgentState.
        specialist_count: Number of specialist nodes expected.

    Returns:
        Next node name based on review feedback and iteration.
    """

    current_iter = state.iteration
    analyses = state.analyses
    feedback = state.feedback

    # 1. Check Barrier
    if len(analyses) < specialist_count * current_iter:
        return "__end__"  # Ends this parallel branch

    # 2. Check if Reviewer ran and generated feedback
    MAX_ITER = 3
    if feedback and (feedback.approved or current_iter >= MAX_ITER):
        return "supervisor_final"

    if feedback and not feedback.approved:
        return "loop_update"

    # If feedback doesn't exist or gate blocked
    return "__end__"


def create_workflow(specialists: Dict[str, Any] = SPECIALIST_NODES) -> Any:
    """Creates and compiles the state graph workflow.

    Args:
        specialists: Dictionary of {node_name: node_function} for parallel execution.
                     Defaults to the global SPECIALIST_NODES.

    Returns:
        Compiled state graph workflow.
    """

    workflow = StateGraph(MarketAgentState)

    # 1. Configure Dynamic Functions with Partials
    # We explicitly bind the current number of specialists to the barrier logic
    # This prevents bugs if the 'specialists' argument differs from the global variable
    num_specialists = len(specialists)

    gated_reviewer_configured = partial(gated_reviewer_node, specialist_count=num_specialists)
    router_configured = partial(router, specialist_count=num_specialists)

    # IMPORTANT: LangGraph requires the function name to be cleaner for visualization usually,
    # but partials work fine for logic.

    # 2. Add Fixed Nodes
    workflow.add_node("setup", entry_node)
    workflow.add_node("reviewer", gated_reviewer_configured)
    workflow.add_node("supervisor_final", supervisor_node)
    workflow.add_node("loop_update", loop_update)

    # 3. Add Fixed Edges
    workflow.add_edge(START, "setup")
    workflow.add_edge("loop_update", "setup")
    workflow.add_edge("supervisor_final", END)

    # 4. Add Specialist Nodes & Wiring (Single Loop)
    for specialist_name, processing_node in specialists.items():
        workflow.add_node(specialist_name, processing_node)
        workflow.add_edge("setup", specialist_name)  # Fan-Out: from setup to all specialists.
        workflow.add_edge(specialist_name, "reviewer")  # Fan-In: from all specialists to reviewer.

    # 5. Conditional Logic at Reviewer
    workflow.add_conditional_edges(
        "reviewer",
        router_configured,
        {"__end__": END, "supervisor_final": "supervisor_final", "loop_update": "loop_update"},
    )

    return workflow.compile()
