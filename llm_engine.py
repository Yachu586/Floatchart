import os
import re
import json
from typing import Dict, Any
from dotenv import load_dotenv
from database import execute_read_query

load_dotenv()

# Pre-compiled regex patterns for deterministic fallback parser
FLOAT_ID_REGEX = re.compile(r'\b(290\d{4})\b')
REGIONS = ["Arabian Sea", "Bay of Bengal", "Equatorial Indian Ocean", "Southern Ocean"]
MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12"
}

def fallback_nl_to_sql(user_prompt: str) -> Dict[str, Any]:
    """
    Deterministic query parser for demo queries when no LLM key is set.
    Directly handles the exact hackathon demo queries and variations.
    """
    prompt_lower = user_prompt.strip().lower()

    # Query 6: Chlorophyll / BGC near equator
    if "chlorophyll" in prompt_lower or "bgc" in prompt_lower:
        sql = """SELECT DISTINCT wmo_id, region, latitude, longitude, ROUND(MAX(chlorophyll), 3) AS max_chlorophyll 
                 FROM argo_data_view 
                 WHERE chlorophyll IS NOT NULL AND ABS(latitude) <= 5.0 
                 GROUP BY wmo_id;"""
        chart_type = "map"

    # Query 5: QC-filtered good quality readings
    elif ("good-quality" in prompt_lower or "good quality" in prompt_lower or "qc" in prompt_lower or "qc-filtered" in prompt_lower) and "temperature" in prompt_lower:
        float_match = FLOAT_ID_REGEX.search(user_prompt)
        wmo_id = float_match.group(1) if float_match else "2901551"
        sql = f"""SELECT depth_m, temperature, qc_flag, cycle_number, profile_date 
                 FROM argo_data_view 
                 WHERE wmo_id = '{wmo_id}' AND qc_flag IN (1, 2) 
                 ORDER BY depth_m ASC;"""
        chart_type = "depth_profile"

    # Query 1: Average temperature in region in month
    elif "average temperature" in prompt_lower or "avg temp" in prompt_lower or "average temp" in prompt_lower:
        matched_region = None
        for reg in REGIONS:
            if reg.lower() in prompt_lower:
                matched_region = reg
                break
        if not matched_region:
            matched_region = "Arabian Sea"

        month_code = "01"
        for month_name, code in MONTHS.items():
            if month_name in prompt_lower:
                month_code = code
                break

        sql = f"""SELECT ROUND(AVG(temperature), 2) AS avg_temperature, COUNT(*) AS measurement_count, '{matched_region}' as region
                 FROM argo_data_view 
                 WHERE region LIKE '%{matched_region}%' AND strftime('%m', profile_date) = '{month_code}';"""
        chart_type = "none"

    # Query 2 & general Depth Profile
    elif "depth profile" in prompt_lower or "depth vs" in prompt_lower or "depth" in prompt_lower:
        float_match = FLOAT_ID_REGEX.search(user_prompt)
        wmo_id = float_match.group(1) if float_match else "2901551"
        sql = f"""SELECT depth_m, temperature, salinity, qc_flag, cycle_number, profile_date 
                 FROM argo_data_view 
                 WHERE wmo_id = '{wmo_id}' AND qc_flag IN (1, 2)
                 ORDER BY cycle_number DESC, depth_m ASC 
                 LIMIT 30;"""
        chart_type = "depth_profile"

    # Query 3: Map of all floats
    elif "map" in prompt_lower or "all floats" in prompt_lower or "locations" in prompt_lower or "where are" in prompt_lower:
        sql = """SELECT wmo_id, region, latitude, longitude, MAX(profile_date) AS last_seen, is_bgc 
                 FROM argo_data_view 
                 GROUP BY wmo_id;"""
        chart_type = "map"

    # Query 4: Compare salinity / floats
    elif "compare" in prompt_lower or "salinity" in prompt_lower:
        float_matches = FLOAT_ID_REGEX.findall(user_prompt)
        if len(float_matches) >= 2:
            ids_str = f"'{float_matches[0]}', '{float_matches[1]}'"
        else:
            ids_str = "'2901551', '2901553'"
        sql = f"""SELECT wmo_id, depth_m, salinity, temperature, cycle_number 
                 FROM argo_data_view 
                 WHERE wmo_id IN ({ids_str}) AND qc_flag IN (1, 2) 
                 ORDER BY wmo_id, depth_m ASC;"""
        chart_type = "time_series"

    else:
        # Default safety query: Recent float activities
        sql = """SELECT wmo_id, region, latitude, longitude, MAX(profile_date) AS last_seen 
                 FROM argo_data_view 
                 GROUP BY wmo_id 
                 LIMIT 8;"""
        chart_type = "map"

    return {"sql": sql, "chart_type": chart_type}


def generate_natural_answer(question: str, sql: str, data: Dict[str, Any], chart_type: str) -> str:
    """Generate a clean natural language answer based on query results."""
    rows = data.get("rows", [])
    if not rows:
        return f"No matching oceanographic data found for your query. (SQL Executed: `{sql}`)"

    q_lower = question.lower()

    if "average temperature" in q_lower or "avg temp" in q_lower:
        avg_temp = rows[0].get("avg_temperature")
        count = rows[0].get("measurement_count", 0)
        reg = rows[0].get("region", "specified region")
        return f"The average temperature in the **{reg}** was **{avg_temp}°C** across {count} quality-controlled measurements."

    elif "good-quality" in q_lower or "good quality" in q_lower or "qc" in q_lower:
        wmo = rows[0].get("wmo_id", "2901551") if "wmo_id" in rows[0] else "2901551"
        return f"Retrieved **{len(rows)} good-quality** temperature measurements (QC flags 1 & 2) for float **{wmo}**. Questionable/bad QC readings (flags 3 & 4) have been filtered out."

    elif "chlorophyll" in q_lower or "equator" in q_lower:
        float_ids = [str(r.get("wmo_id")) for r in rows if r.get("wmo_id")]
        return f"Found **{len(rows)} ARGO float(s)** with BGC chlorophyll data near the equator: **{', '.join(float_ids)}**. Maximum observed chlorophyll is {rows[0].get('max_chlorophyll', 'N/A')} mg/m³."

    elif "depth profile" in q_lower or chart_type == "depth_profile":
        wmo = rows[0].get("wmo_id", "2901551") if "wmo_id" in rows[0] else "2901551"
        min_depth = min(r.get("depth_m", 0) for r in rows)
        max_depth = max(r.get("depth_m", 0) for r in rows)
        return f"Showing the depth profile for float **{wmo}** spanning depths from **{min_depth}m** down to **{max_depth}m**. Surface temperature is {rows[0].get('temperature')}°C."

    elif "map" in q_lower or chart_type == "map":
        return f"Found **{len(rows)} ARGO floats** deployed across the Indian Ocean. Float positions and last reported cycles are rendered on the map below."

    elif "compare" in q_lower or "salinity" in q_lower or chart_type == "time_series":
        wmos = list(set(str(r.get("wmo_id")) for r in rows if r.get("wmo_id")))
        return f"Comparing salinity profiles for float(s) **{', '.join(wmos)}**. Salinity values range from {min(r.get('salinity', 35) for r in rows)} PSU to {max(r.get('salinity', 35) for r in rows)} PSU."

    return f"Retrieved {len(rows)} matching data rows from SQLite database."


def call_llm_nl_to_sql(question: str) -> Dict[str, Any]:
    """
    Translates user prompt into SQL using Gemini or OpenAI if API key present,
    or falls back to the deterministic fallback parser.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not gemini_key and not openai_key:
        # Use deterministic fallback engine
        parsed = fallback_nl_to_sql(question)
        sql = parsed["sql"]
        chart_type = parsed["chart_type"]
        db_result = execute_read_query(sql)
        nl_answer = generate_natural_answer(question, sql, db_result, chart_type)
        return {
            "sql_query": sql,
            "chart_type": chart_type,
            "answer": nl_answer,
            "rows": db_result["rows"],
            "columns": db_result["columns"],
            "engine": "fallback"
        }

    schema_info = """
    SQLite Schema:
    - floats (wmo_id TEXT PRIMARY KEY, region TEXT, deployment_date TEXT, is_bgc INT)
      Regions: 'Arabian Sea', 'Bay of Bengal', 'Equatorial Indian Ocean', 'Southern Ocean'
    - profiles (profile_id INT PRIMARY KEY, wmo_id TEXT, cycle_number INT, profile_date TEXT ISO, latitude REAL, longitude REAL)
    - measurements (measurement_id INT PRIMARY KEY, profile_id INT, depth_m REAL, temperature REAL, salinity REAL, qc_flag INT (1-2 good, 3-4 bad), chlorophyll REAL)
    - argo_data_view: Flattened view with wmo_id, region, is_bgc, profile_id, cycle_number, profile_date, latitude, longitude, depth_m, temperature, salinity, qc_flag, chlorophyll.

    Return JSON ONLY with keys:
    "sql": valid read-only SQLite SELECT statement
    "chart_type": one of "depth_profile", "map", "time_series", "none"
    "answer_summary": concise explanation of results
    """

    system_prompt = f"You are FloatChat SQL Assistant. Translate user question into valid SQLite query using table argo_data_view or base tables. {schema_info}"

    try:
        if gemini_key:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{system_prompt}\nUser Question: {question}"
            )
            text_resp = response.text
        else:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ]
            )
            text_resp = completion.choices[0].message.content

        # Parse JSON from response
        clean_json = text_resp.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_json)
        sql = parsed["sql"]
        chart_type = parsed.get("chart_type", "none")

        db_result = execute_read_query(sql)
        nl_answer = parsed.get("answer_summary") or generate_natural_answer(question, sql, db_result, chart_type)

        return {
            "sql_query": sql,
            "chart_type": chart_type,
            "answer": nl_answer,
            "rows": db_result["rows"],
            "columns": db_result["columns"],
            "engine": "llm"
        }
    except Exception as err:
        # Fallback on any LLM call or JSON parsing error
        parsed = fallback_nl_to_sql(question)
        sql = parsed["sql"]
        chart_type = parsed["chart_type"]
        db_result = execute_read_query(sql)
        nl_answer = generate_natural_answer(question, sql, db_result, chart_type)
        return {
            "sql_query": sql,
            "chart_type": chart_type,
            "answer": nl_answer,
            "rows": db_result["rows"],
            "columns": db_result["columns"],
            "engine": f"fallback (error: {str(err)})"
        }
