"""
tools.py — Tool definitions for the agent layer.

These tools are called by the ToolAgent when the RAG corpus
cannot answer a query (stock prices, campus dates, general comparisons).
Tools are defined as LangChain StructuredTool objects.
"""

from __future__ import annotations

import math

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field


# ── Calculator tool ───────────────────────────────────────────────────────

class CalcInput(BaseModel):
    expression: str = Field(description="A Python math expression to evaluate, e.g. '42.9 - 36.0'")


def calculate(expression: str) -> str:
    """Safely evaluate a math expression."""
    try:
        # Allow only safe builtins
        allowed = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        allowed.update({"abs": abs, "round": round, "max": max, "min": min})
        result = eval(expression, {"__builtins__": {}}, allowed)
        return f"{result}"
    except Exception as e:
        return f"Error evaluating expression: {e}"


calculator_tool = StructuredTool.from_function(
    func=calculate,
    name="calculator",
    description=(
        "Evaluate math expressions. "
        "Use for computed queries like package-to-CGPA ratio, "
        "absolute package increase, percentage change, etc."
    ),
    args_schema=CalcInput,
)


# ── Corpus boundary tool ──────────────────────────────────────────────────

class CorpusCheckInput(BaseModel):
    query: str = Field(description="The user query to check against corpus boundaries")


def corpus_boundary_check(query: str) -> str:
    """
    Returns a clear message about what is and isn't in the corpus.
    Called when the router detects an out-of-corpus query.
    """
    corpus_scope = (
        "The placement intelligence corpus covers: "
        "19 companies (TCS, Infosys, Amazon, Google, Microsoft, Deloitte, Accenture, "
        "Flipkart, Wipro, Cognizant, Capgemini, IBM, Adobe, Oracle, SAP, HCL, "
        "Tech Mahindra, Qualcomm, Intel, Samsung R&D). "
        "Data includes: eligibility criteria, packages, interview rounds, "
        "hiring distribution by role, package trends 2021–2024, "
        "and overall placement statistics. "
        "NOT included: campus visit schedules, stock prices, work-mode policies, "
        "institution-specific placement counts, or subjective career advice."
    )
    return corpus_scope


corpus_tool = StructuredTool.from_function(
    func=corpus_boundary_check,
    name="corpus_boundary_check",
    description="Check what information is and isn't available in the placement corpus.",
    args_schema=CorpusCheckInput,
)


# ── Package ratio tool ────────────────────────────────────────────────────

class RatioInput(BaseModel):
    package: float = Field(description="Package in LPA")
    cgpa:    float = Field(description="CGPA cutoff")


def package_to_cgpa_ratio(package: float, cgpa: float) -> str:
    """Calculate the package-to-CGPA ratio."""
    if cgpa == 0:
        return "CGPA cannot be 0"
    ratio = round(package / cgpa, 2)
    return f"Package/CGPA ratio = {package} / {cgpa} = {ratio}"


ratio_tool = StructuredTool.from_function(
    func=package_to_cgpa_ratio,
    name="package_cgpa_ratio",
    description="Calculate the package-to-CGPA ratio for a company.",
    args_schema=RatioInput,
)


# ── Tool registry ─────────────────────────────────────────────────────────

ALL_TOOLS = [calculator_tool, corpus_tool, ratio_tool]