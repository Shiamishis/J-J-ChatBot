def extract_tables_from_response(response: str, tables: list[str]) -> list[str]:
    """
    Extract table names robustly from an LLM response.

    Handles formats like:
    - ['FACT_Sales', 'DIM_Time']
    - FACT_Sales, DIM_Time
    - "Relevant tables: FACT_Sales and DIM_Time"
    """
    import re

    relevant_tables = []
    for table in tables:
        if re.search(rf"\b{re.escape(table)}\b", response):
            relevant_tables.append(table)
    return relevant_tables


import re


def extract_sql_query(llm_response: str) -> str:
    """
    Extracts the SQL query from a markdown-formatted string.
    Handles blocks with or without the 'sql' language identifier.
    """
    # Regex explains: Look for triple backticks,
    # ignore 'sql' if present, capture everything inside until next backticks.
    pattern = r"```(?:sql)?\n?(.*?)\n?```"
    match = re.search(pattern, llm_response, re.DOTALL)

    if match:
        return match.group(1).strip()

    # Fallback: If no backticks were used, return the whole string (cleaned)
    return llm_response.strip()
