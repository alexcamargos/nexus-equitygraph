"""Sentiment Agent for analyzing market news and sentiment."""

import json
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import ValidationError

from nexus_equitygraph.agents.base import BaseAgent
from nexus_equitygraph.core.prompt_manager import get_prompt_manager
from nexus_equitygraph.domain.state import AgentAnalysis, FinancialMetric, MarketAgentState
from nexus_equitygraph.tools.news_tools import fetch_news_articles


# pylint: disable=too-few-public-methods
class SentimentAgent(BaseAgent):
    """Agent that analyzes market sentiment based on news."""

    def _fetch_news(self) -> str:
        """Fetches market news.

        Returns:
            str: Market news string.
        """

        # Invokes News Tool
        query = f"{self.ticker} investidor mercado financeiro"
        news_data = fetch_news_articles.invoke({"query": query})

        return news_data

    def _prepare_llm_context(self, news_data: str) -> str:
        """Formats the context message for the LLM.

        Args:
            news_data (str): Market news data.

        Returns:
            str: Formatted context message.
        """

        return f"Analise o sentimento para {self.ticker} com base nestas notícias recentes:\n\n{news_data}"

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

            # Get sources from data if available.
            sources = data.get("sources")
            if not sources:
                sources = ["DuckDuckGo Search"]
            elif isinstance(sources, str):
                sources = [sources]

            return AgentAnalysis(
                agent_name="Sonar",
                ticker=self.ticker,
                summary=summary,
                details=details,
                metrics=metrics_objs,
                sources=sources,
                timestamp=datetime.now().isoformat(),
            )

        except (json.JSONDecodeError, AttributeError, TypeError, ValidationError) as error:
            return AgentAnalysis(
                agent_name="Sonar",
                ticker=self.ticker,
                summary="Erro na geração estruturada. Verifique logs.",
                details=f"O LLM não retornou JSON válido.\nConteúdo Bruto:\n{content}\nErro: {error}",
                metrics=[],
                sources=["Error"],
                timestamp=datetime.now().isoformat(),
            )

    def analyze(self) -> dict:
        """Orchestrates the sentiment analysis process.

        Returns:
            dict: The analysis result containing analyses and metadata.
        """

        # 1. Fetch Data
        news_data = self._fetch_news()

        # 2. Prepare Context
        context_msg = self._prepare_llm_context(news_data)

        # 3. LLM Analysis
        system_prompt = self.prompt_manager.get('sentiment.agent.system_message')

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_msg),
        ]

        content = self._execute_llm_analysis(messages)

        # 4. Parse and Structure Result
        analysis = self._parse_llm_response(content)

        return {"analyses": [analysis]}


def sentiment_node(state: MarketAgentState):
    """Sentiment agent node function.

    Args:
        state (MarketAgentState): The market agent state.

    Returns:
        dict: The analysis result.
    """

    prompt_handler = get_prompt_manager()
    agent = SentimentAgent(state, prompt_manager=prompt_handler)

    return agent.analyze()
