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

:::{mermaid}
graph TB
    classDef tier fill:#FBF5E5,stroke:#C27F12,stroke-width:1px,color:#2B1D0F
    classDef user fill:#E89F2A,stroke:#2B1D0F,stroke-width:1.5px,color:#2B1D0F
    classDef app fill:#F6C068,stroke:#2B1D0F,stroke-width:1.5px,color:#2B1D0F
    classDef agent fill:#4E6B3A,stroke:#2B1D0F,color:#F6ECD3
    classDef mcp fill:#6B8A4D,stroke:#2B1D0F,color:#F6ECD3
    classDef provider fill:#D9B880,stroke:#5a4a38,color:#2B1D0F
    classDef store fill:#a68a66,stroke:#2B1D0F,color:#F6ECD3
    classDef external fill:#B83A3A,stroke:#2B1D0F,color:#F6ECD3

    subgraph T1 ["1 • User surface"]
        direction LR
        BROWSER["Browser<br/>(Jinja + HTMX dashboard)"]:::user
        MCPCLI["MCP Client<br/>(Claude Desktop / stdio)"]:::user
    end

    subgraph T2 ["2 • FastAPI app"]
        direction LR
        ROUTES["app/routes/<br/>health, customers, orders,<br/>customer_reports, search, agent"]:::app
        PAGES["app/routes/pages.py<br/>Jinja templates"]:::app
        SCHEMAS["app/schemas/<br/>Pydantic v2 DTOs"]:::app
    end

    subgraph T3 ["3 • Agent + MCP layer"]
        direction LR
        AGENT["agents/order_extractor.py<br/>LangGraph StateGraph<br/>6 nodes, fail-loud"]:::agent
        SC["mcp/sales_copilot_server.py<br/>fastmcp · 5 tools"]:::mcp
        CR["mcp/customer_reports_server.py<br/>fastmcp · 4 tools"]:::mcp
        CMATCH["agents/customer_matcher.py<br/>rapidfuzz + normalization"]:::agent
        SKU["agents/sku_resolver.py<br/>exact → fuzzy → llm"]:::agent
    end

    subgraph T4 ["4 • Providers (first-class, local)"]
        direction LR
        P_LLM["llm.py<br/>Anthropic / OpenAI<br/>fail-loud on no key"]:::provider
        P_VEC["vector_search.py<br/>sentence-transformers<br/>+ pgvector cosine"]:::provider
        P_STO["storage.py<br/>local filesystem<br/>(path-traversal safe)"]:::provider
        P_ERP["erp.py<br/>JSON-line mock ledger<br/>(verifying writes)"]:::provider
        P_INB["inbox.py<br/>fixture-backed<br/>inbound mail"]:::provider
        P_MAIL["mailer.py<br/>outbound JSON log"]:::provider
    end

    subgraph T5 ["5 • Data"]
        direction LR
        PG[("Postgres 15<br/>+ pgvector<br/>17 tables · alembic")]:::store
        REDIS[("Redis<br/>(reserved)")]:::store
        FS[("Local volumes<br/>local-storage/ · sent-mail/<br/>erp-sync-log/ · gmail-fixtures/")]:::store
    end

    subgraph T6 ["6 • External (optional)"]
        direction LR
        APILLM["Anthropic / OpenAI API<br/>(the only net dep)"]:::external
    end

    BROWSER --> ROUTES
    BROWSER --> PAGES
    MCPCLI --> SC
    MCPCLI --> CR

    ROUTES --> SCHEMAS
    ROUTES --> AGENT
    ROUTES --> P_VEC
    PAGES --> PG

    AGENT --> CMATCH
    AGENT --> SKU
    AGENT --> P_LLM
    SC --> CMATCH
    SC --> P_LLM
    SC --> P_VEC
    CR --> P_LLM

    CMATCH --> PG
    SKU --> PG
    P_VEC --> PG
    P_ERP --> PG
    P_ERP --> FS
    P_STO --> FS
    P_INB --> FS
    P_MAIL --> FS

    P_LLM -.-> APILLM

    class T1,T2,T3,T4,T5,T6 tier
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-01-system-architecture.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

A FastAPI service fronts a PostgreSQL store with pgvector for
embeddings. Three agent classes coordinate through a custom MCP server:
order extraction, customer matching, and SKU resolution. The agent
chain is exposed through a chat UI on the same web app.

### RAG + semantic search

**Write path — ingestion:**

:::{mermaid}
flowchart LR
    A[Customer report<br/>PDF or text] --> B[pdfplumber<br/>text + metadata]
    B --> D[Section-aware chunker<br/>~800 tokens, 100 overlap]
    D --> E[Chunk + metadata<br/>tenant_id, site_id,<br/>visit_date, author]
    E --> EMB(["Embedder · shared<br/>all-MiniLM-L6-v2 → 384d"])
    EMB --> STORE[("pgvector chunks<br/>HNSW index")]
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-06-rag-pipeline.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

**Read path — query:**

:::{mermaid}
flowchart LR
    subgraph SRC [" "]
        direction TB
        Q["Rep or copilot query<br/>e.g. pesticide exposure<br/>history for OReilly 2026"]
        EMB(["Embedder · shared<br/>all-MiniLM-L6-v2 → 384d"])
    end
    Q -->|text| QV[query vector]
    EMB -->|model| QV
    QV --> SEARCH{"pgvector cosine top-K<br/>WHERE tenant_id =<br/>+ recency filter"}
    STORE[("pgvector chunks<br/>HNSW index")] --> SEARCH
    SEARCH --> RR[Cross-encoder rerank<br/>top-K · optional]
    RR --> CTX[LLM prompt<br/>chunks + cite_ids]
    CTX --> ANS[Answer<br/>inline citations]
    SEARCH -. no match above threshold .-> FAIL[Refuse / escalate to rep]
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-06-rag-pipeline.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

Inbound text (emails, inspection notes, customer reports) is chunked,
embedded, and stored in pgvector at write time. The same embedder
processes queries at read time so the vector spaces line up. Retrieval
filters by tenant and recency before cosine top-K, with an optional
cross-encoder rerank pass on the top-k. If nothing scores above
threshold, the system escalates to a human rep instead of generating an
ungrounded answer.

### Agent extraction sequence

:::{mermaid}
sequenceDiagram
    autonumber
    participant O as Orchard Owner
    participant G as Gmail (fixture)
    participant Q as Celery Queue
    participant C as Classifier
    participant A as Agent
    participant T as MCP Tools
    participant D as Postgres
    participant L as LLM
    participant R as Rep UI

    O->>G: need 400 hives for almond bloom 2/20
    G->>Q: enqueue classify
    Q->>C: classify email
    C->>D: insert SyncedEmail
    C->>Q: enqueue extract
    Q->>A: run extraction
    A->>T: customer_lookup(OReilly Orchard)
    T->>D: pg_trgm similarity
    D-->>T: candidates + confidence
    T-->>A: match id + confidence
    A->>T: customer_report_search(OReilly 2026)
    T->>D: pgvector cosine
    D-->>T: top-3 chunks
    T-->>A: context summaries
    A->>T: product_catalog(almond pollination)
    T-->>A: contract SKUs
    A->>T: pollination_schedule(2026-02-20, Modesto)
    T-->>A: available / conflicts
    A->>T: regulatory_check(order)
    T-->>A: apiary_cert_ok or flags
    A->>L: propose Order (Pydantic)
    L-->>A: structured Order
    A->>D: persist as EXTRACTED
    A-->>R: notify rep
    R->>D: review + approve
    D->>D: transition to APPROVED
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-04-agent-extraction-sequence.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

An inbound email enters the order pipeline. The order-extraction agent
calls MCP tools to fuzzy-match the customer, resolve SKUs against the
catalog, check regulatory constraints, and emit a typed `Order` object.
Every tool call is logged for review.

### Order pipeline FSM

:::{mermaid}
stateDiagram-v2
    [*] --> DRAFT: created by rep
    [*] --> EXTRACTED: agent parsed email
    DRAFT --> EXTRACTED: run extraction
    EXTRACTED --> UNDER_REVIEW: queue for rep
    UNDER_REVIEW --> APPROVED: rep approves
    UNDER_REVIEW --> EXTRACTED: return with notes
    UNDER_REVIEW --> CANCELLED: rep rejects
    APPROVED --> SCHEDULED: pollination contract
    APPROVED --> PACKED: product order
    SCHEDULED --> IN_PROGRESS: hives deployed
    IN_PROGRESS --> FULFILLED: contract complete
    PACKED --> FULFILLED: shipped
    FULFILLED --> INVOICED
    INVOICED --> SYNCED_TO_ERP: ERP mirror
    SYNCED_TO_ERP --> [*]
    CANCELLED --> [*]
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-02-order-pipeline-fsm.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

Orders move through an explicit lifecycle (extracted, matched, priced,
reviewed, synced) with idempotent transitions and stale-state recovery.
The FSM is the contract between the agent and the ERP adapter.

### Data model

:::{mermaid}
erDiagram
    USER ||--o{ TERRITORY_ASSIGNMENT : has
    TERRITORY ||--o{ TERRITORY_ASSIGNMENT : covers
    CUSTOMER ||--o{ CUSTOMER_SITE : operates
    CUSTOMER ||--o{ ORDER : places
    USER ||--o{ ORDER : manages
    ORDER ||--|{ ORDER_LINE_ITEM : contains
    PRODUCT ||--o{ ORDER_LINE_ITEM : as_product
    SERVICE ||--o{ ORDER_LINE_ITEM : as_service
    ORDER ||--o{ ORDER_STATE_TRANSITION : logs
    ORDER ||--o{ RED_FLAG : flagged_by
    APPROVAL_RULE ||--o{ ORDER : governs
    CUSTOMER_SITE ||--o{ CUSTOMER_REPORT : hosts
    USER ||--o{ CUSTOMER_REPORT : authors
    CUSTOMER_REPORT ||--|| DOCUMENT : has
    DOCUMENT ||--|{ CHUNK : chunks_to
    REGULATED_ITEM ||--o{ PRODUCT : classifies
    ERP_SYNC_LOG }o--|| ORDER : records
    USER {
        uuid id PK
        string email
        string role
        string erp_salesperson_no
    }
    CUSTOMER {
        uuid id PK
        string name
        string erp_customer_no
        jsonb aliases
        string market_segment
    }
    CUSTOMER_SITE {
        uuid id PK
        uuid customer_id FK
        string name
        jsonb acreage_by_crop
    }
    ORDER {
        uuid id PK
        uuid customer_id FK
        uuid user_id FK
        string state
        date pollination_date
        decimal total
    }
    CUSTOMER_REPORT {
        uuid id PK
        uuid customer_site_id FK
        uuid author_id FK
        date visit_date
        int hives_placed
        decimal varroa_count
        text narrative
    }
    CHUNK {
        uuid id PK
        uuid document_id FK
        text content
        vector embedding
        jsonb metadata
    }
    RED_FLAG {
        uuid id PK
        string scope
        string rule_name
        jsonb context
    }
    PRODUCT {
        uuid id PK
        string sku
        string category
        decimal price
    }
    SERVICE {
        uuid id PK
        string sku
        string category
        string pricing_model
    }
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-05-data-model-er.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

Customers, sites, products, inspections, orders, and customer reports:
relational where they're relational, vectorized where they're searched
by meaning.
