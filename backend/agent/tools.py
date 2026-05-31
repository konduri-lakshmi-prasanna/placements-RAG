"""
tools.py — Tool definitions for the agent layer.

These tools are called by the ToolAgent when the RAG corpus
cannot answer a query (stock prices, campus dates, general comparisons).
Tools are defined as LangChain StructuredTool objects.

Tools available:
  calculator_tool       — safe math expression evaluator
  corpus_tool           — explains what is/isn't in the corpus
  ratio_tool            — package-to-CGPA ratio
  web_search_tool       — live web search via SerpAPI (falls back to DuckDuckGo)
  mysql_tool            — queries structured placement MySQL database
"""

from __future__ import annotations

import math
import os

import requests
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

# MySQL connector is optional — only needed if DB is configured
try:
    import mysql.connector
    _MYSQL_AVAILABLE = True
except ImportError:
    _MYSQL_AVAILABLE = False


# ── Calculator tool ───────────────────────────────────────────────────────

class CalcInput(BaseModel):
    expression: str = Field(description="A Python math expression to evaluate, e.g. '42.9 - 36.0'")


def calculate(expression: str) -> str:
    """Safely evaluate a math expression."""
    try:
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


# ── Web search tool ───────────────────────────────────────────────────────
#
# Answers questions that are completely outside the corpus:
#   "Who is the CEO of TCS?"
#   "What is TCS's current stock price?"
#   "What is Amazon's work-from-home policy?"
#
# Setup — add to your .env file:
#   SERPAPI_KEY=your_key_here   ← free at https://serpapi.com (100/month)
#
# If SERPAPI_KEY is not set, falls back to DuckDuckGo (no key needed).
#
# Add to requirements.txt:
#   requests

class WebSearchInput(BaseModel):
    query: str = Field(description="The search query to look up on the web")


def web_search(query: str) -> str:
    """
    Search the live web for information not available in the placement corpus.
    Use this for public facts: CEO names, stock prices, company news, etc.
    """
    serpapi_key = os.getenv("SERPAPI_KEY", "")
    if serpapi_key:
        return _serpapi_search(query, serpapi_key)
    return _duckduckgo_search(query)


def _serpapi_search(query: str, api_key: str) -> str:
    """Google search results via SerpAPI."""
    try:
        response = requests.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": api_key, "num": 3, "hl": "en"},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()

        snippets = []

        # Answer box = highest quality (direct answer)
        if "answer_box" in data:
            box = data["answer_box"]
            answer = box.get("answer") or box.get("snippet") or box.get("result")
            if answer:
                snippets.append(f"Direct answer: {answer}")

        # Organic results as fallback
        for result in data.get("organic_results", [])[:3]:
            snippet = result.get("snippet", "")
            title   = result.get("title", "")
            if snippet:
                snippets.append(f"{title}: {snippet}")

        return "\n\n".join(snippets) if snippets else "No results found."

    except requests.exceptions.Timeout:
        return "Web search timed out. Please try again."
    except Exception as e:
        return f"Web search error: {e}"


def _duckduckgo_search(query: str) -> str:
    """DuckDuckGo Instant Answer API — no key needed, factual questions only."""
    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("AbstractText"):
            return data["AbstractText"]
        if data.get("Answer"):
            return data["Answer"]

        topics = data.get("RelatedTopics", [])
        snippets = [
            t["Text"] for t in topics[:3]
            if isinstance(t, dict) and t.get("Text")
        ]
        return "\n\n".join(snippets) if snippets else "No results found."

    except Exception as e:
        return f"DuckDuckGo search error: {e}"


web_search_tool = StructuredTool.from_function(
    func=web_search,
    name="web_search",
    description=(
        "Search the live web for information NOT available in the placement corpus. "
        "Use this for: CEO names, current stock prices, company news, general company info, "
        "anything outside the 19-company placement dataset."
    ),
    args_schema=WebSearchInput,
)


# ── MySQL placement database tool ─────────────────────────────────────────
#
# Queries your structured college placement database for student-specific
# and college-specific data that isn't in the PDF corpus.
#
# Setup — add to your .env file:
#   DB_HOST=localhost
#   DB_USER=root
#   DB_PASSWORD=your_password
#   DB_NAME=placements_db
#
# Expected tables (your sir's MySQL task):
#   students(id, name, roll_no, branch, cgpa, backlogs, year)
#   companies(id, name, min_cgpa, allowed_branches, package_lpa, bond_years)
#   placements(id, student_id, company_id, year, package_lpa, status)
#
# Add to requirements.txt:
#   mysql-connector-python

class MySQLInput(BaseModel):
    query: str = Field(
        description=(
            "Natural language question about students or placements. "
            "Examples: 'Is John eligible for TCS?', "
            "'How many students were placed in 2024?', "
            "'Which companies visited campus?'"
        )
    )


def query_placement_db(query: str) -> str:
    """
    Query the college placement MySQL database for student eligibility,
    placement statistics, and company visit records.
    """
    if not _MYSQL_AVAILABLE:
        return (
            "MySQL tool is not available. "
            "Run: pip install mysql-connector-python "
            "and configure DB credentials in your .env file."
        )

    db_host = os.getenv("DB_HOST", "")
    if not db_host:
        return (
            "MySQL database is not configured. "
            "Add DB_HOST, DB_USER, DB_PASSWORD, DB_NAME to your .env file."
        )

    query_lower = query.lower()

    try:
        conn = mysql.connector.connect(
            host=db_host,
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "placements_db"),
            connection_timeout=5,
        )
        cursor = conn.cursor(dictionary=True)
        result = _route_db_query(cursor, query_lower)
        cursor.close()
        conn.close()
        return result if result else "No matching records found in the placement database."

    except mysql.connector.Error as e:
        return f"Database connection error: {e}"
    except Exception as e:
        return f"Unexpected error querying database: {e}"


def _route_db_query(cursor, query_lower: str) -> str:
    """Routes the natural-language question to the correct SQL query."""

    company_name = _extract_company(query_lower)

    # --- Eligibility check ---
    # "Is [student] eligible for TCS?" / "eligibility for Infosys"
    if "eligible" in query_lower and company_name:
        cursor.execute(
            """
            SELECT name, min_cgpa, allowed_branches, package_lpa
            FROM companies
            WHERE LOWER(name) = %s
            """,
            (company_name,),
        )
        rows = cursor.fetchall()
        if rows:
            r = rows[0]
            return (
                f"Eligibility criteria for {r['name']}:\n"
                f"  Minimum CGPA     : {r['min_cgpa']}\n"
                f"  Allowed branches : {r['allowed_branches']}\n"
                f"  Package offered  : {r['package_lpa']} LPA"
            )

    # --- Company details ---
    # "What is the package for Wipro?" / "Infosys criteria"
    if company_name and any(w in query_lower for w in ["package", "salary", "ctc", "criteria", "cutoff"]):
        cursor.execute(
            """
            SELECT name, min_cgpa, allowed_branches, package_lpa, bond_years
            FROM companies
            WHERE LOWER(name) = %s
            """,
            (company_name,),
        )
        rows = cursor.fetchall()
        if rows:
            r = rows[0]
            bond = f"\n  Bond             : {r['bond_years']} years" if r.get("bond_years") else ""
            return (
                f"Details for {r['name']}:\n"
                f"  Min CGPA         : {r['min_cgpa']}\n"
                f"  Allowed branches : {r['allowed_branches']}\n"
                f"  Package          : {r['package_lpa']} LPA"
                f"{bond}"
            )

    # --- Placement statistics ---
    # "How many students were placed?" / "placement record 2024"
    if any(w in query_lower for w in ["how many", "placed", "statistics", "record", "stats"]):
        cursor.execute(
            """
            SELECT
                p.year,
                COUNT(DISTINCT p.student_id)  AS placed_count,
                ROUND(AVG(p.package_lpa), 2)  AS avg_package,
                MAX(p.package_lpa)            AS highest_package
            FROM placements p
            WHERE p.status = 'placed'
            GROUP BY p.year
            ORDER BY p.year DESC
            LIMIT 3
            """
        )
        rows = cursor.fetchall()
        if rows:
            lines = ["Placement statistics (last 3 years):"]
            for r in rows:
                lines.append(
                    f"  {r['year']}: {r['placed_count']} students | "
                    f"Avg: {r['avg_package']} LPA | "
                    f"Highest: {r['highest_package']} LPA"
                )
            return "\n".join(lines)

    # --- Companies that visited campus ---
    # "Which companies came to campus?" / "what companies visited"
    if any(w in query_lower for w in ["which companies", "what companies", "companies visited", "companies came"]):
        cursor.execute(
            """
            SELECT DISTINCT c.name, c.package_lpa
            FROM companies c
            JOIN placements p ON c.id = p.company_id
            ORDER BY c.package_lpa DESC
            """
        )
        rows = cursor.fetchall()
        if rows:
            names = [f"{r['name']} ({r['package_lpa']} LPA)" for r in rows]
            return "Companies that visited campus:\n  " + "\n  ".join(names)

    return ""


def _extract_company(query_lower: str) -> str:
    """Extracts a known company name from the query string."""
    known = [
        "tcs", "infosys", "wipro", "accenture", "cognizant",
        "amazon", "google", "microsoft", "capgemini", "ibm",
        "adobe", "oracle", "sap", "hcl", "tech mahindra",
        "qualcomm", "intel", "samsung", "flipkart", "deloitte",
    ]
    for company in known:
        if company in query_lower:
            return company
    return ""


mysql_tool = StructuredTool.from_function(
    func=query_placement_db,
    name="mysql_placement_db",
    description=(
        "Query the college's MySQL placement database for student-specific data. "
        "Use this for: student eligibility checks, placement statistics, "
        "company visit records, and cutoff data from the college's own records. "
        "Different from the PDF corpus — this contains live college database records."
    ),
    args_schema=MySQLInput,
)


# ── Tool registry ─────────────────────────────────────────────────────────
# ToolAgent imports ALL_TOOLS — adding tools here is the only change needed.
# No changes required in tool_agent.py or main.py.

ALL_TOOLS = [calculator_tool, corpus_tool, ratio_tool, web_search_tool, mysql_tool]