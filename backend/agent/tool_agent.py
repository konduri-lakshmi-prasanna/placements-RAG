"""
tool_agent.py — LangChain agent with tools using Groq (free, fast).

Handles:
  - Web search for external questions (CEO names, stock prices, company news)
  - Student eligibility check via MySQL database
  - Package-to-CGPA ratio computation
  - Package increase calculation
  - Out-of-corpus boundary explanations
  - Any query needing arithmetic over retrieved data
"""

from __future__ import annotations

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from loguru import logger

from agent.tools import ALL_TOOLS
from config import GROQ_API_KEY, LLM_MODEL


AGENT_SYSTEM = """You are PlacementIQ, a smart placement intelligence assistant.

You have access to these tools — always use the right one:

1. calculator
   → Use for any arithmetic: ratios, percentages, package differences, comparisons.
   → Example: "What is the package-to-CGPA ratio for TCS?" → use calculator

2. corpus_boundary_check
   → Use when a query is completely outside the placement dataset scope.
   → Example: "Which career is best for me?" → use corpus_boundary_check

3. package_cgpa_ratio
   → Use specifically to compute the package divided by CGPA ratio.

4. web_search
   → Use for ANY question about real-world, live, or external information that
     is NOT inside the placement PDF dataset.
   → Examples of when to use web_search:
       - "Who is the CEO of TCS?" → web_search("CEO of TCS")
       - "What is Infosys stock price?" → web_search("Infosys stock price today")
       - "Where is Google headquarters?" → web_search("Google headquarters location")
       - "When was Amazon founded?" → web_search("When was Amazon founded")
       - "What is TCS's work from home policy?" → web_search("TCS work from home policy 2024")
       - "How many employees does Wipro have?" → web_search("Wipro number of employees")
   → ALWAYS use web_search for CEO, stock price, news, headquarters, founding year,
     employee count, remote work policy, recent events — do NOT guess from memory.

5. mysql_placement_db
   → Use for student-specific eligibility checks and college placement statistics
     from the college's own database records.
   → Examples of when to use mysql_placement_db:
       - "Is roll no 21A91A0501 eligible for TCS?" → mysql_placement_db
       - "Am I eligible for Amazon with CGPA 7.5?" → mysql_placement_db
       - "How many students were placed in 2024?" → mysql_placement_db
       - "Which companies visited our campus?" → mysql_placement_db
   → This tool queries the live college database — use it for student-specific queries.

Decision rules:
- Question about a real person's role/title → web_search (not memory)
- Question about live data (stock, price, news) → web_search
- Question with a roll number → mysql_placement_db
- Question starting with "Am I eligible" or "Can I apply" → mysql_placement_db
- Question about campus statistics or placement count → mysql_placement_db
- Math calculation needed → calculator
- Query completely outside placement scope → corpus_boundary_check

Always show your reasoning clearly. If a tool returns no result, say so honestly.
"""

_agent_prompt = ChatPromptTemplate.from_messages([
    ("system", AGENT_SYSTEM),
    ("human",  "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])


class ToolAgent:
    """LangChain agent with web search, MySQL, arithmetic + corpus tools powered by Groq."""

    def __init__(self) -> None:
        llm = ChatGroq(
            model=LLM_MODEL,
            api_key=GROQ_API_KEY,
            max_tokens=512,
            temperature=0.0,
        )
        agent = create_tool_calling_agent(llm, ALL_TOOLS, _agent_prompt)
        self._executor = AgentExecutor(
            agent=agent,
            tools=ALL_TOOLS,
            verbose=False,
            max_iterations=5,
            handle_parsing_errors=True,
        )

    def run(self, query: str, context: str = "") -> str:
        """
        Run the agent on a query.
        Context from PDF corpus is injected if available (may be empty for web queries).
        """
        full_input = query
        if context and context.strip():
            full_input = (
                f"Context from placement PDF dataset (may or may not be relevant):\n"
                f"{context}\n\n"
                f"User Question: {query}"
            )
        try:
            result = self._executor.invoke({"input": full_input})
            return result.get("output", "No answer generated.")
        except Exception as e:
            logger.error(f"ToolAgent error: {e}")
            return f"Tool agent encountered an error: {e}"