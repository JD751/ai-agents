# Product Name

## Consumer Health Content & Claims Assistant

---

# Objective

Build a production-ready AI agent API that:

- Answers questions using RAG with citations  
- Generates compliant marketing content  
- Reviews claims for policy alignment  
- Deploys to Azure using containers  

---

# Core Features

1. Document ingestion (store in Azure Blob Storage)  
2. Embedding generation and vector retrieval  
3. Q&A endpoint with citations  
4. Draft generation endpoint  
5. Compliance review endpoint  
6. Agent orchestration via LangGraph  
7. Logging and evaluation framework  

---

# Non-Functional Requirements

- Containerized with Docker  
- Deployable to Azure Container Apps  
- CI/CD via GitHub Actions  
- Secure secret management  
- Horizontally scalable  
- Fully async API  
- Structured logging  

---

# Tech Stack

- Python  
- FastAPI  
- LangChain  
- LangGraph  
- Azure Blob Storage  
- Docker  
- GitHub Actions  

---

# Success Criteria

- End-to-end deployable system  
- Clean architecture separation  
- Production-ready code quality  
- Clear documentation  
- Architecture diagram included  

Ue context 7 mcp where appropriate

Day 4 Implementation Plan
The goal is to build a LangGraph agent that orchestrates between tools, replacing the stub services with real logic.

1. Implement DraftService
A service that takes a brief and generates compliant marketing copy using the RAG context. It retrieves relevant policy/product docs, then uses an LLM to draft content grounded in them.

2. Implement ReviewService
A service that takes marketing text, runs it against retrieved compliance policy docs, and returns is_compliant + specific notes about violations or approvals.

3. Build a LangGraph Agent (app/agents/)
The agent is the orchestrator. It exposes three tools:

rag_tool — answers factual questions (wraps RAGService)
draft_tool — generates marketing drafts (wraps DraftService)
review_tool — reviews copy for compliance (wraps ReviewService)
The LangGraph graph will have:

A reasoning node (LLM decides which tool to call based on user intent)
Tool nodes for each capability
A loop back to the reasoning node after each tool call until the agent decides it's done
4. Wire Agent into API
The /draft and /review endpoints will call the agent (or their dedicated services directly). Optionally add a new /agent endpoint that accepts free-form queries and lets the agent decide what to do.

5. Add Tests
Basic tests for draft and review endpoints to confirm they return real content (not stubs).

Architecture after Day 4:


User Request
    ↓
FastAPI Endpoint
    ↓
LangGraph Agent  ←──── memory (in-memory for now)
    ↓
  Tool Selection
  ├── rag_tool     → RAGService (Chroma + OpenAI)
  ├── draft_tool   → DraftService (RAG-grounded generation)
  └── review_tool  → ReviewService (policy compliance check)


Here is a **tight 21 day execution plan** 
---

# 🗓 WEEK 1 — Build a Production-Ready AI Core

Goal: Build a clean, structured AI backend locally.

---

## Day 1 – Project Architecture

Create a clean repo structure:

```
app/
  api/
  core/
  agents/
  services/
  models/
  config/
tests/
Dockerfile
docker-compose.yml
```

Set up:

* FastAPI
* Poetry or pip + requirements
* .env config management
* Logging config
* Pre-commit hooks

Deliverable:
FastAPI app running locally with structured logging and config separation.

---

## Day 2 – Clean FastAPI Patterns

Implement:

* Pydantic request/response models
* Dependency injection
* Health endpoint
* Versioned API route
* Proper exception handling

Deliverable:
Professional API skeleton ready for production.

---

## Day 3 – RAG Implementation

Use:

* LangChain
* Vector DB like FAISS or Chroma

Implement:

* Document ingestion
* Embeddings
* Retrieval pipeline
* Simple evaluation script

Deliverable:
Working RAG endpoint `/ask`.

---

## Day 4 – Build an Agent with LangGraph

Use:

* LangGraph
* Tool calling
* Memory handling

Create:
* Vector database made permeanent
* create draft service
* create review service
* Agent that chooses between retrieval and tool
* Basic reasoning loop

Deliverable:
Functional AI agent endpoint.

---

## Day 5 – Production Concerns

Add:

* Request timeout handling
* Retry logic
* Structured logging for prompts + outputs
* Basic response validation

Deliverable:
AI service that does not look like a hackathon demo.

---

# 🗓 WEEK 2 — Industrialization + Cloud

Goal: Make it deployable and cloud ready.

---

## Day 6 – Docker Deep Dive

Write:

* Multi stage Dockerfile
* Small image
* Proper environment variables
* Non root user

Test locally.

Deliverable:
Clean containerized app.

---

## Day 7 – Docker Compose + Local Simulation

Simulate:

* App
* Vector DB
* Database (PostgreSQL optional)

Deliverable:
Full local production-like environment.

---

## Day 8 – CI Pipeline

Create GitHub Actions:

* Run tests
* Lint
* Build Docker image

Deliverable:
Working CI pipeline.

---

## Day 9 – Deploy to Azure

Deploy container to:

* Azure Container Apps

Configure:

* Environment variables
* Secrets
* Scaling rules

Deliverable:
Public working endpoint.

---

## Day 10 – Storage Integration

Integrate:

* Azure Blob Storage

Store:

* Uploaded documents
* Logs or metadata

Deliverable:
Cloud integrated RAG system.

---

# 🗓 WEEK 3 — Senior Level Thinking

Goal: Move from “engineer” to “senior engineer.”

---

## Day 11 – AI Evaluation

Implement:

* RAG evaluation metrics
* Response scoring
* Simple hallucination detection
* Prompt version tracking

Deliverable:
Evaluation module.

---

## Day 12 – Scalability Concepts

Study:

* Horizontal scaling
* Container scaling triggers
* Rate limiting
* Caching strategies
* Async request handling

Understand how:

* Azure Kubernetes Service works conceptually.

Deliverable:
Architecture diagram for scaled AI API.

---

## Day 13 – Observability

Add:

* Structured logs
* Request IDs
* Performance metrics
* Basic monitoring hooks

Deliverable:
Observable AI service.

---

## Day 14 – Security

Implement:

* API key auth
* Basic role protection
* Secure secret handling
* Input validation

Deliverable:
Production-safe API.

---

## Day 15 – Refactor for Clean Code

Refactor:

* Remove tight coupling
* Improve modularity
* Clean architecture separation

Deliverable:
Senior-level repo quality.

---

# Final 6 Days — Polish & Mastery

Days 16–17
Write:

* README
* Architecture diagram
* Deployment documentation

Days 18–19
Practice explaining:

* RAG design decisions
* Agent architecture
* Deployment choices
* Scaling strategy

Days 20–21
Simulate real scenarios:

* Take a notebook prototype
* Turn it into production API in 1 day

This is exactly what he will do on the job.

---

# 🔥 What This Achieves

By start date, he will be able to:

* Design AI system architecture
* Build agent workflows
* Productionize prototypes
* Deploy confidently to Azure
* Speak like a senior engineer

That drastically reduces probation risk.

---

If you want, I can now design a concrete project theme tailored to Bayer’s commercial and marketing domain so it aligns perfectly with their business context.
