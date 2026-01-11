"""Main entry point for Nexus Equity Graph application."""

import os
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

# Ensure src is in pythonpath to allow running directly without installation
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# pylint: disable=import-error
from nexus_equitygraph import __version__
from nexus_equitygraph.core.providers import create_llm_provider
from nexus_equitygraph.core.settings import settings


def configure_logging():
    """Configures the logging format and level.

    Sets up loguru to display time, log level, function name, and message.
    """

    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )


def run_smoke_test():
    """Runs a connectivity test to validate LLM configuration.

    This is a smoke test to ensure that the LLM provider is correctly set up
    and can respond to a simple domain-specific prompt.
    """

    logger.info(f"Starting Nexus Equity Graph v{__version__.__version__}")
    logger.info(f"Configuration: Provider={settings.provider.upper()}")

    try:
        # 1. Initialize the LLM Provider
        llm = create_llm_provider(temperature=0.0)
        logger.info(
            f"LLM Initialized: {llm.model_name if hasattr(llm, 'model_name') else 'Unknown Model'}"
        )

        # 2. Prepare a domain-specific test prompt
        messages = [
            SystemMessage(
                content="You are a senior financial analyst. Answer concisely."
            ),
            HumanMessage(content="Define 'Free Cash Flow' in one sentence."),
        ]

        # 3. Execute Inference
        logger.info("Sending test prompt to LLM...")
        response = llm.invoke(messages)

        # 4. Display Result
        logger.success("Smoke Test Passed Successfully")
        logger.info(f"Agent Response: {response.content}")

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Smoke Test Failed: {e}")
        sys.exit(1)


def main():
    """Main entry point for the application."""

    configure_logging()
    run_smoke_test()


if __name__ == "__main__":
    main()
