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
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#F6ECD3','primaryTextColor':'#2B1D0F','primaryBorderColor':'#E89F2A','lineColor':'#2B1D0F','secondaryColor':'#F6ECD3','tertiaryColor':'#FFF'}}}%%
flowchart TB
    classDef user fill:#F6ECD3,stroke:#2B1D0F,stroke-width:2px,color:#2B1D0F
    classDef edge fill:#FFF,stroke:#E89F2A,stroke-width:2px,color:#2B1D0F
    classDef app fill:#E89F2A,stroke:#2B1D0F,stroke-width:2px,color:#2B1D0F
    classDef provider fill:#FFF,stroke:#4E6B3A,stroke-width:2px,color:#2B1D0F
    classDef store fill:#FFF,stroke:#B83A3A,stroke-width:2px,color:#2B1D0F
    classDef external fill:#F6ECD3,stroke:#4E6B3A,stroke-width:2px,color:#2B1D0F
    classDef note fill:#FFF7E1,stroke:#E89F2A,stroke-width:1px,color:#5A3C0B,font-style:italic

    User["👤 Salesperson<br/>(browser)"]:::user
    MCPClient["🔌 MCP client<br/>Claude Desktop · Claude Code · Cursor · Codex"]:::user

    subgraph EDGE["Fly.io edge — waggle.fly.dev"]
        Auth["🔒 BasicAuthMiddleware<br/>WAGGLE_USER / WAGGLE_PASS<br/>(/health public bypass)"]:::edge
    end

    subgraph APP["FastAPI app (uvicorn)"]
        direction TB
        Lifespan["⏱ Lifespan startup<br/>WAGGLE_BOOT_REINDEX=1 →<br/>asyncio.to_thread(reindex_if_empty)<br/><i>post-bind, fire-and-forget</i>"]:::note
        subgraph Routes["Routes"]
            direction LR
            Pages["HTML pages<br/>/ · /inbox · /copilot ·<br/>/customer-reports · /erp-log"]:::app
            API["JSON API<br/>/api/*"]:::app
            SSE["SSE turns<br/>POST /copilot/turns<br/>+ /confirm-{order,report,match}"]:::app
            Health["/health<br/>liveness, public"]:::app
        end
        subgraph Agents["agents/"]
            direction LR
            Extractor["LangGraph<br/>order_extractor"]:::app
            Orchestrator["Copilot<br/>orchestrator"]:::app
        end
    end

    subgraph Providers["providers/ (first-class, not stubs)"]
        direction TB
        Matcher["🧭 semantic_matcher<br/>Stage A: pgvector + FTS (RRF fusion, best-entry-per-target)<br/>Stage B: LLM disambig (gpt-5.4-mini, structured output)<br/>Stage C: public API + per-conv LRU cache<br/>+ MatcherIndexEmpty guard"]:::provider
        VS["vector_search<br/>sentence-transformers (384d)"]:::provider
        Inbox["inbox<br/>fixture-backed"]:::provider
        ERP["erp<br/>JSON-line mock"]:::provider
        Mailer["mailer<br/>sent-mail/ log"]:::provider
        Storage["storage<br/>path-traversal-protected"]:::provider
        LLM["llm<br/>OpenAI / Anthropic"]:::provider
    end

    subgraph Data["Data layer"]
        direction LR
        PG[("Postgres 16 + pgvector<br/>21 tables<br/>(17 baseline + chat_turns/conversations<br/>from migration 003 + customer_search_entries/<br/>sku_search_entries from migration 004)")]:::store
        FS[("Local volumes<br/>gmail-fixtures · erp-sync-log<br/>sent-mail · local-storage")]:::store
    end

    subgraph MCP["MCP servers (stdio)"]
        Sales["sales_copilot_server"]:::app
        Reports["customer_reports_server"]:::app
    end

    OpenAI[("OpenAI API<br/>gpt-5.4-mini · gpt-5.4-nano ·<br/>gpt-5.5 (rare fallback)")]:::external
    Anthropic[("Anthropic API<br/>claude-sonnet-4-6 (toggle)")]:::external

    User --HTTPS Basic Auth--> EDGE
    EDGE --> APP
    MCPClient --stdio--> MCP

    Routes --> Agents
    SSE --post-bind backfill--> Matcher
    Agents --> Providers
    Providers --> Data
    Matcher --> PG
    VS --> PG
    Inbox --> FS
    ERP --> FS
    Mailer --> FS
    Storage --> FS
    MCP --> Providers
    MCP --> PG
    LLM --> OpenAI
    LLM --> Anthropic
    Matcher -.-> LLM
    Orchestrator -.-> LLM
    Extractor -.-> LLM

    style EDGE fill:#FFF7E1
    style APP fill:#FFF7E1
    style Providers fill:#F6ECD3
    style Data fill:#F6ECD3
    style MCP fill:#FFF7E1
    style Routes fill:#FFF
    style Agents fill:#FFF
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-01-system-architecture.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

A FastAPI app sits behind a Fly edge with HTTP Basic auth, fronting
Postgres 16 + pgvector. Two agent entry points (the LangGraph order
extractor and the copilot orchestrator) share one `semantic_matcher`
provider and one LLM provider. The same providers back two stdio MCP
servers, sales-copilot and customer-reports, so an MCP client reaches the
identical matching and retrieval logic the browser UI uses.

### RAG + semantic search

:::{mermaid}
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#F6ECD3','primaryTextColor':'#2B1D0F','primaryBorderColor':'#E89F2A','lineColor':'#2B1D0F'}}}%%
flowchart LR
    classDef src fill:#F6ECD3,stroke:#4E6B3A,stroke-width:2px,color:#2B1D0F
    classDef step fill:#E89F2A,stroke:#2B1D0F,stroke-width:2px,color:#2B1D0F
    classDef store fill:#FFF,stroke:#B83A3A,stroke-width:2px,color:#2B1D0F
    classDef llm fill:#FFF7E1,stroke:#E89F2A,stroke-width:2px,color:#2B1D0F
    classDef out fill:#FFF,stroke:#2B1D0F,stroke-width:2px,color:#2B1D0F

    subgraph Ingest["Ingest path (seed/embeddings.py + boot.py reindex_if_empty)"]
        direction LR
        Reports["customer_reports.<br/>narrative<br/>(40 inspections)"]:::src
        Chunker["Chunker<br/>~512-token windows<br/>(seed/embeddings.py)"]:::step
        ST1["sentence-transformers<br/>all-MiniLM-L6-v2<br/>(local, 384-dim)"]:::step
        Chunks[("documents +<br/>chunks tables<br/>vector(384)")]:::store
        Reports --> Chunker --> ST1 --> Chunks
    end

    subgraph Query["Query path — POST /copilot/turns"]
        direction LR
        Q["User question<br/>e.g. 'varroa trend at O''Reilly?'"]:::src
        Orch["Copilot orchestrator<br/>intent = query"]:::step
        ST2["sentence-transformers<br/>(same model;<br/>cached after first call)"]:::step
        Search["pgvector cosine search<br/>top-k chunks<br/>(LIMIT 5; IVFFLAT_PROBES=10)"]:::step
        Q --> Orch --> ST2 --> Search
        Search --> Chunks
    end

    Build["build_context<br/>assembles retrieved chunks<br/>+ active_account context<br/>+ recent customer hints"]:::step
    Search --> Build

    LLM["gpt-5.4-nano (copilot_main_model)<br/>structured output<br/>+ verbatim-evidence grounding"]:::llm
    Build --> LLM

    Answer["✅ Grounded answer<br/>with citation chips<br/>(text + evidence_used + tool_calls)"]:::out
    LLM --> Answer

    Persist["_persist_assistant_turn<br/>commit() →<br/>on_committed callback<br/>(post-2026-05-19 fix)"]:::step
    Answer --> Persist
    Persist --> ChatTurns[("chat_turns")]:::store

    SSE["SSE stream<br/>complete event<br/>+ try/finally orphan guard"]:::step
    Persist --> SSE
    SSE --> U["👤 User<br/>sees bubble + chips"]:::out
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-06-rag-pipeline.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

Customer-report narratives are chunked, embedded with a local
sentence-transformers model (all-MiniLM-L6-v2, 384-dim), and written to
pgvector at ingest time (seed plus a post-boot reindex). The same embedder
serves queries, so the two vector spaces align: a copilot question embeds,
retrieves top-k chunks by cosine distance, assembles them with the
active-account context, and answers through gpt-5.4-nano with
verbatim-evidence grounding. The reply persists as a chat turn and streams
back over SSE with citation chips.

### Order extraction pipeline

:::{mermaid}
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#F6ECD3','primaryTextColor':'#2B1D0F','primaryBorderColor':'#E89F2A','lineColor':'#2B1D0F'}}}%%
flowchart LR
    classDef fixture fill:#FFF7E1,stroke:#E89F2A,stroke-width:2px,color:#2B1D0F
    classDef step fill:#E89F2A,stroke:#2B1D0F,stroke-width:2px,color:#2B1D0F
    classDef agent fill:#F6ECD3,stroke:#4E6B3A,stroke-width:2px,color:#2B1D0F
    classDef ui fill:#FFF,stroke:#2B1D0F,stroke-width:2px,color:#2B1D0F
    classDef db fill:#FFF,stroke:#B83A3A,stroke-width:2px,color:#2B1D0F
    classDef note fill:#FFF7E1,stroke:#E89F2A,stroke-width:1px,color:#5A3C0B,font-style:italic

    Fixture["📥 gmail-fixtures/*.json<br/>fixture inboxes (16 reps)"]:::fixture
    InboxProv["providers/inbox.py<br/>InboxFixtureMissing → raises<br/>(fail-loud, no silent empty-return)"]:::step
    InboxRoute["/inbox<br/>list emails per rep,<br/>render Extract / Confirm forms"]:::ui

    Click1["[ Extract ]<br/>HTMX POST"]:::ui
    Extractor["agents/order_extractor.py<br/><b>LangGraph StateGraph</b>"]:::agent

    subgraph Pipeline["Extraction pipeline (in order, agents/order_extractor.py)"]
        direction TB
        Classify["1. classify_intent<br/>gpt-5.4-mini"]:::step
        ExtractCust["2. extract_customer_reference<br/>LLM pulls the customer hint string<br/>(gpt-5.4-mini, evidence-grounded)"]:::step
        MatchCust["3. match_customer<br/>providers/semantic_matcher.match_customer<br/>Stage A retrieve + Stage B LLM disambig"]:::step
        ExtractItems["4. extract_line_items<br/>gpt-5.4-nano + structured output<br/>(verbatim grounding for tooltips)"]:::step
        ResolveSKU["5. resolve_skus<br/>providers/semantic_matcher.match_sku<br/>(per-line-item)"]:::step
        Draft["6. assemble_draft<br/>customer + line_items + total → OrderDraft"]:::step
    end

    DraftPartial["Confirm form partial<br/>(qty / unit_price / pollination_date<br/>editable before save)"]:::ui
    Click2["[ Confirm ]<br/>HTMX POST /inbox/confirm"]:::ui
    Persistence["_order_persistence.py<br/>persist_order_from_draft"]:::step
    DB[("orders<br/>+ order_line_items<br/>+ order_state_transitions (None → EXTRACTED)<br/>+ synced_emails")]:::db

    Fixture --> InboxProv --> InboxRoute --> Click1 --> Extractor
    Extractor --> Classify --> ExtractCust --> MatchCust --> ExtractItems --> ResolveSKU --> Draft
    Draft --> DraftPartial --> Click2 --> Persistence --> DB

    NoteHotfix["Schema-evolution guard:<br/>_split_tool_calls / _persist_*_draft<br/>wrap model_validate in try/except<br/>ValidationError → log+skip<br/>(post-2026-05-18 hotfix)"]:::note
    Persistence -.-> NoteHotfix
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-03-ingestion-pipeline-fsm.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

An inbound fixture email surfaces at `/inbox`. Clicking Extract runs a
six-node LangGraph pipeline: classify intent, pull the customer reference,
match it through the `semantic_matcher` (pgvector + FTS retrieval fused by
RRF, then LLM disambiguation), extract line items, resolve each to a SKU
through the same matcher, and assemble a typed `OrderDraft`. The rep edits
quantities and dates in a Confirm form before any row is written to
`orders`.

### Copilot: a live agent turn

:::{mermaid}
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#F6ECD3','primaryTextColor':'#2B1D0F','primaryBorderColor':'#E89F2A','lineColor':'#2B1D0F','signalColor':'#2B1D0F','actorBkg':'#E89F2A','actorBorder':'#2B1D0F'}}}%%
sequenceDiagram
    autonumber
    participant U as 👤 User
    participant R as POST /copilot/turns<br/>(SSE)
    participant SSE as _stream_turn_events<br/>(async generator)
    participant DB as Postgres
    participant O as Orchestrator<br/>(asyncio.to_thread)
    participant M as semantic_matcher
    participant L as OpenAI<br/>(gpt-5.4-mini)

    U->>R: POST text=<br/>"Draft an order for Martinez — 20 Italian queens"
    R->>SSE: invoke generator
    SSE->>DB: INSERT user-turn (commit)
    SSE-->>U: SSE: user_turn HTML
    Note over SSE,DB: assistant_persisted = False<br/>(post-2026-05-19 try/finally guard)
    SSE-->>U: SSE: status "Thinking…"

    par Orchestrator runs in a thread
        SSE->>O: get_copilot_response(text, db, models, conv_id, …)
        O->>L: router LLM (intent = create_order)
        O-->>SSE: stage = intent_routed
        SSE-->>U: SSE: status "Routed your intent…"

        O->>M: match_customer("Martinez")
        M->>DB: Stage A — hybrid retrieve<br/>(pgvector + FTS, RRF fusion)
        DB-->>M: top-5 candidates
        M->>L: Stage B — LLM disambig<br/>(structured output, temp=0)
        L-->>M: CustomerMatch(id=…, evidence, confidence)
        M-->>O: matched customer
        O-->>SSE: stage = context_built
        SSE-->>U: SSE: status "Loaded customer context…"

        O->>L: items extract (gpt-5.4-nano + structured output)
        L-->>O: line items + evidence
        loop per line item
            O->>M: match_sku("Italian queens")
            M->>DB: Stage A retrieve
            M->>L: Stage B disambig
            L-->>M: SkuMatch
            M-->>O: resolved SKU
        end
        O-->>SSE: stage = draft_ready
        SSE-->>U: SSE: status "Building the draft card…"
    end

    SSE->>DB: _persist_assistant_turn<br/>commit()
    Note over DB,SSE: on_committed() callback fires →<br/>assistant_persisted = True<br/>(BEFORE db.refresh, which can fail)
    SSE-->>U: SSE: complete (assistant bubble + Confirm form)

    alt happy path (most turns)
        Note over SSE: finally: flag is True → no synthetic-turn write
    else client disconnects / orchestrator exception
        Note over SSE,DB: finally: flag still False → session_scope() →<br/>INSERT synthetic "Stream interrupted" assistant-turn<br/>(prevents orphan user-turn)
    end
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-04-agent-extraction-sequence.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

The copilot answers in the browser over a single streamed request.
`POST /copilot/turns` commits the user turn, runs the orchestrator on a
worker thread, and emits Server-Sent Events at each stage: intent routed,
customer context built, draft ready. Customer and SKU references resolve
through the same two-stage `semantic_matcher`. The assistant turn persists
on an `on_committed` callback that fires before the row refresh, and a
`try`/`finally` guard writes a synthetic "stream interrupted" turn if the
client disconnects, so a user turn is never left orphaned.

### Order pipeline FSM

:::{mermaid}
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#F6ECD3','primaryTextColor':'#2B1D0F','primaryBorderColor':'#E89F2A','lineColor':'#2B1D0F','secondaryColor':'#FFF7E1'}}}%%
stateDiagram-v2
    direction TB
    [*] --> DRAFT: human creates manually
    [*] --> EXTRACTED: agent extracts from email

    DRAFT --> EXTRACTED: extractor fills line items
    EXTRACTED --> UNDER_REVIEW: ops triage
    UNDER_REVIEW --> APPROVED: ops approves
    UNDER_REVIEW --> CANCELLED: rejected
    APPROVED --> SCHEDULED: production-plan
    SCHEDULED --> PACKED: shipment prepared
    PACKED --> IN_PROGRESS: handed to carrier
    IN_PROGRESS --> FULFILLED: delivered
    FULFILLED --> INVOICED: billing run
    INVOICED --> SYNCED_TO_ERP: ERP submit_sales_order
    SYNCED_TO_ERP --> [*]
    CANCELLED --> [*]

    note left of DRAFT
        Live UI surfaces — what the interactive app does today:
        /inbox extract+confirm and /copilot create-order
        write rows in DRAFT or EXTRACTED via
        app/routes/_order_persistence.py:persist_order_from_draft
        (the ONLY OrderStateTransition writer in the app/agents tree).
    end note

    note right of SYNCED_TO_ERP
        scripts/demo.py writes 5 of the 9 transitions:
        EXTRACTED → UNDER_REVIEW → APPROVED → SCHEDULED → SYNCED_TO_ERP
        + calls providers.erp.submit_sales_order on the final step.
        PACKED / IN_PROGRESS / FULFILLED / INVOICED states exist in
        the schema + seed data but NO live code path writes those
        transitions today. Full UI wiring + the four missing steps
        are tracked follow-ups (matcher_phase_i_summary deferred items).
    end note
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-02-order-pipeline-fsm.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

Orders move through an explicit lifecycle from `DRAFT` or `EXTRACTED`
toward `SYNCED_TO_ERP`. The diagram is honest about where each transition
runs: the interactive app writes only the `DRAFT` and `EXTRACTED` rows
today, through a single order-persistence writer, while `scripts/demo.py`
drives the approve-to-ERP path end to end. The intermediate fulfillment
states exist in the schema and seed data, with their live wiring tracked as
follow-ups.

### Data model

:::{mermaid}
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#F6ECD3','primaryTextColor':'#2B1D0F','primaryBorderColor':'#E89F2A','lineColor':'#2B1D0F'}}}%%
erDiagram
    %% Core territory + identity
    territories ||--o{ territory_assignments : "scopes"
    users ||--o{ territory_assignments : "covers"

    %% Customers + sites
    customers ||--o{ customer_sites : "operates"
    customer_sites ||--o{ customer_reports : "visits logged at"
    users ||--o{ customer_reports : "authored by"

    %% Catalog
    products ||--o{ regulated_items : "restrictions"

    %% Orders
    customers ||--o{ orders : "places"
    users ||--o{ orders : "owned by salesperson"
    synced_emails ||--o{ orders : "source email (nullable)"
    orders ||--o{ order_line_items : "contains"
    products ||--o{ order_line_items : "stocked SKU"
    services ||--o{ order_line_items : "service SKU"
    orders ||--o{ order_state_transitions : "FSM history"
    users ||--o{ order_state_transitions : "actor (nullable)"

    %% RAG corpus (documents are polymorphic via source_type/source_id —
    %% no enforced FK to customer_reports, but in practice that's the
    %% main source)
    documents ||--o{ chunks : "vectorized as"

    %% Copilot conversations
    users ||--o{ conversations : "salesperson (nullable)"
    customers ||--o{ conversations : "active_account (nullable)"
    conversations ||--o{ chat_turns : "thread of"

    %% Matcher Stage A indices (migration 004)
    customers ||--o{ customer_search_entries : "indexed for matcher"
    products ||--o{ sku_search_entries : "indexed for matcher"
    services ||--o{ sku_search_entries : "indexed for matcher"

    territories {
        uuid id PK
        text code UK
        text name
        jsonb metadata
    }
    users {
        uuid id PK
        text email UK
        text name
        text role "apiarist|ops_manager|admin"
        text erp_salesperson_no UK
        bool is_active
    }
    territory_assignments {
        uuid id PK
        uuid user_id FK
        uuid territory_id FK
    }
    customers {
        uuid id PK
        text name
        text erp_customer_no UK
        jsonb aliases
        text market_segment
    }
    customer_sites {
        uuid id PK
        uuid customer_id FK
        text name
        jsonb acreage_by_crop
        jsonb metadata
    }
    products {
        uuid id PK
        text sku UK
        text name
        text category
        numeric price_usd
        bool is_regulated
    }
    services {
        uuid id PK
        text sku UK
        text name
        text category
        text pricing_model
        numeric default_rate_usd
        text description
    }
    regulated_items {
        uuid id PK
        uuid product_id FK
        text restriction_type
        jsonb restricted_states
        text notes
    }
    red_flag_rules {
        uuid id PK
        text rule_name UK
        text scope
        text description
        text severity
        bool is_active
    }
    approval_rules {
        uuid id PK
        text rule_name UK
        text condition_description
        text requires_role
        bool is_active
    }
    customer_reports {
        uuid id PK
        uuid customer_site_id FK
        uuid author_id FK
        date visit_date
        int hives_placed
        numeric varroa_count
        jsonb diseases_observed
        text pesticide_exposure_note
        text narrative
        jsonb tags
    }
    documents {
        uuid id PK
        text source_type "polymorphic"
        uuid source_id "no FK constraint"
        text content
        jsonb metadata
    }
    chunks {
        uuid id PK
        uuid document_id FK
        text content
        vector embedding "384d (pgvector)"
        jsonb metadata
    }
    synced_emails {
        uuid id PK
        text external_id UK
        text thread_id
        text account_id
        text from_address
        jsonb to_addresses
        text subject
        text body_text
        timestamptz received_at
        bool is_classified
    }
    orders {
        uuid id PK
        uuid customer_id FK
        uuid user_id FK
        text state "FSM"
        date pollination_date
        numeric total_usd
        uuid source_email_id FK
        timestamptz created_at
        timestamptz updated_at
    }
    order_line_items {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        uuid service_id FK
        text sku
        int quantity
        numeric unit_price_usd
    }
    order_state_transitions {
        uuid id PK
        uuid order_id FK
        text from_state
        text to_state
        uuid actor_id FK
        timestamptz transitioned_at
        jsonb metadata
    }
    conversations {
        uuid id PK
        uuid salesperson_id FK
        uuid active_account_id FK
        text title
        text model_used
        timestamptz created_at
        timestamptz updated_at
    }
    chat_turns {
        uuid id PK
        uuid conversation_id FK
        text role "user|assistant|system|tool"
        text text
        jsonb tool_calls "+ stashed pending drafts"
        jsonb evidence_used
        text model
        int tokens_input
        int tokens_output
        numeric cost_usd
        int latency_ms
        timestamptz created_at
    }
    customer_search_entries {
        uuid id PK
        uuid customer_id FK
        text entry_text
        text source "name|alias|site"
        vector embedding "384d, IVFFLAT lists=32"
        tsvector tsv "FTS, generated"
        timestamptz created_at
    }
    sku_search_entries {
        uuid id PK
        uuid product_id FK "exactly one of product/service"
        uuid service_id FK
        text entry_text
        text source "product_{name,code,alias} | service_{name,code,alias}"
        vector embedding "384d, IVFFLAT lists=16"
        tsvector tsv "FTS, generated"
        timestamptz created_at
    }
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-05-data-model-er.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

Twenty-one tables: customers and sites, products and services, orders with
their line items and state transitions, customer reports, the document and
chunk corpus behind RAG, copilot conversations and turns, and the matcher
search-entry indices. Relational where the data is relational, vectorized
where it is searched by meaning.

### Glossary: domain, tech, and stack

:::{mermaid}
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#F6ECD3','primaryTextColor':'#2B1D0F','primaryBorderColor':'#E89F2A','lineColor':'#2B1D0F'}}}%%
flowchart TB
    classDef cat fill:#E89F2A,stroke:#2B1D0F,stroke-width:2px,color:#2B1D0F
    classDef term fill:#FFF,stroke:#2B1D0F,stroke-width:1px,color:#2B1D0F
    classDef value fill:#F6ECD3,stroke:#4E6B3A,stroke-width:1px,color:#2B1D0F

    subgraph Domain["Domain — beekeeping & operations"]
        direction TB
        Varroa["<b>Varroa</b><br/>Varroa destructor mite — primary hive health metric;<br/>tracked per visit (pct or per-100-bee count)"]:::value
        Pollination["<b>Pollination service</b><br/>seasonal contract (almond, blueberry, tree-fruit, custom)"]:::value
        Apiary["<b>Apiary / Yard</b><br/>a customer site holding one or more hives"]:::value
        Queen["<b>Queen (mated)</b><br/>per-SKU lineage: Italian (ITA), Carniolan (CAR),<br/>Buckfast (BKF), Russian (RUS), …"]:::value
        Nuc["<b>Nuc (nucleus colony)</b><br/>5-frame starter hive (e.g. NUC-5F-ITA)"]:::value
        Varroa ~~~ Pollination ~~~ Apiary ~~~ Queen ~~~ Nuc
    end

    subgraph Tech["Tech & system"]
        direction TB
        RAG["<b>RAG</b><br/>Retrieval-Augmented Generation —<br/>retrieve grounding chunks → LLM answers with citations"]:::value
        FSM["<b>FSM</b><br/>Finite State Machine — Order lifecycle:<br/>DRAFT → EXTRACTED → … → SYNCED_TO_ERP"]:::value
        MCP["<b>MCP</b><br/>Model Context Protocol — stdio tool-calling protocol;<br/>Waggle exposes sales-copilot + customer-reports servers"]:::value
        SSE["<b>SSE</b><br/>Server-Sent Events — POST /copilot/turns streams<br/>user_turn → status × N → complete events to the browser"]:::value
        FTS["<b>FTS</b><br/>Postgres Full-Text Search — used in matcher Stage A<br/>alongside pgvector cosine, fused via RRF"]:::value
        RRF["<b>RRF</b><br/>Reciprocal Rank Fusion — combines pgvector + FTS rankings<br/>(k=60) into a single Stage A shortlist"]:::value
        IVFFLAT["<b>IVFFLAT</b><br/>pgvector index type;<br/>lists=32 (customers) / 16 (SKUs), probes=10"]:::value
        ERP["<b>ERP</b><br/>Enterprise Resource Planning — Waggle uses a JSON-line<br/>mock (providers/erp.py → /erp-sync-log/YYYYMMDD.jsonl)"]:::value
        RAG ~~~ FSM ~~~ MCP ~~~ SSE ~~~ FTS ~~~ RRF ~~~ IVFFLAT ~~~ ERP
    end

    subgraph Stack["Stack — package & deploy"]
        direction TB
        FastAPI_["<b>FastAPI</b><br/>ASGI app framework; lifespan hosts post-bind reindex task"]:::value
        SQLModel_["<b>SQLModel</b><br/>SQLAlchemy + Pydantic; ORM layer in db/models.py"]:::value
        Alembic_["<b>Alembic</b><br/>migration HEAD: 004 (matcher search-entry tables)"]:::value
        Pgvector_["<b>pgvector</b><br/>Postgres extension; vector(384) columns for embeddings"]:::value
        Fly_["<b>Fly.io</b><br/>deploy target; secrets WAGGLE_USER / WAGGLE_PASS<br/>gate the live site behind HTTP Basic"]:::value
        HTMX_["<b>HTMX</b><br/>hypermedia-driven frontend; Jinja partials swap in place"]:::value
        FastAPI_ ~~~ SQLModel_ ~~~ Alembic_ ~~~ Pgvector_ ~~~ Fly_ ~~~ HTMX_
    end

    subgraph Models["LLM models (per-stage assignments)"]
        direction TB
        Mini["<b>gpt-5.4-mini</b><br/>copilot router, copilot title, matcher Stage B disambig,<br/>extract intent, extract customer, copilot report"]:::value
        Nano["<b>gpt-5.4-nano</b><br/>copilot main answer, extract items<br/>(highest verbatim-grounding rate at low cost)"]:::value
        Five["<b>gpt-5.5</b><br/>fallback resolver only (rare path);<br/>note: API mandates temperature=1 → non-deterministic"]:::value
        Mini ~~~ Nano ~~~ Five
    end
:::

<p class="diagram-fullscreen-row"><a href="/static/diagrams/waggle/waggle-07-acronyms-reference.png" target="_blank" rel="noopener" class="diagram-fullscreen">View fullscreen ↗</a></p>

A reference for the vocabulary the rest of the page assumes: beekeeping
domain terms (Varroa, apiary, queen lineages), the technical acronyms the
architecture leans on (RAG, MCP, SSE, RRF, IVFFLAT), the deployment stack,
and the per-stage LLM model assignments.
