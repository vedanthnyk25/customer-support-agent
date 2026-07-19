# Agentic AI Customer Support Assistant

An end-to-end AI customer support system built using **LangGraph**, **FastAPI**, **Gemini**, **Pinecone**, **PostgreSQL**, and **Next.js**.

Unlike traditional chatbots, this project uses an **agentic workflow** where the LLM reasons about the user's intent, decides which tools to invoke, retrieves live data, executes business actions, and generates grounded responses.

---

# Architecture

```
                        ┌────────────────────────────┐
                        │        Next.js UI          │
                        │  Streaming Chat Interface  │
                        └─────────────┬──────────────┘
                                      │
                               HTTP / SSE
                                      │
                                      ▼
                    ┌────────────────────────────────┐
                    │          FastAPI API           │
                    │       /api/chat endpoint       │
                    └─────────────┬──────────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────────┐
                    │        LangGraph Agent         │
                    │  Persistent Conversation State │
                    └─────────────┬──────────────────┘
                                  │
                        Gemini reasons over prompt
                                  │
                    decides whether tool is required
                                  │
             ┌────────────────────┴────────────────────┐
             │                                         │
             ▼                                         ▼
      Direct AI Response                      Tool Invocation
                                                      │
             ┌────────────────────────────────────────┴─────────────────────────────────────┐
             │                │                  │                 │                        │
             ▼                ▼                  ▼                 ▼                        ▼
     Order Lookup      Product Lookup      Policy Search     Place Order          Support Ticket
             │                │                  │                 │                        │
             ▼                ▼                  ▼                 ▼                        ▼
      PostgreSQL       PostgreSQL         Pinecone VectorDB   PostgreSQL           PostgreSQL
             │                │                  │                 │                        │
             └────────────────┴──────────────────┴─────────────────┴────────────────────────┘
                                              │
                                              ▼
                                   Tool Result returned
                                              │
                                              ▼
                                  Gemini generates answer
                                              │
                                              ▼
                              Streamed back to frontend (SSE)
```

---

# High Level Flow

```
User
   │
   ▼
Frontend (Next.js)
   │
   ▼
FastAPI
   │
   ▼
LangGraph
   │
   ▼
Gemini
   │
   ├── Answer directly
   │
   └── Call Tool
           │
           ▼
 Repository → Service → Database / Vector DB
           │
           ▼
 Tool Result
           │
           ▼
 Gemini
           │
           ▼
 Final Response
           │
           ▼
 Streaming Response to UI
```

---

# Project Components

## Frontend

Built with **Next.js + React**.

Responsible for:

- Chat interface
- Streaming responses through Server Sent Events
- Human confirmation dialogs
- Maintaining thread IDs
- Displaying conversation history

---

## FastAPI Backend

Acts as the gateway between frontend and the AI agent.

Responsibilities:

- Chat API
- Streaming responses
- Resume interrupted conversations
- Session management
- CORS
- Health endpoint

---

## LangGraph

The core orchestration engine.

Responsible for:

- Maintaining conversation state
- Routing between LLM and tools
- Executing multi-step reasoning
- Persisting conversations
- Human-in-the-loop workflows

Graph structure:

```
START
   │
   ▼
Chatbot Node
   │
   ▼
Need Tool?
   │
 ┌─┴──────────┐
 │            │
No           Yes
 │            │
 ▼            ▼
END        Tool Node
               │
               ▼
        Chatbot Node
               │
               ▼
              END
```

---

## Gemini LLM

Responsible for:

- Understanding user intent
- Tool selection
- Parameter extraction
- Final response generation
- Multi-turn reasoning

The LLM never directly accesses databases.

Everything is accessed through tools.

---

## Tool Layer

LangChain Tools expose business capabilities to the LLM.

Available tools:

- Order Lookup
- Place Order
- Product Lookup
- Policy Lookup
- Ticket Creation

Each tool performs one business operation only.

---

## Service Layer

Contains business logic.

Responsibilities include:

- Validation
- Data formatting
- Repository coordination
- Business rules

Keeps the tools lightweight.

---

## Repository Layer

Responsible only for database access.

Handles:

- SQL queries
- CRUD operations
- ORM interaction
- DTO conversion

No business logic exists here.

---

## PostgreSQL

Stores structured application data.

Includes:

- Orders
- Products
- Support Tickets
- Conversation checkpoints
- LangGraph state persistence

---

## Pinecone

Stores vector embeddings for company knowledge.

Used for semantic search over:

- Return policy
- Refund policy
- Warranty
- Shipping
- Internal documentation

Instead of keyword matching, the agent retrieves the most semantically relevant policy before responding.

---

# Human-in-the-Loop (HITL)

Potentially destructive operations require explicit user approval.

Example:

```
User
   │
   ▼
"I want to buy 3 headphones"

Gemini
   │
   ▼
Place Order Tool

   │
   ▼
Interrupt Graph

   │
   ▼
Frontend Confirmation

   │
Confirm / Cancel

   │
   ▼
Resume Graph

   │
   ▼
Complete Order
```

This prevents accidental transactions while preserving conversation context.

---

# Streaming Architecture

```
Frontend
    │
POST /chat
    │
    ▼
FastAPI
    │
    ▼
LangGraph
    │
    ▼
Gemini
    │
Generates tokens
    │
    ▼
Server Sent Events
    │
    ▼
Frontend renders tokens live
```

The user begins seeing output immediately without waiting for the entire response.

---

# Conversation Persistence

Each chat is associated with a unique **thread ID**.

Conversation state is checkpointed in PostgreSQL through LangGraph, allowing:

- Multi-turn conversations
- Memory across requests
- Interrupted workflow recovery
- Resume after confirmation

---

# Repository Structure

```
ai-service/
│
├── app/
│   ├── api/
│   ├── graph/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   ├── tools/
│   ├── prompts/
│   ├── database.py
│   └── main.py
│
├── benchmark/
│
├── seed_db.py
├── seed_policies.py
└── migration_001.py

frontend/
│
├── app/
├── components/
├── lib/
└── public/
```

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| Frontend | Next.js, React, TypeScript |
| Backend | FastAPI |
| Agent Framework | LangGraph |
| LLM | Google Gemini |
| Tool Framework | LangChain Tools |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Vector Database | Pinecone |
| Embeddings | Gemini Embeddings |
| Streaming | Server-Sent Events |
| Conversation Persistence | LangGraph Checkpointer |
| Benchmarking | Async HTTP Load Test Suite |

---

# End-to-End Request Lifecycle

```
1. User sends a message.

2. Frontend forwards it to FastAPI.

3. FastAPI invokes the LangGraph agent.

4. LangGraph loads previous conversation state.

5. Gemini analyzes the request.

6. Gemini decides whether tools are needed.

7. Selected tool executes business logic.

8. Tool queries PostgreSQL or Pinecone.

9. Retrieved data is returned to Gemini.

10. Gemini synthesizes a grounded response.

11. Tokens are streamed back to the frontend.

12. Conversation state is checkpointed for future turns.
```

---

# Key Features

- Agentic multi-step reasoning
- Dynamic tool selection
- Retrieval-Augmented Generation (RAG)
- Live order and product lookup
- AI-powered policy retrieval
- Support ticket generation
- Human-in-the-loop order confirmation
- Persistent conversational memory
- Real-time streaming responses
- Modular layered architecture
- Benchmark suite for latency, throughput, task success, and memory evaluation
