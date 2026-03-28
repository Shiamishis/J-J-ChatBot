def extract_tables_from_response(response: str, tables: list[str]) -> list[str]:
    # Checks for every table if it appears in the response as a seperate word
    relevant_tables = []
    for table in tables:
        if f" {table} " in f" {response} ":
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
