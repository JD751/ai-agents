
Before each edit provide a simple, brief, yet comprehensive explanation of why you are doing that step



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

## Use context 7 mcp where appropriate



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

## Day 4.5- Langsmith Tracing

* Implement Langsmith tracing for the agent

## Day 5 – Production Concerns

Add:

* Request timeout handling
* API robustness
* Fairness and Rate limiting
* Queue Consumer and Worker architecture
* Scalabale backend
* frontend communication strategy
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

## Day 8 – CI/CD Pipeline

Create GitHub Actions:

* Run tests
* Lint
* Build Docker image

Deliverable:
Working CI pipeline.

---




## Day 9 – Deploy to Azure

Deploy container to:

* Azure Container Apps (not AKS — right-sized for this project, no K8s expertise required)

Infrastructure:

* Azure Container Registry (ACR) — store and version Docker images
* Azure Container Apps Environment — shared networking for app + chromadb containers
* Azure Database for PostgreSQL (managed service, not a container)
* Azure Key Vault — store secrets (OPENAI_API_KEY, DATABASE_URL, etc.)

Configure:

* GitHub Actions CD job: push image to ACR, trigger Container Apps redeploy
* Environment variables via Container Apps settings (non-sensitive) and Key Vault references (sensitive)
* Min/max replica scaling rules based on HTTP load
* Managed identity for Container Apps → Key Vault access (no hardcoded credentials)

Deliverable:
Public working endpoint on Azure Container Apps.

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

* Azure Container Apps autoscaling works (KEDA-based, HTTP concurrency triggers).

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



* Design AI system architecture
* Build agent workflows
* Productionize prototypes
* Deploy confidently to Azure
* Speak like a senior engineer


