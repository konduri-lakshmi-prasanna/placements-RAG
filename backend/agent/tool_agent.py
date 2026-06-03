"""
tool_agent.py — LangChain agent with multi-tool handling using Groq.

Handles:
  - Web search for external questions (CEO, stock prices, news)
  - MySQL database for student eligibility checks
  - Calculator for arithmetic
  - Corpus boundary check for out-of-scope queries
  - MULTI-TOOL: can call multiple tools in a single query
    e.g. "Is roll 21A91A0501 eligible for TCS and who is the CEO?"
         → calls mysql_tool AND web_search_tool, combines both answers
"""

from __future__ import annotations

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from loguru import logger

from agent.tools import ALL_TOOLS
from config import GROQ_API_KEY, LLM_MODEL


AGENT_SYSTEM = """You are PlacementIQ, a smart placement intelligence assistant for SVECW students.

You have access to these tools — use AS MANY AS NEEDED for a single query:

1. calculator
   → Use for any arithmetic: ratios, percentages, package differences.

2. corpus_boundary_check
   → Use when a query is completely outside the placement dataset scope.

3. package_cgpa_ratio
   → Use specifically to compute package divided by CGPA ratio.

4. web_search
   → Use for ANY real-world/live information NOT in the placement PDF:
     CEO names, stock prices, news, headquarters, founding year,
     employee count, remote work policy, recent events.
   → ALWAYS use web_search — NEVER guess from memory.

5. mysql_placement_db
   → Use for student-specific eligibility and college placement statistics:
     roll numbers, CGPA-based eligibility, campus placement records.

MULTI-TOOL INSTRUCTIONS — VERY IMPORTANT:
- If a query has MULTIPLE parts, use MULTIPLE tools — one for each part.
- DO NOT stop after the first tool. Check if other parts still need answering.
- Combine all tool results into ONE clear, structured answer.

Examples of multi-tool queries:
  "Is roll 21A91A0501 eligible for TCS and who is the CEO?"
  → Step 1: mysql_placement_db → eligibility result
  → Step 2: web_search("CEO of TCS 2024") → CEO name
  → Combine both into one answer

  "What is TCS package in our college and their stock price today?"
  → Step 1: mysql_placement_db → campus package
  → Step 2: web_search("TCS stock price today") → live price
  → Combine both

STRICT RULES:
1. NEVER guess or answer from memory — always use a tool.
2. Always show which tool gave which part of the answer.
3. If a tool returns no result, try another approach.
"""

_agent_prompt = ChatPromptTemplate.from_messages([
    ("system", AGENT_SYSTEM),
    ("human",  "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])


class ToolAgent:
    """LangChain agent that calls multiple tools in a single query."""

    def __init__(self) -> None:
        llm = ChatGroq(
            model=LLM_MODEL,
            api_key=GROQ_API_KEY,
            max_tokens=1024,
            temperature=0.0,
        )
        agent = create_tool_calling_agent(llm, ALL_TOOLS, _agent_prompt)
        self._executor = AgentExecutor(
            agent=agent,
            tools=ALL_TOOLS,
            verbose=True,
            max_iterations=8,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
        )

    def run(self, query: str, context: str = "") -> str:
        full_input = query
        if context and context.strip():
            full_input = (
                f"Context from placement PDF dataset:\n{context}\n\n"
                f"User Question: {query}\n\n"
                f"If the question has multiple parts, use multiple tools."
            )
        try:
            result     = self._executor.invoke({"input": full_input})
            answer     = result.get("output", "No answer generated.")
            steps      = result.get("intermediate_steps", [])

            if steps:
                tools_used = [step[0].tool for step in steps]
                logger.info(f"Tools used: {tools_used} for: '{query[:50]}'")
                if len(set(tools_used)) > 1:
                    answer += f"\n\n---\n🔧 Tools used: {', '.join(set(tools_used))}"

            return answer
        except Exception as e:
            logger.error(f"ToolAgent error: {e}")
            return f"Tool agent encountered an error: {e}"