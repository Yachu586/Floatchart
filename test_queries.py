import os
import sys

# Explicitly ensure fallback engine is used for testing
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

from llm_engine import call_llm_nl_to_sql

DEMO_TEST_SUITE = [
    {
        "id": 1,
        "query": "What was the average temperature in Arabian Sea in January?",
        "expected_chart_type": "none",
        "description": "Average temperature calculation for Arabian Sea in January"
    },
    {
        "id": 2,
        "query": "Show me the depth profile for float 2901551",
        "expected_chart_type": "depth_profile",
        "description": "Depth profile chart for float 2901551"
    },
    {
        "id": 3,
        "query": "Show me all floats on a map",
        "expected_chart_type": "map",
        "description": "Map coordinates view of all 8 ARGO floats"
    },
    {
        "id": 4,
        "query": "Compare salinity between two floats",
        "expected_chart_type": "time_series",
        "description": "Salinity comparison plot between float pairs"
    },
    {
        "id": 5,
        "query": "Show me only good-quality temperature readings for float 2901551",
        "expected_chart_type": "depth_profile",
        "description": "QC-filtered good quality readings (qc_flag IN (1,2))"
    },
    {
        "id": 6,
        "query": "Which floats have chlorophyll data near the equator?",
        "expected_chart_type": "map",
        "description": "BGC float query filtering chlorophyll near equator"
    }
]

def run_tests():
    print("=" * 70)
    print("  FloatChat End-to-End Fallback Engine Test Suite")
    print("=" * 70)
    
    passed = 0
    total = len(DEMO_TEST_SUITE)

    for test in DEMO_TEST_SUITE:
        q_id = test["id"]
        query_str = test["query"]
        expected_chart = test["expected_chart_type"]
        desc = test["description"]

        print(f"\n[Test {q_id}/{total}] {desc}")
        print(f"  Input Prompt  : \"{query_str}\"")

        try:
            res = call_llm_nl_to_sql(query_str)
            
            sql = res.get("sql_query")
            chart_type = res.get("chart_type")
            rows = res.get("rows", [])
            answer = res.get("answer")

            print(f"  SQL Generated : {sql}")
            print(f"  Chart Type    : {chart_type} (Expected: {expected_chart})")
            print(f"  Rows Returned : {len(rows)}")
            print(f"  NL Answer     : {answer}")

            # Assertions
            assert len(rows) > 0, f"FAILED: Returned 0 rows!"
            assert chart_type == expected_chart, f"FAILED: Expected chart '{expected_chart}', got '{chart_type}'!"

            print(f"  STATUS        : PASSED [OK]")
            passed += 1
        except Exception as e:
            print(f"  STATUS        : FAILED [{str(e)}]")

    print("\n" + "=" * 70)
    print(f"  RESULT: {passed}/{total} Demo Queries PASSED SUCCESSFULLY!")
    print("=" * 70)

    if passed != total:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
