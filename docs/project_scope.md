# Project Scope

## Summary

Build an AI-orchestrated semiconductor sensor data warehouse and quality analytics platform that ingests manufacturing sensor data, models it in a star schema on Azure SQL, monitors quality with LLM assistance, and exposes insights via Power BI and natural-language querying.

## In Scope

- PySpark ETL for SECOM and wafer-defect (and similar) datasets
- 6-table star schema on Azure SQL Database
- AI modules: ETL assistant, data quality monitor, documentation generator, NL SQL agent
- Power BI dashboards (Executive, Yield, Equipment Health, Data Quality)
- Automated profiling and anomaly detection support
- GitHub-hosted repository with professional engineering practices

## Out of Scope (initial releases)

- Real-time MES/SCADA streaming ingestion (batch-first)
- Full MES master data management
- On-premise fab network integration beyond documented file/API landings
- Production multi-tenant SaaS packaging

## Phases

| Phase | Deliverable |
| --- | --- |
| Phase 1 | Repository setup, docs, scaffolding **(current)** |
| Phase 2 | ETL pipelines, Parquet layers, Azure SQL star schema |
| Phase 3 | AI modules (LangChain + Groq/OpenAI) |
| Phase 4 | Power BI dashboards and conversational analytics polish |

## Success Criteria

- Reproducible local/Databricks pipeline entry points
- Documented warehouse schema and data dictionary
- Measurable KPI views for yield, defects, equipment, and data quality
- Safe, reviewed AI-assisted SQL and documentation workflows
