"""Core execution logic for Nexus EquityGraph."""

from typing import Any, Dict

from loguru import logger

from nexus_equitygraph.workflow import create_workflow


# pylint: disable=too-few-public-methods
class NexusGraph:
    """Encapsulates the execution of the Nexus EquityGraph workflow."""

    def __init__(self) -> None:
        """Initialize the graph runner."""

        self.app = create_workflow()

    def run(self, ticker: str, iteration: int = 1) -> Dict[str, Any]:
        """Runs the analysis workflow for a given ticker.

        Args:
            ticker: The stock ticker symbol (e.g., WEGE3).
            iteration: Initial iteration counter (default: 1).

        Returns:
            Dict containing the final state of the workflow.
        """

        logger.info(f"Starting NexusGraph execution for {ticker}")

        inputs = {"ticker": ticker.upper(), "iteration": iteration, "analyses": [], "messages": []}

        try:
            # Execute the workflow
            # Using invoke for synchronous execution as per current architecture.
            final_state = self.app.invoke(inputs)

            return final_state

        except Exception:
            logger.exception(f"Error executing graph for {ticker}")
            raise
