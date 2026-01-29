# Nexus Equity Graph

[![LinkedIn](https://img.shields.io/badge/%40alexcamargos-230A66C2?style=social&logo=LinkedIn&label=LinkedIn&color=white)](https://www.linkedin.com/in/alexcamargos)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)

> **Orquestração Multi-Agente Autônoma para Análise de Equity Research (B3).**

O **Nexus Equity Graph** é um sistema avançado de inteligência artificial que revoluciona a análise de investimentos. Utilizando a arquitetura **LangGraph**, ele coordena uma equipe de **agentes autônomos especializados** que colaboram para extrair, processar, analisar e sintetizar dados financeiros complexos em tempo real.

Diferente de chatbots convencionais, este projeto implementa um **Grafo de Estado Cíclico** com capacidades de auto-correção, ETL em tempo real da CVM e validação rigorosa de dados.

## Funcionalidades Principais

- **🤖 Arquitetura Multi-Agente (The Squad)**: 6 agentes especializados (Fundamentalista, Quant, Sentimento, Risco, Revisor, Supervisor) trabalhando em conjunto.
- **📊 Integração CVM em Tempo Real**: Conexão direta com o portal de Dados Abertos da CVM para extração de DRE, BPP e DFC.
- **🧠 LLM Agnostic**: Flexibilidade total para rodar com modelos locais (Ollama/Llama3, DeepSeek) ou em nuvem (Groq/Llama-70b, OpenAI, Gemini).
- **🛡️ Governance & QA Loop**: Agente "Revisor" dedicado a validar fatos e fontes, prevenindo alucinações.
- **🔍 Observabilidade Total**: Integração nativa com **[LangSmith](https://smith.langchain.com/)** para rastreabilidade completa (trace), debug e auditoria de cada passo dos agentes.
- **⚡ Alta Performance**: Gerenciamento de dependências com `uv` e execução otimizada.

## O Esquadrão (Agentes)

O sistema opera através de "personas" com responsabilidades distintas. Para detalhes completos sobre a personalidade e missão de cada agente, veja [PERSONAS.md](PERSONAS.md).

| Agente | Codinome | Função Principal |
| :--- | :--- | :--- |
| **Fundamentalista** | `Graham` | **Valuation & Contabilidade**: Extrai e analisa balanços (ITR/DFP) e calcula indicadores fundamentais (ROE, Margens). |
| **Quantitativo** | `Vector` | **Análise Técnica**: Analisa price action, volatilidade, médias móveis e indicadores técnicos (RSI, MACD). |
| **Sentimento** | `Sonar` | **Market Mood**: Monitora notícias e tendências de mercado para identificar o sentimento dos investidores. |
| **Risco** | `Sentry` | **Devil's Advocate**: Estressa a tese de investimento com análises de riscos regulatórios e macroeconômicos. |
| **Revisor** | `Argus` | **Quality Assurance**: "Gatekeeper" que valida a consistência lógica e factual das análises antes da aprovação. |
| **Supervisor** | `Chairman` | **Tomada de Decisão**: Sintetiza todas as análises aprovadas e redige a tese final de investimento. |

## Instalação e Configuração

### Pré-requisitos

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Recomendado) ou pip

### Instalação

Clone o repositório e instale as dependências:

```bash
# Opção 1: Via uv (Recomendado - Mais rápido)
uv sync

# Opção 2: Via pip
pip install -e .
```

### Configuração (.env)

Crie um arquivo `.env` na raiz do projeto baseando-se no `.env.example`. As configurações principais são:

```ini
# Escolha do Provedor de IA (ollama ou groq)
AI_PROVIDER=ollama

# Configuração Ollama (Local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.1

# Configuração Groq (Cloud - Opcional)
AI_API_KEY=sua_chave_aqui
GROQ_DEFAULT_MODEL=llama-3.1-70b-versatile
```

## Como Usar

Para iniciar uma análise completa de uma empresa, execute o comando abaixo passando o **ticker** da ação:

```bash
uv run main.py WEGE3
```

### O que acontece em seguida?

1. O sistema inicializa o grafo de agentes.
2. Os agentes (Graham, Vector, Sonar, Sentry) iniciam suas pesquisas paralelamente.
3. O **Argus (Revisor)** valida cada relatório gerado.
4. O **Chairman (Supervisor)** consolida tudo em um relatório final de investimento.
5. O resultado é salvo na pasta `reports/` em formato Markdown (ex: `reports/WEGE3_20231027.md`).

### Exemplo de Execução

**Comando:**

```bash
python main.py WEGE3
```

**Snippet do Relatório Gerado (Exemplo):**
> **Tese de Investimento**
>
> **Recomendação: COMPRA**
> Justificativa: A WEG S.A. apresenta fundamentos sólidos, com crescimento acelerado de receita (CAGR de 31,5% em 2 anos), margens operacionais resilientes (EBIT de ~20%) e posição financeira robusta (dívida líquida negativa).
>
> **Fundamentos (Graham):**
>
> - Receita: R$ 30,6 bi (9 meses de 2025).
> - Margem Líquida: 16,5%.
> - ROE: 29,2% (superior à média do setor).
>
> **Sentimento de Mercado (Sonar):**
>
> - Positivo: Itaú BBA revisou projeções para alta (preço-alvo de R$ 50).
> - Técnico (Vector): Tendência de alta, mas RSI sugere cautela no curto prazo.

## Stack Tecnológico

- **Orquestração**: LangChain / LangGraph
- **Observabilidade**: LangSmith (Auditoria e Tracing)
- **Linguagem**: Python 3.11+
- **Gerenciamento de Pacotes**: uv
- **Dados Financeiros**: CVM (Dados Abertos), Yahoo Finance
- **Busca Web**: DuckDuckGo Search

## DISCLAIMER & NOTA LEGAL

> Este software é um projeto de engenharia de dados e inteligência artificial para fins educacionais e de portfólio. As informações aqui contidas têm caráter meramente informativo e analítico, baseadas em dados públicos.
>
> **As análises geradas NÃO constituem recomendação de investimento, oferta ou solicitação de compra ou venda de valores mobiliários.**
>
> O autor não se responsabiliza por decisões financeiras tomadas com base neste software. Rentabilidade passada não representa garantia de rentabilidade futura.
>
> **CONSULTE UM PROFISSIONAL CERTIFICADO (CNPI/CFA) ANTES DE TOMAR DECISÕES.**

## Licença

Este projeto está licenciado sob a licença [MIT](LICENSE).
