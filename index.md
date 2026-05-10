---
title: Oliver Muellerklein
short_title: Home
description: >-
  Selected work in agentic systems, MCP tooling, and applied AI.
---

::::{div}
:class: hero

:::{image} static/oliver_wave-glitch-v2.png
:alt: Oliver Muellerklein
:class: hero-portrait-img
:::

:::{div}
:class: hero-text

# Oliver Muellerklein

I build agentic systems end-to-end: LLM-driven extraction pipelines,
semantic search, custom MCP tooling, and the full-stack applications
that wrap them. Background in environmental science, geospatial data,
and HPC.

[See Waggle →](/waggle) &nbsp;·&nbsp;
[TRACE on GitHub →](https://github.com/Thru-Echoes/TRACE) &nbsp;·&nbsp;
[Email](mailto:omuellerklein@berkeley.edu)

:::

::::

## Selected work

:::{card} Waggle: agentic CRM
:link: /waggle

A full-stack agentic CRM I built for a beekeeping wholesale domain.
Custom chatbots, an automated ordering pipeline that converts inbound
email into typed orders, and a semantic-search RAG layer over
operational data. **Live app and architecture diagrams.**
:::

<div class="trace-callout">
  <div class="trace-callout-eyebrow">Open source</div>
  <div class="trace-callout-title">TRACE: provenance for AI-assisted workflows</div>
  <div class="trace-callout-body">
    I built TRACE, an open-source MCP-based Python package for tracking who
    made what decision and why in AI-assisted workflows. If you've thought
    hard about agent observability, audit trails, or provenance in
    AI-assisted dev, I want collaborators. Star, open an issue, or send a PR.
  </div>
  <div class="trace-callout-actions">
    <a href="https://github.com/Thru-Echoes/TRACE" target="_blank" rel="noopener" class="trace-callout-button">★ Star on GitHub →</a>
    <a href="https://github.com/Thru-Echoes/TRACE/blob/main/docs/specification.md" target="_blank" rel="noopener" class="trace-callout-button-secondary">Read the spec ↗</a>
  </div>
</div>

## Skills

::::{grid} 1 1 2 2

:::{card} AI / agentic systems
- LLM tool use, prompt engineering, eval design
- Custom MCP server design (Python)
- LangGraph + ReAct agents
- RAG, semantic search, embeddings (pgvector)
- Decision provenance + audit trails (TRACE)
:::

:::{card} Backend / data engineering
- Python: FastAPI, Pydantic, async pipelines
- JavaScript / TypeScript, Clojure / ClojureScript
- Postgres + pgvector, SQL, Alembic migrations
- FSM design, idempotent ETL, schema-first ingest
- Pyright, type-driven Python; Pytest with real-data fixtures
:::

:::{card} Cloud, HPC + containers
- AWS (EC2, SageMaker), Azure, GCP
- HPC: Slurm, batch jobs, distributed compute
- Containers: Docker, Kubernetes
- Apptainer (renamed from Singularity, 2021)
- Reproducible env management across cloud + on-prem
:::

:::{card} Geospatial / mapping
- PostGIS for spatial SQL
- Google Earth Engine: low-level API + scripts
- GDAL / OGR, raster + vector workflows
- Interactive web maps + geospatial models in Python, JavaScript, Clojure / ClojureScript
- Satellite imagery (Sentinel, Landsat), time-series rasters, CRS handling
:::

:::{card} Data science / R / applied ML
- R + RStudio: extensively, ecological + environmental modelling
- Python: pandas, scikit-learn
- Time-series and spatial statistics
- Reproducible analysis pipelines
:::

:::{card} Engineering practice
- E2E testing against real data over mocks
- Fail-loud over silent error swallowing
- Schema-first design, Pydantic across boundaries
- Open-source MCP servers and tooling
- TRACE-style decision provenance for AI work
:::

::::
