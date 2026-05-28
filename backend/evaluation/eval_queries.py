"""
eval_queries.py — Official 30-query evaluation set from Section 9.

Each query includes:
  - id, question, difficulty, rag_skill
  - expected_answer (ground truth for scoring)
  - expected_query_type (for routing correctness check)
"""

EVAL_QUERIES = [
    # ── Easy (E) ─────────────────────────────────────────────────────────
    {
        "id": "E1", "difficulty": "easy", "rag_skill": "direct_table_lookup",
        "question": "What is the CGPA requirement for TCS?",
        "expected_answer": "7.5",
        "expected_query_type": "threshold_filter",
    },
    {
        "id": "E2", "difficulty": "easy", "rag_skill": "direct_table_lookup",
        "question": "How many backlogs does Deloitte allow?",
        "expected_answer": "1",
        "expected_query_type": "direct_lookup",
    },
    {
        "id": "E3", "difficulty": "easy", "rag_skill": "direct_table_lookup",
        "question": "What is the bond period for Amazon?",
        "expected_answer": "2",
        "expected_query_type": "direct_lookup",
    },
    {
        "id": "E4", "difficulty": "easy", "rag_skill": "direct_table_lookup",
        "question": "Which technology does Flipkart focus on in interviews?",
        "expected_answer": "Python",
        "expected_query_type": "direct_lookup",
    },
    {
        "id": "E5", "difficulty": "easy", "rag_skill": "direct_table_lookup",
        "question": "What is the package offered by Google?",
        "expected_answer": "42.0 LPA",
        "expected_query_type": "direct_lookup",
    },
    {
        "id": "E6", "difficulty": "easy", "rag_skill": "boolean_table_query",
        "question": "Does Microsoft allow backlogs?",
        "expected_answer": "Yes, 1 backlog",
        "expected_query_type": "direct_lookup",
    },
    {
        "id": "E7", "difficulty": "easy", "rag_skill": "text_retrieval",
        "question": "What rounds does TCS conduct?",
        "expected_answer": "Online Assessment, Technical Interview (System Design), Managerial/HR",
        "expected_query_type": "direct_lookup",
    },
    {
        "id": "E8", "difficulty": "easy", "rag_skill": "text_retrieval",
        "question": "Which programming language is tested at Amazon?",
        "expected_answer": "C++",
        "expected_query_type": "direct_lookup",
    },

    # ── Medium (M) ────────────────────────────────────────────────────────
    {
        "id": "M1", "difficulty": "medium", "rag_skill": "multi_row_filter",
        "question": "List all companies that allow at least 2 backlogs.",
        "expected_answer": "Flipkart, IBM, HCL, Tech Mahindra, Qualcomm, Samsung R&D, Amazon",
        "expected_query_type": "threshold_filter",
    },
    {
        "id": "M2", "difficulty": "medium", "rag_skill": "threshold_filter",
        "question": "Which companies require a CGPA above 8.0?",
        "expected_answer": "Infosys (8.0), Accenture (8.2), Cognizant (8.4), SAP (8.4), HCL (8.4), Tech Mahindra (8.1)",
        "expected_query_type": "threshold_filter",
    },
    {
        "id": "M3", "difficulty": "medium", "rag_skill": "category_sort",
        "question": "Which company has the highest package among IT service firms?",
        "expected_answer": "Infosys at 42.9 LPA",
        "expected_query_type": "threshold_filter",
    },
    {
        "id": "M4", "difficulty": "medium", "rag_skill": "boolean_filter",
        "question": "Which companies are bond-free?",
        "expected_answer": "TCS, Infosys, Microsoft, IBM, Intel",
        "expected_query_type": "threshold_filter",
    },
    {
        "id": "M5", "difficulty": "medium", "rag_skill": "multi_attribute_comparison",
        "question": "Compare TCS and Infosys on all eligibility criteria.",
        "expected_answer": "TCS: CGPA 7.5, 0 backlogs, 4.1 LPA, 0 bond. Infosys: CGPA 8.0, 0 backlogs, 42.9 LPA, 0 bond.",
        "expected_query_type": "direct_lookup",
    },
    {
        "id": "M6", "difficulty": "medium", "rag_skill": "chart_table_comparison",
        "question": "How many SDE roles does Amazon hire versus Google?",
        "expected_answer": "Amazon=42, Google=30",
        "expected_query_type": "direct_lookup",
    },
    {
        "id": "M7", "difficulty": "medium", "rag_skill": "hiring_table_aggregation",
        "question": "Which company hires the most Interns?",
        "expected_answer": "Oracle (95)",
        "expected_query_type": "direct_lookup",
    },
    {
        "id": "M8", "difficulty": "medium", "rag_skill": "text_retrieval_synthesis",
        "question": "What topics should I prepare for a Microsoft interview?",
        "expected_answer": "DSA (Trees, Graphs), OS (threading, deadlocks), DBMS (indexing, normalisation), C++",
        "expected_query_type": "direct_lookup",
    },
    {
        "id": "M9", "difficulty": "medium", "rag_skill": "temporal_reasoning",
        "question": "Which company's package grew the most from 2021 to 2024?",
        "expected_answer": "Infosys — grew by 6.9 LPA (36.0 to 42.9)",
        "expected_query_type": "temporal",
    },
    {
        "id": "M10", "difficulty": "medium", "rag_skill": "column_filter",
        "question": "Which companies use Python as the technical focus?",
        "expected_answer": "Google, Flipkart, Oracle, Intel",
        "expected_query_type": "threshold_filter",
    },

    # ── Hard (H) ──────────────────────────────────────────────────────────
    {
        "id": "H1", "difficulty": "hard", "rag_skill": "3_condition_filter",
        "question": "A student with CGPA 7.0, 1 backlog wants maximum pay with no bond.",
        "expected_answer": "Wipro (26.1 LPA) — eligible (CGPA 6.7 req, 1 backlog ok, 1 yr bond). Among 0-bond: Microsoft (21.4), IBM (27.5). IBM at 27.5 LPA.",
        "expected_query_type": "eligibility_package",
    },
    {
        "id": "H2", "difficulty": "hard", "rag_skill": "join_tech_hiring",
        "question": "Which Python-focused company hires the most Interns?",
        "expected_answer": "Oracle — Python focus, 95 interns",
        "expected_query_type": "tech_package",
    },
    {
        "id": "H3", "difficulty": "hard", "rag_skill": "filter_sort",
        "question": "For CGPA 8.0+, zero backlog students, rank companies by package.",
        "expected_answer": "Cognizant (42.3), Infosys (42.9), Capgemini (38.3), SAP (20.7), Accenture (17.3), HCL (28.1)",
        "expected_query_type": "eligibility_package",
    },
    {
        "id": "H4", "difficulty": "hard", "rag_skill": "conflict_detection",
        "question": "Which company had conflicting CGPA data across sources?",
        "expected_answer": "TCS, Amazon, Google, Infosys, Microsoft",
        "expected_query_type": "conflict",
    },
    {
        "id": "H5", "difficulty": "hard", "rag_skill": "conflict_resolution",
        "question": "Is the Amazon CGPA cutoff 6.4 or 7.0? Explain.",
        "expected_answer": "Both exist — official says 6.4, portal says 7.0. Verify with placement cell.",
        "expected_query_type": "conflict",
    },
    {
        "id": "H6", "difficulty": "hard", "rag_skill": "computed_aggregation",
        "question": "Which company offers the best package-to-CGPA ratio?",
        "expected_answer": "Samsung R&D (7.6/6.3 = 1.21 — highest ratio, though absolute package is low). For high absolute: Infosys (42.9/8.0 = 5.36).",
        "expected_query_type": "general",
    },
    {
        "id": "H7", "difficulty": "hard", "rag_skill": "full_synthesis",
        "question": "Compare Google and Amazon on all dimensions: eligibility, package, hiring, trend.",
        "expected_answer": "Google: CGPA 7.4, 0 backlogs, 42.0 LPA, 1yr bond, Python, 198 total hires (30 SDE, 92 Analyst). Amazon: CGPA 6.4, 1 backlog, 28.6 LPA, 2yr bond, C++, 200 total hires (42 SDE, 36 Analyst). Google pays more, Amazon more accessible.",
        "expected_query_type": "general",
    },

    # ── Expert (X) ────────────────────────────────────────────────────────
    {
        "id": "X1", "difficulty": "expert", "rag_skill": "out_of_corpus_fallback",
        "question": "What is TCS's campus visit date at SVECW?",
        "expected_answer": "NOT_IN_CORPUS",
        "expected_query_type": "out_of_corpus",
    },
    {
        "id": "X2", "difficulty": "expert", "rag_skill": "opinion_subjective",
        "question": "Should I join Google or Microsoft? Which is better for my career?",
        "expected_answer": "SUBJECTIVE — present objective comparison only",
        "expected_query_type": "out_of_corpus",
    },
    {
        "id": "X3", "difficulty": "expert", "rag_skill": "below_threshold_edge",
        "question": "I have CGPA 5.0. Where can I apply?",
        "expected_answer": "No company in this dataset has a CGPA cutoff ≤ 5.0.",
        "expected_query_type": "out_of_corpus",
    },
    {
        "id": "X4", "difficulty": "expert", "rag_skill": "realtime_out_of_corpus",
        "question": "What is Infosys's current stock price?",
        "expected_answer": "NOT_IN_CORPUS",
        "expected_query_type": "out_of_corpus",
    },
    {
        "id": "X5", "difficulty": "expert", "rag_skill": "scope_boundary",
        "question": "Which company in this dataset pays the highest in the world?",
        "expected_answer": "The corpus only covers these 19 companies — comparison to global companies not possible.",
        "expected_query_type": "out_of_corpus",
    },
]

# Index by ID for fast lookup
EVAL_BY_ID = {q["id"]: q for q in EVAL_QUERIES}