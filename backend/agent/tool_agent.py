"""
tool_agent.py — LangChain agent with tools using Groq (free, fast).

Handles:
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


AGENT_SYSTEM = """You are PlacementIQ, a placement data analyst.
You have access to tools for calculations and corpus boundary checks.
Use the calculator tool for any arithmetic (ratios, differences, percentages).
Use the corpus_boundary_check tool when a query is outside the dataset scope.
Always show your calculation steps clearly.
"""

_agent_prompt = ChatPromptTemplate.from_messages([
    ("system", AGENT_SYSTEM),
    ("human",  "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])


class ToolAgent:
    """LangChain agent with arithmetic + corpus tools powered by Groq."""

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
        Context is injected into the query if provided.
        """
        full_input = query
        if context:
            full_input = f"Context from placement data:\n{context}\n\nQuery: {query}"
        try:
            result = self._executor.invoke({"input": full_input})
            return result.get("output", "No answer generated.")
        except Exception as e:
            logger.error(f"ToolAgent error: {e}")
            return f"Tool agent encountered an error: {e}"