"""Risk Manager Agent for analyzing macro and micro risks."""

import json
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from nexus_equitygraph.agents.base import BaseAgent
from nexus_equitygraph.core.prompt_manager import get_prompt_manager
from nexus_equitygraph.domain.state import AgentAnalysis, FinancialMetric, MarketAgentState


# pylint: disable=too-few-public-methods
class RiskManagerAgent(BaseAgent):
    """Agent that analyzes macro and micro factors that may threaten the asset."""

    def _prepare_llm_context(self) -> str:
        """Formats the context message for the LLM.

        Returns:
            str: Formatted context message.
        """

        return f"Avalie os riscos associados ao investimento em {self.ticker}."

    def _parse_llm_response(self, content: str) -> AgentAnalysis:
        """Parses the LLM response content into structured AgentAnalysis.

        Args:
            content (str): LLM response content.

        Returns:
            AgentAnalysis: Structured analysis result.
        """

        try:
            data = self._safe_parse_json(content)

            summary = data.get("summary", "Resumo indisponível.")
            details = data.get("details", "")
            if not details:
                details = str(data)

            metrics_objs = []
            for metric in data.get("metrics", []):
                if isinstance(metric, str):
                    metrics_objs.append(FinancialMetric(name=metric, value=0, unit="", period="", description=""))
                else:
                    metrics_objs.append(
                        FinancialMetric(
                            name=metric.get("name", "N/A"),
                            value=metric.get("value", 0),
                            unit=metric.get("unit", ""),
                            period=metric.get("period", ""),
                            description=metric.get("description", ""),
                        )
                    )

            sources = ["Model Knowledge Base"]

            return AgentAnalysis(
                agent_name="Sentry",
                ticker=self.ticker,
                summary=summary,
                details=details,
                metrics=metrics_objs,
                sources=sources,
                timestamp=datetime.now().isoformat(),
            )

        except (json.JSONDecodeError, AttributeError, TypeError, ValidationError) as error:
            return AgentAnalysis(
                agent_name="Sentry",
                ticker=self.ticker,
                summary="Erro na geração estruturada. Verifique logs.",
                details=f"O LLM não retornou JSON válido.\nConteúdo Bruto:\n{content}\nErro: {error}",
                metrics=[],
                sources=["Error"],
                timestamp=datetime.now().isoformat(),
            )

    def analyze(self) -> dict:
        """Orchestrates the risk analysis process.

        Returns:
            dict: The analysis result containing analyses and metadata.
        """

        # 1. Prepare Context
        context_msg = self._prepare_llm_context()

        # 2. LLM Analysis
        system_prompt = self.prompt_manager.get('risk_manager.agent.system_message')

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_msg),
        ]

        content = self._execute_llm_analysis(messages)

        # 3. Parse and Structure Result
        analysis = self._parse_llm_response(content)

        return {"analyses": [analysis]}


def risk_manager_node(state: MarketAgentState):
    """Risk Manager agent node function.

    Args:
        state (MarketAgentState): The market agent state.

    Returns:
        dict: The analysis result.
    """

    prompt_handler = get_prompt_manager()
    agent = RiskManagerAgent(state, prompt_manager=prompt_handler)

    return agent.analyze()
