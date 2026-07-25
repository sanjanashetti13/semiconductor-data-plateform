# AI-Orchestrated Semiconductor Sensor Data Warehouse & Quality Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PySpark](https://img.shields.io/badge/PySpark-3.x-orange.svg)](https://spark.apache.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Phase%201%20%7C%20Repository%20Setup-yellow.svg)](#project-status)

---

## Project Overview

This project builds an end-to-end AI-assisted data engineering platform for semiconductor manufacturing analytics using PySpark, Azure SQL, Power BI and Large Language Models. It combines scalable ETL, a dimensional warehouse, automated data quality monitoring, and conversational analytics so manufacturing teams can turn high-volume sensor streams into actionable insight.

---

## Business Problem

Semiconductor manufacturing generates high-dimensional sensor data which must be cleaned, transformed, monitored and modeled before business users can derive insights. Raw SECOM and wafer-defect datasets arrive noisy, incomplete, and difficult to query. Without a governed warehouse and AI-assisted quality controls, yield loss, equipment drift, and process anomalies remain hard to detect in time.

---

## Project Objectives

1. Build a scalable PySpark ETL pipeline for semiconductor manufacturing data.
2. Design and implement a 6-table Star Schema on Azure SQL Database.
3. Integrate AI-assisted automation for:
   - transformation generation
   - data quality monitoring
   - documentation generation
   - natural-language SQL querying
4. Build Power BI dashboards for manufacturing analytics.
5. Improve data quality through automated profiling and anomaly detection.
6. Enable conversational analytics using LLM-powered SQL generation.

---

## Business KPIs

| KPI | Meaning | Business Value |
| --- | --- | --- |
| Yield Rate | Percentage of wafers or lots that pass final inspection and are shippable. | Directly links process control to revenue and scrap reduction. |
| Defect Rate | Proportion of units or dies failing quality thresholds across process steps. | Highlights where rework, scrap, and customer risk originate. |
| Equipment Health Score | Composite indicator of tool stability, drift, and maintenance readiness. | Supports predictive maintenance and reduces unplanned downtime. |
| Sensor/Data Quality Score | Measure of completeness, consistency, validity, and freshness of sensor feeds. | Ensures analytics and AI models are built on trustworthy inputs. |
| Process Step Performance | Throughput, cycle time, and pass rates at each manufacturing stage. | Identifies bottlenecks and optimizes line balance and capacity. |
| Anomaly Detection Rate | Share of sensor or process events flagged as statistical or ML anomalies. | Enables early intervention before yield or quality incidents escalate. |

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Language | Python |
| Distributed processing | PySpark |
| Compute | Databricks Community Edition |
| Warehouse | Azure SQL Database |
| Visualization | Power BI |
| LLM providers | Groq / OpenAI API |
| AI orchestration | LangChain |
| Version control | Git / GitHub |
| Storage format | Apache Parquet |
| Query language | SQL |

---

## Planned AI Modules

| Module | Description |
| --- | --- |
| AI ETL Assistant | Uses LLMs to propose, refine, and document PySpark transformation logic from schema and sample data. |
| AI Data Quality Monitor | Profiles datasets, detects anomalies and rule violations, and summarizes quality issues in natural language. |
| AI Documentation Generator | Auto-generates data dictionaries, pipeline docs, and change summaries from code and metadata. |
| Natural Language SQL Agent | Translates analyst questions into warehouse SQL, executes safely, and returns explainable answers. |

---

## Planned Dashboard Pages

- **Executive Dashboard** — high-level yield, defect, and quality KPIs for leadership.
- **Yield Analytics** — lot/wafer yield trends, process-step contribution, and scrap drivers.
- **Equipment Health** — tool scores, drift signals, and maintenance-oriented views.
- **Data Quality** — sensor completeness, anomaly rates, and pipeline health indicators.

---

## Repository Structure

```text
semiconductor-data-platform/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── .env.example
├── config/
│   └── config.yaml
├── data/
│   ├── raw/
│   │   ├── secom/
│   │   └── wafer_defect/
│   ├── processed/
│   └── warehouse/
├── etl/
│   └── __init__.py
├── ai/
│   ├── __init__.py
│   ├── prompts/
│   └── generated/
├── dashboard/
│   └── screenshots/
├── warehouse/
│   ├── schema.sql
│   └── ddl/
├── notebooks/
├── scripts/
│   └── run_pipeline.py
├── tests/
│   └── test_placeholder.py
├── docs/
│   ├── project_scope.md
│   ├── architecture/
│   │   └── system_architecture.md
│   └── data_dictionary/
├── logs/
├── models/
└── assets/
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Git
- Access to Databricks Community Edition (or local Spark)
- Azure SQL Database (Phase 2+)
- Groq or OpenAI API key for AI modules

### Setup

```bash
git clone https://github.com/<your-org>/semiconductor-data-platform.git
cd semiconductor-data-platform

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # then fill in secrets
```

### Run placeholder pipeline

```bash
python scripts/run_pipeline.py
```

### Run tests

```bash
pytest tests/
```

---

## Project Status

| Phase | Focus | Status |
| --- | --- | --- |
| **Phase 1** | Repository Setup | **(Current)** |
| Phase 2 | ETL Pipelines & Star Schema | Planned |
| Phase 3 | AI Modules & Quality Monitoring | Planned |
| Phase 4 | Power BI Dashboards & NL SQL | Planned |

---

## Contributing

Contributions are welcome once Phase 1 is complete. Please open an issue to discuss proposed changes before submitting a pull request.

---

## License

MIT License

See [LICENSE](LICENSE) for full terms.

---

## Acknowledgments

- SECOM and wafer defect public datasets (for research and prototyping)
- Apache Spark / PySpark community
- Databricks, Azure, Power BI, LangChain, and LLM provider ecosystems
