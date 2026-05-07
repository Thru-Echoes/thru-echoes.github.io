---
title: "Waggle: agentic CRM"
short_title: Waggle
description: >-
  Full-stack agentic CRM for a beekeeping wholesale domain: custom
  chatbots, automated ordering pipeline, semantic-search RAG layer.
---

# Waggle: agentic CRM

A full-stack application I built for a commercial beekeeping wholesale
domain. Custom chatbots, an automated ordering pipeline that converts
inbound email into typed, reviewable orders, and a semantic-search RAG
layer over historical inspections, customer correspondence, and product
data.

- **Live app:** *forthcoming*
- **Code:** *forthcoming*
- **Stack:** Python · FastAPI · Postgres + pgvector · LangGraph · MCP · Docker

---

## How it's built

### System architecture

:::{image} /static/diagrams/waggle/waggle-01-system-architecture.png
:alt: Waggle system architecture
:align: center
:width: 100%
:::

A FastAPI service fronts a PostgreSQL store with pgvector for
embeddings. Three agent classes coordinate through a custom MCP server:
order extraction, customer matching, and SKU resolution. The agent
chain is exposed through a chat UI on the same web app.

### RAG + semantic search

:::{image} /static/diagrams/waggle/waggle-06a-rag-pipeline-top.png
:alt: RAG pipeline - ingestion + query streams
:align: center
:width: 100%
:::

:::{image} /static/diagrams/waggle/waggle-06b-rag-pipeline-bottom.png
:alt: RAG pipeline - retrieval + answer
:align: center
:width: 100%
:::

Inbound text (emails, inspection notes, trip reports) is chunked,
embedded, and stored in pgvector at write time. At query time, the LLM
gets snippets retrieved by semantic similarity, filtered by tenant and
recency, with an optional reranker pass on the top-k.

### Agent extraction sequence

:::{image} /static/diagrams/waggle/waggle-04-agent-extraction-sequence.png
:alt: Agent extraction sequence
:align: center
:width: 100%
:::

An inbound email enters the order pipeline. The order-extraction agent
calls MCP tools to fuzzy-match the customer, resolve SKUs against the
catalog, check regulatory constraints, and emit a typed `Order` object.
Every tool call is logged for review.

### Order pipeline FSM

:::{image} /static/diagrams/waggle/waggle-02-order-pipeline-fsm.png
:alt: Order pipeline FSM
:align: center
:width: 70%
:::

Orders move through an explicit lifecycle (extracted, matched, priced,
reviewed, synced) with idempotent transitions and stale-state recovery.
The FSM is the contract between the agent and the ERP adapter.

### Data model

:::{image} /static/diagrams/waggle/waggle-05-data-model-er.png
:alt: Entity-relationship diagram
:align: center
:width: 100%
:::

Customers, sites, products, inspections, orders, and trip reports:
relational where they're relational, vectorized where they're searched
by meaning.
