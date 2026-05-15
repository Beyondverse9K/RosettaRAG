# RosettaRAG

RosettaRAG is an Private Enterprise Retrieval-Augmented Generation (RAG) system for (Hypothetical Organization) Chromatic Prism Corp. It routes questions across relational, graph, and vector data sources, applies relevance grading and hallucination checks, and delivers grounded answers through a modern React UI backed by a FastAPI + LangGraph workflow.

## Features
- **Polyglot routing** across SQL, Neo4j, and Pinecone with structured LLM outputs.
- **Hybrid retrieval** with Text-to-SQL, Text-to-Cypher, and HyDE-based vector search.
- **CRAG relevance grading** to filter weak context before generation.
- **Self-RAG grounding checks** with retry limits to reduce hallucinations.
- **Multi-hop agent** for cross-database questions using tool-based reasoning.
- **Persistent memory** via LangGraph Postgres checkpointer.
- **Guardrail Intercept** which short-circuits the workflow for irrelevant questions.
- **Frontend workflow visualizer** showing routing, retrieval, grading, and generation.

## Use Cases
- HR and payroll queries (salaries, departments, roles).
- Org chart questions (reporting lines, leadership, project ownership).
- Policy lookups (IT, HR, Legal, Finance, Security).
- Project intelligence (status, scope, budget from internal wikis).
- Cross-domain analytics (e.g., combine org structure + budgets + project details).

## Technology Stack
**Backend**
- FastAPI, LangGraph, LangChain
- Gemini LLMs (gemini-2.5-flash / gemini-2.5-flash-lite) + Gemini embeddings (gemini-embedding-2-preview)
- PostgreSQL (Neon) for relational data and conversation memory
- Neo4j for graph relationships
- Pinecone for vector search

**Frontend**
- React, Tailwind CSS, axios

**Data & Ingestion**
- Faker-based synthetic dataset generator

**Deployment**
- Render (Backend)
- Netlify (Frontend)

## Architecture

### Component Diagram
```mermaid
flowchart LR
  UI[React UI] --> API[FastAPI /api/chat]
  API --> WF[LangGraph Workflow]
  WF --> Router[Router LLM]
  WF --> SQL[(Postgres)]
  WF --> Graph[(Neo4j)]
  WF --> Vec[(Pinecone)]
  WF --> Gen[Generator LLM]
  WF --> Mem[(Postgres Checkpointer)]
  Router --> WF
  Gen --> WF
  WF --> API
  API --> UI
```

### Sequence Diagram
```mermaid
sequenceDiagram
  participant User as User
  participant UI as React UI
  participant API as FastAPI
  participant WF as LangGraph
  participant R as Router LLM
  participant SQL as Postgres
  participant G as Neo4j
  participant V as Pinecone
  participant Gen as Generator LLM
  participant Mem as Postgres Memory

  User->>UI: Submit question
  UI->>API: POST /api/chat
  API->>WF: invoke(question, messages)
  WF->>R: route_question
  R-->>WF: datasource
  alt reject
    WF-->>API: guardrail response
  else retrieve
    WF->>SQL: Text-to-SQL (if relational_db)
    WF->>G: Text-to-Cypher (if graph_db)
    WF->>V: HyDE + similarity search (if vector_db)
    WF->>WF: multi-hop tool calls (if multi_hop)
    WF->>WF: CRAG relevance grading
    WF->>Gen: generate_answer
    WF->>WF: self-RAG grounding check (<=3 retries)
    WF->>Mem: persist conversation state
    WF-->>API: final answer + datasource
  end
  API-->>UI: response
```
