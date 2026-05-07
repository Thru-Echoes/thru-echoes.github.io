---
title: "Waggle — agentic CRM"
short_title: Waggle
description: >-
  Full-stack agentic CRM for a beekeeping wholesale domain — custom
  chatbots, automated ordering pipeline, semantic-search RAG layer.
---

# Waggle — agentic CRM

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

![Waggle system architecture](/static/diagrams/waggle/waggle-01-system-architecture.png)

A FastAPI service fronts a PostgreSQL store with pgvector for
embeddings. Three agent classes — order extraction, customer matching,
SKU resolution — coordinate through a custom MCP server. The agent
chain is exposed through a chat UI on the same web app.

### RAG + semantic search

![RAG pipeline](/static/diagrams/waggle/waggle-06-rag-pipeline.png)

Inbound text — emails, inspection notes, trip reports — is chunked,
embedded, and stored in pgvector at write time. At query time, the LLM
gets snippets retrieved by semantic similarity, filtered by tenant and
recency, with an optional reranker pass on the top-k.

### Agent extraction sequence

![Agent extraction sequence](/static/diagrams/waggle/waggle-04-agent-extraction-sequence.png)

An inbound email enters the order pipeline. The order-extraction agent
calls MCP tools to fuzzy-match the customer, resolve SKUs against the
catalog, check regulatory constraints, and emit a typed `Order` object.
Every tool call is logged for review.

### Order pipeline FSM

![Order pipeline FSM](/static/diagrams/waggle/waggle-02-order-pipeline-fsm.png)

Orders move through an explicit lifecycle — extracted, matched, priced,
reviewed, synced — with idempotent transitions and stale-state recovery.
The FSM is the contract between the agent and the ERP adapter.

### Data model

![Entity-relationship diagram](/static/diagrams/waggle/waggle-05-data-model-er.png)

Customers, sites, products, inspections, orders, and trip reports —
relational where they're relational, vectorized where they're searched
by meaning.
