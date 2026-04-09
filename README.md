# TechDesk AI — Industry-Grade AI Social Media Agent

> Built as a student project demonstrating production-grade AI engineering patterns.

A fully autonomous AI social media monitoring and response agent that watches Reddit, LinkedIn, and Twitter in real time, classifies incoming signals using a large language model, retrieves relevant answers from a knowledge base, routes them through a multi-agent pipeline, and queues draft replies for human review.

---

## What it does

- Monitors **Reddit**, **LinkedIn**, and **Twitter** simultaneously in real time
- Classifies every signal by **intent** — complaint, praise, question, crisis, viral opportunity
- Retrieves accurate answers from a **RAG knowledge base** (12 TechDesk AI FAQs)
- Routes signals through a **LangGraph multi-agent swarm** — Orchestrator, Engagement, Crisis, ContentCreator agents
- Drafts on-brand replies using **Llama 3.3 70B** via Groq API
- Runs every draft through a **multi-layer safety gate** — keyword filter + toxicity detection
- Queues drafts for **human review** in a real-time web dashboard
- Logs every LLM call and action to an **append-only audit trail** in PostgreSQL
- Collects **RLHF preference data** from human edits for future fine-tuning
- Tracks **strategy performance** using a contextual bandit algorithm

---

## Architecture — 7 layers

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 0 — Perception                                        │
│  Reddit · LinkedIn · Twitter · Simulation → Kafka           │
├─────────────────────────────────────────────────────────────┤
│  Layer 1 — Understanding                                     │
│  Intent classification · Sentiment · Entity extraction      │
├─────────────────────────────────────────────────────────────┤
│  Layer 2 — Planning                                          │
│  LangGraph orchestration · Strategy selection · Routing     │
├─────────────────────────────────────────────────────────────┤
│  Layer 3 — Memory                                            │
│  PostgreSQL + pgvector · Redis · RAG knowledge base         │
├─────────────────────────────────────────────────────────────┤
│  Layer 4 — Action                                            │
│  Draft generation · Platform formatting · Scheduling        │
├─────────────────────────────────────────────────────────────┤
│  Layer 5 — Safety                                            │
│  Keyword filter · Perspective API · HITL review dashboard   │
├─────────────────────────────────────────────────────────────┤
│  Layer 6 — Observability                                     │
│  Audit trail · RLHF collector · Strategy leaderboard        │
└─────────────────────────────────────────────────────────────┘
```

---

## Multi-agent system

```
                    ┌─────────────────┐
    Signal ──────►  │  Orchestrator   │  classifies intent + routes
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐  ┌──────────┐  ┌──────────────────┐
    │  Engagement  │  │  Crisis  │  │ ContentCreator   │
    │    Agent     │  │  Agent   │  │     Agent        │
    │              │  │          │  │                  │
    │ Drafts reply │  │Escalates │  │ Creates proactive│
    │ using RAG    │  │ to HITL  │  │ content for      │
    │ + persona    │  │ urgently │  │ viral signals    │
    └──────────────┘  └──────────┘  └──────────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                    ┌─────────────────┐
                    │  Safety Gate    │  keyword + toxicity check
                    └────────┬────────┘
                             │
                    ┌─────────────────┐
                    │  HITL Queue     │  human review dashboard
                    └─────────────────┘
```

---

## Tech stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| LLM | Llama 3.3 70B via Groq API (free) |
| Agent orchestration | LangGraph |
| Embeddings | fastembed — BAAI/bge-small-en-v1.5 (local, no GPU) |
| Primary database | PostgreSQL 16 + pgvector extension |
| Vector search | pgvector cosine similarity |
| Event streaming | Apache Kafka (KRaft mode, no Zookeeper) |
| Working memory | Redis 7 |
| API framework | FastAPI + WebSocket |
| HITL dashboard | FastAPI + vanilla JS + WebSocket real-time updates |
| Safety | Keyword filter + Google Perspective API |
| Infrastructure | Docker Compose |
| Reddit connector | Public JSON API — no key needed |
| LinkedIn connector | Google News RSS + feedparser — no key needed |

---

## Project structure

```
AI-Social-Agent/
├── main.py                          ← Main orchestrator — Phase 4
├── README.md
├── requirements.txt
├── .env                             ← API keys (never commit this)
│
├── services/
│   ├── perception/
│   │   ├── launcher.py              ← Starts all platform connectors
│   │   ├── main.py                  ← Simulation mode
│   │   ├── reddit_stream.py         ← Reddit public API connector
│   │   ├── linkedin_stream.py       ← LinkedIn + Google News connector
│   │   ├── twitter_stream.py        ← Twitter filtered stream
│   │   └── normalizer.py            ← Normalizes all platforms to SocialSignal
│   │
│   ├── agents/
│   │   ├── graph.py                 ← LangGraph compiled agent graph
│   │   ├── state.py                 ← Shared AgentState TypedDict
│   │   ├── orchestrator.py          ← Routes signals to specialist agents
│   │   ├── engagement.py            ← Drafts replies using RAG + persona
│   │   ├── crisis.py                ← Crisis escalation agent
│   │   └── content_creator.py      ← Proactive content for viral signals
│   │
│   ├── safety/
│   │   └── gate.py                  ← Multi-layer content moderation
│   │
│   ├── hitl/
│   │   ├── dashboard.py             ← FastAPI backend + WebSocket
│   │   └── dashboard.html           ← Review UI — approve/edit/reject
│   │
│   ├── rag/
│   │   └── pipeline.py              ← Embed + retrieve knowledge chunks
│   │
│   └── rlhf/
│       ├── collector.py             ← Saves human edit preference pairs
│       ├── strategy_tracker.py      ← Contextual bandit strategy selector
│       └── dashboard_routes.py      ← RLHF API endpoints
│
├── shared/
│   ├── models.py                    ← Pydantic data models
│   ├── config.py                    ← Settings loader (.env)
│   ├── kafka_client.py              ← Kafka producer/consumer helpers
│   ├── audit.py                     ← Append-only audit trail
│   └── db/
│       └── models.py                ← SQLAlchemy ORM models
│
├── scripts/
│   ├── init_db.py                   ← Creates tables + seeds knowledge base
│   └── export_preferences.py        ← Exports RLHF data to JSONL
│
└── infra/
    └── docker-compose.yml           ← PostgreSQL + Redis + Kafka
```

---

## Database schema

| Table | Purpose |
|---|---|
| `signals` | Every incoming social signal with embedding |
| `actions` | Every agent action — draft, final content, scores |
| `knowledge_base` | RAG document chunks with vector embeddings |
| `audit_log` | Append-only log of every LLM call and publish event |
| `preference_pairs` | RLHF training data from human edits |

---

## Kafka topics

| Topic | Purpose |
|---|---|
| `social.signals.raw` | Raw normalized signals from all platforms |
| `social.signals.classified` | Signals after intent classification |
| `agent.actions.draft` | Draft replies before safety gate |
| `agent.actions.approved` | Approved replies ready to publish |
| `agent.actions.published` | Confirmed published actions |

---

## Setup and running

### Prerequisites
- Docker Desktop or Docker Engine
- Python 3.12
- Groq API key — free at console.groq.com

### Step 1 — Clone and set up environment
```bash
git clone <repo>
cd AI-Social-Agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2 — Configure API keys
```bash
cp .env.example .env
nano .env
# Add your GROQ_API_KEY
```

### Step 3 — Start infrastructure
```bash
docker compose -f infra/docker-compose.yml up -d
```

### Step 4 — Initialize database
```bash
python scripts/init_db.py
```

### Step 5 — Run the system (3 terminal tabs)

**Tab 1 — All platform connectors:**
```bash
python services/perception/launcher.py
```

**Tab 2 — Main agent:**
```bash
python main.py
```

**Tab 3 — HITL dashboard:**
```bash
uvicorn services.hitl.dashboard:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

---

## Environment variables

```env
GROQ_API_KEY=                    # Required — get free at console.groq.com
TWITTER_BEARER_TOKEN=            # Optional — Twitter filtered stream
PERSPECTIVE_API_KEY=             # Optional — Google toxicity detection
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://agent:agentpass@localhost:5432/social_agent
AGENT_ENV=development
HITL_ENABLED=true
SAFETY_THRESHOLD=0.7
LOG_LEVEL=INFO
```

---

## Key engineering decisions

**Why Groq instead of OpenAI?**
Groq provides free API access to Llama 3.3 70B with generous rate limits — perfect for a student project. The architecture supports swapping in any LLM provider by changing one file.

**Why LangGraph instead of LangChain agents?**
LangGraph gives explicit control over the agent graph — nodes, edges, and routing are all code. This makes the system debuggable and predictable, unlike black-box agent frameworks.

**Why Kafka instead of just Redis queues?**
Kafka provides durable, replayable event streaming. If the agent crashes, no signals are lost — the consumer group simply re-reads from its last committed offset. Redis queues are ephemeral.

**Why pgvector instead of a separate vector database?**
pgvector keeps the entire data model in one system. For a project of this scale, the operational simplicity of one database outweighs the performance benefits of a dedicated vector store.

**Why fastembed instead of OpenAI embeddings?**
fastembed runs entirely locally — no API call, no cost, no latency. BAAI/bge-small-en-v1.5 is 384 dimensions and performs well for semantic similarity on short social media text.

---

## What makes this industry-level

| Property | This project |
|---|---|
| Memory | Four-tier: working (Redis) + episodic (pgvector) + semantic (RAG) + procedural (strategy tracker) |
| Agent architecture | Specialized agents with LangGraph orchestration and tool use |
| Safety | Keyword filter + toxicity detection + HITL review + full audit trail |
| Human oversight | Built into the workflow as a first-class concept |
| Feedback loop | RLHF preference collection + contextual bandit strategy selection |
| Observability | Append-only PostgreSQL audit log, every LLM call recorded |
| Scalability | Stateless agents + Kafka = horizontal scaling ready |
| Reliability | Idempotent actions, Kafka consumer groups, error recovery |

---

## Learning roadmap

Built with guidance from the AI Social Agents Industry Guide. Skills used:

- **Python** — async/await, Pydantic, SQLAlchemy, FastAPI
- **LLM engineering** — prompt engineering, tool use, ReAct pattern
- **RAG** — embedding, vector similarity search, context injection
- **Multi-agent systems** — LangGraph state machines, agent specialization
- **Data engineering** — Kafka, streaming, consumer groups
- **Databases** — PostgreSQL, pgvector, Redis
- **Infrastructure** — Docker, docker-compose

---

## Author

Student project — Ankit Negi
Built as a demonstration of industry-grade AI agent engineering patterns.

---

*"Build one layer at a time. Iterate on real data. The best agents are built by engineers who keep learning."*
