"""Main entry point for Nexus EquityGraph CLI."""

import argparse
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from loguru import logger

# Ensure src is in pythonpath to allow running directly without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from nexus_equitygraph import NexusGraph
from nexus_equitygraph.core.configs import DirectoryConfigs
from nexus_equitygraph.core.formatters import format_final_report

# Load env vars before importing other modules
load_dotenv()


def parse_arguments() -> argparse.Namespace:
    """Parses command line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    
    parser = argparse.ArgumentParser(description="Nexus EquityGraph - AI Investment Analyst")
    parser.add_argument("ticker", type=str, help="The stock ticker symbol (e.g., WEGE3)")
    
    return parser.parse_args()


def run_cli() -> None:
    """Runs the CLI for Nexus EquityGraph."""
    
    logger.info("Initializing Nexus EquityGraph CLI")

    try:
        args = parse_arguments()
        ticker = args.ticker.strip().upper()
    except SystemExit:
        # Argparse handles exit on error or help, but if called programmatically we might handle it
        return

    print(f"Nexus EquityGraph: Iniciando análise para {ticker}...")

    try:
        # Initialize and run graph
        runner = NexusGraph()
        final_state = runner.run(ticker)

        print("\n" + "=" * 40)
        print("RELATÓRIO FINAL DE INVESTIMENTO")
        print("=" * 40)

        final_report = final_state.get("final_report", "Nenhum relatório gerado.")
        print(final_report)

        if ticker and final_report:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{ticker}_{timestamp}.md"

            output_dir = os.path.join(os.getcwd(), "reports")
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)

            metadata = final_state.get("metadata", {})
            configs = DirectoryConfigs()
            full_content = format_final_report(ticker, final_report, metadata, configs.REPORT_TEMPLATE_FILE)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_content)

            print(f"\nRelatório salvo em: {filepath}")
            logger.info(f"Report saved to {filepath}")

    except Exception as e:
        logger.exception("Error during execution")
        print(f"Erro durante execução: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_cli()
