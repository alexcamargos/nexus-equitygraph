# Nexus Equity Graph

[![LinkedIn](https://img.shields.io/badge/%40alexcamargos-230A66C2?style=social&logo=LinkedIn&label=LinkedIn&color=white)](https://www.linkedin.com/in/alexcamargos)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)


> Orquestração multi-agente autônoma para análise de equity research de empresas brasileiras (B3).


## Sobre o Projeto

O **Nexus Equity Graph** é um sistema de inteligência artificial projetado para automatizar o pipeline de *Equity Research* (Análise de Ações). Utilizando a arquitetura **LangGraph**, o projeto coordena uma equipe de 6 agentes autônomos especializados que atuam colaborativamente para coletar, validar, analisar e sintetizar dados financeiros complexos.

Ao contrário de "chatbots" tradicionais, este sistema implementa um **Grafo de Estado Cíclico** capaz de:
1. **ETL em Tempo Real**: Extrair e processar dados brutos do portal de Dados Abertos da CVM (Comissão de Valores Mobiliários).
2. **Flexibilidade de Modelos**: Utilizar modelos de IA rápidos e econômicos à escolha do usuário, permitindo escalar a operação com baixo custo.
3. **Auto-Correção**: Um agente "Revisor" atua como gatekeeper, rejeitando análises com alucinações ou falta de fontes.

Este projeto serve como demonstração de competências de **engenharia de dados** e **engenharia de inteligência artificial**, focando em robustez, transformação de dados não-estruturados e orquestração de fluxos complexos.



## Arquitetura de Agentes (The Squad)

O sistema opera via um grafo onde cada nó representa uma "persona" com responsabilidades e ferramentas isoladas:

| Agente | Codinome | Função & Stack Técnica |
| :--- | :--- | :--- |
| **Fundamentalista** | `Graham` | **ETL & Valuation**: Acessa a API da CVM, baixa demonstrativos (ITR/DFP), trata dados contábeis (Pandas) e calcula indicadores como ROE, Margens e Dívida Líquida. |
| **Quantitativo** | `Vector` | **Time Series Analytics**: Analisa o histórico de preços (OHLCV), calcula Volatilidade, RSI e Médias Móveis para identificar tendências técnicas. |
| **Sentimento** | `Sonar` | **NLP & News Scraping**: Monitora o fluxo de notícias recentes, filtrando ruídos de redes sociais e estruturando o "humor" do mercado. |
| **Risco** | `Sentry` | **Governance Engine**: Atua como *Devil's Advocate*, estressando a tese com fatores macroeconômicos e riscos regulatórios. |
| **Revisor** | `Argus` | **Quality Assurance Loop**: Valida logicamente os relatórios dos analistas. Se encontrar inconsistências, devolve o ticket para refação (Retry Loop). |
| **Supervisor** | `Chairman` | **Decision Making**: Consolida os inputs aprovados e redige a Tese de Investimento final (Buy/Sell/Hold). |


## Stack Tecnológico

* **Linguagem**: Python 3.11+
* **Framework de Agentes**: [LangChain](https://www.langchain.com/) / [LangGraph](https://langchain-ai.github.io/langgraph/)
* **LLM Engine**: Flexível (Local ou Nuvem)
  * **Local**: [Ollama](https://ollama.com/) (ex: Qwen3, DeepSeek-R1, Llama3).
  * **Nuvem**: Integração com provedores diversos (Google Gemini, OpenAI, Groq, etc.) à livre escolha.
* **Gerenciamento de Pacotes**: [uv](https://github.com/astral-sh/uv) (Alta performance).
* **Fontes de Dados (Data Sources)**:
  * **CVM (Dados Abertos)**: Balanços Oficiais (DRE, BPP, DFC).
  * **B3 / Yahoo Finance**: Dados de Mercado (Delay 15min).
  * **Web Search**: DuckDuckGo API.


## Autor

**Alexsander Lopes Camargos**

Engenheiro de dados e inteligência artificial focado em soluções de alta performance para o mercado financeiro.
Este projeto reflete meu interesse em arquiteturas de agentes autônomos e estruturação de dados complexos.

Fique à vontade para entrar em contato para discussões técnicas, sugestões ou oportunidades:

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/alexcamargos/)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:alcamargos@vivaldi.net)


## Licença

Este projeto está sob a licença [MIT](LICENSE).
