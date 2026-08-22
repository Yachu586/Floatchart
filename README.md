# FloatChat — Ocean ARGO Float Conversational Interface

FloatChat is a conversational MVP for querying oceanographic ARGO float data using natural language. It translates natural language questions into safe SQL queries, executes them against a SQLite database seeded with synthetic Indian Ocean float data, and visualizes the results with Plotly line charts or Leaflet maps.

## Features
- **NL-to-SQL Engine**: Translates natural language questions to read-only SQL queries using Gemini or OpenAI LLMs (with smart deterministic fallback parser if no API key is provided).
- **Interactive Visualizations**:
  - **Depth Profiles**: Inverted depth vs. temperature and salinity line charts via Plotly.js.
  - **Float Maps**: Interactive Leaflet.js maps with custom ocean float markers and region tags.
  - **Time Series & Comparisons**: Salinity & temperature comparisons between floats over time.
  - **BGC & QC Filtering**: Supports biogeochemical data (chlorophyll) and ARGO Quality Control flags (`qc_flag IN (1, 2)`).
- **Preset Demo Prompts**: 6 built-in click-to-query prompts for quick hackathon demos.

---

## Setup & Running Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Seed the Database
Seed `argo_data.db` with 8 realistic ARGO floats, profiles, depth measurements, BGC data, and QC flags:
```bash
python seed_db.py
```

### 3. (Optional) Configure API Key
Create a `.env` file in the root directory if you want to use an LLM API:
```env
GEMINI_API_KEY=your_gemini_api_key_here
# OR
OPENAI_API_KEY=your_openai_api_key_here
```
*Note: If no API key is provided, FloatChat automatically operates using its built-in deterministic query engine, ensuring 100% reliable hackathon demo execution.*

### 4. Launch the Server
```bash
uvicorn main:app --reload --port 8000
```
Open your browser and navigate to: **[http://localhost:8000](http://localhost:8000)**

---

## Demo Queries Tested End-to-End
1. `"What was the average temperature in Arabian Sea in January?"`
2. `"Show me the depth profile for float 2901551"`
3. `"Show me all floats on a map"`
4. `"Compare salinity between two floats"`
5. `"Show me only good-quality temperature readings for float 2901551"`
6. `"Which floats have chlorophyll data near the equator?"`

To run the automated verification test suite:
```bash
python test_queries.py
```
