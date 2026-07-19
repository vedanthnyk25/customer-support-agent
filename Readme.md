# AI Customer Support Agent

An agentic customer support system: a FastAPI + LangGraph backend that gives a
Gemini LLM tool access to a company's orders, product catalog, and policy
knowledge base, with token-level streaming, multi-turn memory, RAG-based
policy answers, and a human-in-the-loop confirmation flow before placing an
order. A Next.js frontend consumes the stream and renders it as a live chat
UI, including an interactive order-confirmation card.

This document explains **what every part does, why it's built that way, and
how the pieces fit together** — written so you can use it directly as
interview prep, not just as setup instructions.

---

## 1. High-level architecture

```
┌─────────────────────┐        HTTP POST + SSE        ┌──────────────────────────┐
│   Next.js Frontend   │ ─────────────────────────────▶│      FastAPI Backend     │
│  (chat-container.tsx)│ ◀───────────────────────────── │        (chat.py)         │
└─────────────────────┘   token-by-token stream        └───────────┬──────────────┘
                                                                     │
                                                                     ▼
                                                          ┌────────────────────┐
                                                          │   LangGraph Agent   │
                                                          │  (StateGraph loop)  │
                                                          └───┬───────────┬────┘
                                                              │           │
                                                    chatbot_node       tools node
                                                    (Gemini LLM)     (ToolNode)
                                                              │           │
                              ┌───────────────────────────────┘           │
                              │                                           │
                              ▼                                           ▼
                    ┌──────────────────┐                    ┌───────────────────────┐
                    │  Google Gemini   │                    │  order / product /     │
                    │  (flash-lite)    │                    │  ticket / policy tools │
                    └──────────────────┘                    └──────────┬────────────┘
                                                                        │
                                    ┌───────────────────────────────────┼───────────────┐
                                    ▼                                   ▼                ▼
                          ┌─────────────────┐              ┌─────────────────┐  ┌───────────────┐
                          │    Postgres      │              │     Pinecone     │  │  Postgres via  │
                          │ (business data:  │              │  (policy vector  │  │  psycopg_pool  │
                          │ orders, products,│              │     search)      │  │  (checkpointer:│
                          │    tickets)      │              └─────────────────┘  │ conversation +  │
                          └─────────────────┘                                    │ interrupt state)│
                                                                                  └───────────────┘
```

Two completely separate uses of Postgres are worth calling out up front,
because conflating them is a common point of confusion:

1. **Business data** (`orders`, `products`, `tickets` tables) — plain
   SQLAlchemy ORM, queried synchronously inside tool functions.
2. **LangGraph checkpointer** — a *different* mechanism (`AsyncPostgresSaver`)
   that persists the *agent's own execution state* (message history, and
   paused/interrupted graph state) keyed by `thread_id`. This is what makes
   multi-turn memory and the human-in-the-loop order confirmation possible.

---

## 2. The agent's "brain": LangGraph

### 2.1 Why LangGraph instead of just calling the LLM in a loop?

You *could* hand-roll a while-loop that calls Gemini, checks for tool calls,
executes them, and calls Gemini again. LangGraph gives you that same
ReAct-style loop, but as a **checkpointed state machine** — every step
persists to Postgres automatically. That's what buys you three things a
hand-rolled loop would need to reinvent:

- **Multi-turn memory** "for free" — resume a conversation by thread_id days
  later.
- **`interrupt()`** — pause execution mid-tool-call, hand control back to a
  human, and resume exactly where you left off (used for order confirmation).
- **Streaming primitives** (`stream_mode="messages"` / `"updates"`) that plug
  directly into token-by-token UI updates.

### 2.2 The graph itself (`app/graph/builder.py`)

```python
graph.add_node('chatbot_node', chatbot_node)
graph.add_node('tools', ToolNode(tools))

graph.add_edge(START, 'chatbot_node')
graph.add_conditional_edges('chatbot_node', tools_condition)
graph.add_edge('tools', 'chatbot_node')
```

This is a **2-node loop**:

- `chatbot_node` calls the LLM with the full message history.
- If the LLM's response contains tool calls, `tools_condition` (a LangGraph
  prebuilt) routes to the `tools` node, which executes them via `ToolNode`.
- `tools` routes back to `chatbot_node` so the model can see the tool
  results and either respond in plain text or call another tool.
- If the LLM's response has *no* tool calls, `tools_condition` routes to
  `END` instead.

This is the same "ReAct" (Reason + Act) pattern behind most tool-using
agents: think → act → observe → think again, until no more action is
needed.

### 2.3 State (`app/graph/state.py`)

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

`add_messages` is a **reducer**: LangGraph doesn't overwrite `messages` on
each node's return, it *appends* to it (and correctly merges streamed
chunks of the same message). This is what gives you conversation history
without manually managing a list.

### 2.4 `chatbot_node` — why `.astream()` and not `.ainvoke()`

```python
full_response = None
async for chunk in llm.astream(message_with_prompt, config):
    full_response = chunk if full_response is None else full_response + chunk
return {'messages': [full_response]}
```

**This is the single most important line in the whole backend to be able to
explain in an interview.** `llm.ainvoke()` blocks until the entire response
is generated, then returns it as one lump — no intermediate output ever
reaches LangGraph's streaming machinery. `llm.astream()` emits `AIMessageChunk`
objects as tokens are generated, and those chunks flow through to
`agent.astream(..., stream_mode="messages")` in the API layer, which is what
actually lets the frontend show a live typing effect instead of a big pause
followed by the whole answer at once.

Accumulating chunks with `+` works because LangChain's message chunk classes
implement `__add__` to merge partial tool-call arguments and text
concatenation correctly.

### 2.5 The `AIMessageChunk` vs `"ai"` gotcha

In `chat.py`'s streaming loop:
```python
if not isinstance(msg, AIMessageChunk) or not msg.content:
    continue
```
A subtle but important fact: a streamed chunk's `.type` attribute is the
literal string `"AIMessageChunk"`, **not** `"ai"` — `"ai"` is only the type
of a fully-formed, non-streaming `AIMessage`. Checking `msg.type != "ai"`
(an easy, natural-looking mistake) silently discards *every* streamed token,
and looks exactly like "streaming isn't working" from the outside, with no
error thrown anywhere. Using `isinstance(msg, AIMessageChunk)` is the correct,
version-robust check.

---

## 3. Streaming protocol (SSE) — `app/api/chat.py`

### 3.1 Why Server-Sent Events instead of WebSockets or plain JSON

The interaction is fundamentally **one request → one streamed response**,
not bidirectional real-time messaging. SSE is the right-sized tool: it's
just a long-lived HTTP response with `Content-Type: text/event-stream`,
each event formatted as `data: <json>\n\n`, and the browser's `fetch` +
`ReadableStream` API consumes it incrementally. No extra protocol, no
persistent duplex connection to manage.

### 3.2 The event vocabulary

Every response is a stream of these event types, terminated by `[DONE]`:

| Event | When it's sent | Purpose |
|---|---|---|
| `{"thread_id": "..."}` | Immediately, once per `/chat` call | Lets the frontend learn the conversation's ID on the very first turn |
| `{"chunk": "..."}` | Per streamed token from the LLM | The actual visible text, appended incrementally |
| `{"type": "confirmation_required", "payload": {...}}` | When the agent hits an `interrupt()` | Tells the frontend to render a confirmation card instead of text |
| `{"error": "..."}` | On any exception during the run | Surfaced without crashing the connection |
| `[DONE]` | Always, in a `finally` block | Tells the frontend the stream is over (success, error, or paused-on-interrupt) |

### 3.3 Dual `stream_mode` — how the interrupt event gets detected

```python
async for stream_mode, data in agent.astream(
    graph_input, config=config, stream_mode=["messages", "updates"]
):
```
Passing a **list** of stream modes makes LangGraph yield `(mode, data)`
tuples instead of raw data, multiplexing two different signal types onto
one stream:
- `"messages"` → the token-by-token `(AIMessageChunk, metadata)` pairs
  described above.
- `"updates"` → per-superstep state diffs. When the graph pauses on
  `interrupt()`, one of these updates is `{"__interrupt__": (Interrupt(...),)}`
  — `.value` on that object is exactly whatever was passed into `interrupt()`
  inside the tool. This is forwarded straight to the client.

### 3.4 Why a shared `_stream_agent()` helper

`/chat` (start a new turn) and `/chat/resume` (continue after a
confirmation) both need identical event-translation logic — only the input
to `agent.astream()` differs (a fresh state dict vs. a `Command(resume=...)`).
Factoring this into one generator avoids duplicating the messages/updates
handling in two places that would inevitably drift apart.

### 3.5 Response headers worth knowing why they're there

```python
"Cache-Control": "no-cache",
"Connection": "keep-alive",
"X-Accel-Buffering": "no",
```
The last one specifically disables **nginx's response buffering** if this
is ever deployed behind an nginx reverse proxy — without it, nginx can
buffer the entire streamed response before forwarding any of it to the
client, silently defeating streaming at the infra layer even though the
app code is correct.

---

## 4. Tools — the agent's "hands"

Every tool is a thin `@tool`-decorated function that delegates to a
**service** (business logic) which delegates to a **repository** (data
access). This is a deliberate layering:

```
tools/          -- LLM-facing interface: docstring = the tool's "API contract"
  ↓
services/       -- business rules (stock checks, atomic commits, error shaping)
  ↓
repositories/   -- raw SQL/ORM queries, no business logic
```

**Why layer it this way?** The tool's docstring is read by the LLM to decide
*when* to call it — that's prompt engineering, not code, and deserves to be
isolated from the actual DB logic. The service layer is where you'd add
business rules (e.g. "can't order more than stock") without touching either
the LLM-facing contract or the raw queries. The repository layer is pure
data access, swappable/testable independent of the other two.

### 4.1 `order_lookup(order_id)`
Straightforward read-only lookup by primary key.

### 4.2 `product_lookup(search_term)`
Fuzzy `ILIKE '%term%'` search, capped at 5 results — the cap exists
specifically **to avoid dumping an unbounded result set into the LLM's
context window**, which would waste tokens and could distract the model
into recommending irrelevant products.

### 4.3 `create_support_ticket(description)`
Straightforward create.

### 4.4 `policy_lookup(question)` — Retrieval-Augmented Generation (RAG)

```python
def search_policies(self, query: str, top_k: int = 5) -> list[str]:
    docs = self.vector_store.similarity_search(query, k=top_k)
    return [result.page_content for result in docs]
```

**Why RAG instead of just putting the policies in the system prompt?**
Two reasons: (1) it scales — a real company's policy handbook doesn't fit
in a context window, and (2) it grounds the model in retrieved text rather
than letting it improvise, which is enforced explicitly in the system
prompt: *"you MUST base your answer EXCLUSIVELY on the retrieved context...
if it doesn't contain the answer, do not guess."* This is the core
anti-hallucination mechanism of the whole project.

**How retrieval actually works:** `seed_policies.py` embeds a handful of
policy documents (return policy, warranty, shipping, escalation SLAs) via
`GoogleGenerativeAIEmbeddings` and upserts them into a Pinecone index.
`policy_lookup` embeds the user's question the same way and does a cosine
similarity search, returning the top-k most relevant chunks as plain text
for the LLM to read and paraphrase from.

**Why a module-level singleton for `PolicyRepository`:**
```python
_policy_repository: PolicyRepository | None = None
def get_policy_repository() -> PolicyRepository:
    global _policy_repository
    if _policy_repository is None:
        _policy_repository = PolicyRepository()
    return _policy_repository
```
Constructing `PolicyRepository()` creates an embeddings client *and* opens a
connection to a Pinecone index. Doing that fresh on every single policy
question adds real, avoidable latency to every RAG call. The singleton
builds it once, lazily, on first use.

### 4.5 `place_order(product_id, quantity)` — the human-in-the-loop tool

This is the most architecturally interesting piece of the project. Full
walkthrough in §5.

---

## 5. Human-in-the-loop order placement

### 5.1 The problem this solves

An agent that can autonomously execute an irreversible action (charging a
customer, writing an order, decrementing real inventory) on nothing but its
own judgment is a genuine production risk — a misread quantity or a
misunderstood intent becomes a real mistake with no chance to catch it.
LangGraph's `interrupt()` primitive exists specifically to put a human
checkpoint in front of exactly that class of action, without throwing away
the conversation's state while waiting.

### 5.2 What `interrupt()` actually does, mechanically

```python
decision = interrupt({
    "type": "order_confirmation",
    "product_id": product_id,
    "product_name": product["name"],
    "quantity": quantity,
    "unit_price": product["price"],
    "total_price": total_price,
})
```

Calling `interrupt(payload)` the first time inside a node **raises a special
`GraphInterrupt` exception internally**. LangGraph catches this, and instead
of crashing:
1. Persists the *entire* current graph state — including exactly which node
   was executing and what `payload` was passed — to the checkpointer
   (Postgres, via `AsyncPostgresSaver`).
2. Halts the graph run and returns control to the caller.
3. The caller (`chat.py`) sees this show up as a `__interrupt__` entry in the
   `"updates"` stream (§3.3) and forwards `payload` to the frontend.

Later, calling `agent.astream(Command(resume={"confirmed": True/False}), config=...)`
resumes the *exact same paused task*. This time, `interrupt()` doesn't
pause — it simply **returns the resume value** (`{"confirmed": ...}`) as if
it were a normal function call, and execution continues from that line.

### 5.3 The critical correctness rule: what's safe before vs. after `interrupt()`

> **"The graph resumes from the start of the node, re-executing all logic"**
> — this is documented LangGraph behavior, not a bug.

That means everything in `place_order` *above* the `interrupt()` call
(fetching current product info, checking stock) **re-runs from scratch**
every time the tool is resumed. This is why:
- Everything above `interrupt()` is deliberately **read-only** — safe to
  repeat any number of times.
- The actual write (`OrderService.place_order(...)`, which creates the order
  row and decrements stock) is placed **strictly after** the confirmation
  check, so it only ever executes once, and only after a real, confirmed
  resume.

Getting this ordering wrong (e.g. writing to the DB before the interrupt)
is the single most common mistake when implementing HITL flows with
LangGraph, and would cause a re-run on any retry/reconnect to duplicate
writes.

### 5.4 Atomic order creation

```python
order = order_repo.create_order(...)      # staged, not committed
product_repo.decrement_stock(...)         # staged, not committed
db_session.commit()                       # both succeed or both roll back
```

`create_order` and `decrement_stock` both stage their changes in the same
SQLAlchemy session without committing individually. `OrderService.place_order`
commits once, after both operations succeed. **Why this matters**: without
it, a crash between "order created" and "stock decremented" would leave the
database in an inconsistent state — an order exists for stock that was
never actually reserved. Wrapping both in one transaction guarantees they
happen together or not at all.

### 5.5 End-to-end walkthrough

1. User: *"I want to order 2 Pro Gaming Mice."*
2. Model calls `product_lookup("Pro Gaming Mouse")` → gets `PRD-001`.
3. Model calls `place_order(product_id="PRD-001", quantity=2)`.
4. Inside the tool: re-fetches product, checks stock, computes total,
   calls `interrupt(payload)` → graph pauses, state persisted to Postgres.
5. `/api/chat`'s SSE stream emits `{"type": "confirmation_required", "payload": {...}}`.
6. Frontend renders a `CONFIRM ORDER` card with Confirm/Cancel buttons
   (`message-list.tsx`).
7. User clicks Confirm → frontend calls `/api/chat/resume` with
   `{thread_id, confirmed: true}`.
8. Backend calls `agent.astream(Command(resume={"confirmed": true}), config=...)`.
9. `interrupt()` returns `{"confirmed": true}`; `OrderService.place_order`
   runs; order + stock decrement commit atomically.
10. Model streams its final answer: *"Your order ORD-XXXX has been placed..."*

### 5.6 Known limitation: abandoned interrupts

If a user opens a confirmation card and never responds, that thread stays
paused in Postgres indefinitely — there's no timeout. In production, you'd
want a background sweep that expires/cancels threads paused longer than
some threshold (e.g. 24h). Worth naming proactively in an interview as a
"what would you add next" answer.

---

## 6. Persistence layer — why the Postgres pool was rebuilt twice

This project went through two real, instructive failure modes worth being
able to narrate:

### 6.1 Failure 1: per-request pool creation

The original code created a *brand new* `AsyncPostgresSaver` connection pool
and ran `checkpointer.setup()` on **every single chat request**. Opening a
pool and running migration checks is expensive — this added real latency to
every message and was a symptom of not understanding that the checkpointer's
pool is meant to be a long-lived, app-scoped resource, not a per-request one.
**Fix**: build the pool once in FastAPI's `lifespan` context manager, store
the compiled graph on `app.state`, reuse it across all requests.

### 6.2 Failure 2: stale connections after idle periods

After the above fix, the app worked fine under active testing but started
failing instantly with `"the connection is closed"` after sitting idle for
a few hours. **Root cause**: `psycopg_pool` does not proactively check
whether pooled connections are still alive. If Postgres (or a managed DB
provider's idle-connection timeout) silently kills a connection, the pool
still hands it out on the next request — which then fails immediately.
**Fix**: build the `AsyncConnectionPool` explicitly instead of via
`AsyncPostgresSaver.from_conn_string()`, with:
- `check=AsyncConnectionPool.check_connection` — validates a connection is
  alive before handing it out, transparently replacing it if dead.
- `max_idle=300` — proactively recycles connections idle >5 minutes, before
  a typical server-side timeout would kill them anyway.
- `max_lifetime=1800` — recycles any connection after 30 minutes regardless
  of activity, as a second safety net.

### 6.3 Startup timeout + logging

```python
async with asyncio.timeout(DB_STARTUP_TIMEOUT_SECONDS):
    await pool.open()
    ...
```
Without an explicit timeout, a DB connectivity problem at startup manifests
as `uvicorn` hanging forever at `"Waiting for application startup."` with
zero diagnostic output. Wrapping startup in `asyncio.timeout` turns a silent
infinite hang into a clear, actionable `RuntimeError` (and specifically
flags the classic cause: pointing `DATABASE_URL` at a transaction-mode
connection pooler like PgBouncer, which doesn't support the prepared
statements `AsyncPostgresSaver` relies on).

---

## 7. Frontend architecture

### 7.1 Component tree
```
app/chat/page.tsx
  └── Header               -- static branding
  └── ChatContainer        -- owns all chat state + SSE consumption
        └── MessageList    -- renders messages + confirmation cards
        └── ChatInput      -- textarea + send button
```

### 7.2 Why `thread_id` is generated client-side, once, on mount

```tsx
const [threadId] = useState<string>(() => crypto.randomUUID())
```
Earlier versions initialized `threadId` to `''` and relied on the server's
response to populate it. But an **explicitly-provided empty string** is a
valid Pydantic field value — it doesn't trigger the backend's
`default_factory`. That meant *every new browser tab's first message* was
sent with `thread_id=""`, and since the checkpointer keys conversations by
thread_id, every first-ever message from every user landed in the **same
shared conversation** until the server handed back a real UUID. Generating
a real UUID client-side, once, up front, closes this entirely — it's a
correctness/privacy fix as much as a convenience.

### 7.3 SSE parsing: line buffering across reads

```tsx
buffer += decoder.decode(value, { stream: true })
const lines = buffer.split('\n')
buffer = lines.pop() ?? ''   // keep the possibly-incomplete last line
```
A single `data: {...}\n\n` event is not guaranteed to arrive in one
`reader.read()` call — it can be split across TCP packet boundaries. Naively
splitting each chunk on `'\n'` independently (an earlier, buggier version)
would occasionally truncate a JSON line mid-object, fail to parse, and
silently drop that piece of the response (caught and ignored as a
`SyntaxError`). Buffering the trailing incomplete line across reads and only
processing complete lines fixes this class of intermittent, hard-to-reproduce
data loss.

### 7.4 The typewriter effect — decoupling display speed from network speed

```tsx
function createTypewriter(setMessages, messageId) {
  let fullText = ''
  let revealedLength = 0
  ...
  const tick = () => {
    revealedLength = Math.min(revealedLength + CHARS_PER_FRAME, fullText.length)
    ...
    frameId = requestAnimationFrame(tick)
  }
}
```
**Why this exists**: for short replies, Gemini can generate the *entire*
response fast enough that all SSE chunks arrive within a handful of
milliseconds of each other — genuinely streaming at the network level, but
too fast for a human to perceive as "typing." Rather than depending on raw
chunk arrival timing for visual pacing (which varies wildly depending on
reply length and model latency), the real text is accumulated instantly into
`fullText`, and a `requestAnimationFrame` loop reveals it onto the screen at
a fixed, controllable rate (`CHARS_PER_FRAME`), continuing smoothly even
after the network stream has already finished. This is the same pattern
production chat UIs (ChatGPT, Claude, etc.) use — display pacing is a
deliberate UX choice, not an accident of network timing.

### 7.5 The confirmation card UI

When a `{"type": "confirmation_required", ...}` event arrives, instead of
appending to the current assistant message, a distinct message object is
pushed with a `confirmation` field. `MessageList` branches on this field to
render a bordered card with Confirm/Cancel buttons instead of a text bubble.
Clicking either calls `/api/chat/resume` and marks the card `resolved` so
the buttons disappear — reusing the exact same `consumeStream()` logic as a
fresh send, since both endpoints emit an identical event vocabulary.

---

## 8. Evaluation & benchmarking (`benchmark/benchmark.py`)

Why build this at all: an agent that "seems to work" in ad hoc manual
testing isn't the same as one with **measured, reproducible** correctness
and performance — and "I built an eval harness for my own agent" is a
meaningfully stronger interview answer than "I tested it by chatting with it."

- **Labeled task-success eval**: a fixed set of queries per tool category
  (order lookup, product lookup, policy RAG, ticket creation, and an
  out-of-scope guardrail check), each scored pass/fail by checking for
  expected/forbidden keywords in the final answer — a lightweight but
  legitimate automated regression check.
- **Latency/TTFT percentiles under concurrency**: p50/p95/p99 total latency
  and time-to-first-token, measured against the real running server, not
  estimated.
- **Multi-turn memory check**: verifies the checkpointer actually persists
  context (name + order ID) across two independent HTTP requests on the same
  thread_id.
- **Built-in rate limiter**: paces requests to stay under the Gemini free
  tier's RPM ceiling — without it, load-testing at any real concurrency
  causes a wave of `429`s that has nothing to do with your system's actual
  performance, and would produce misleading numbers.

**Honest caveat learned from actually running it**: on the free tier,
latency numbers reflect Google's request queue/deprioritization for
non-paying traffic at least as much as your own architecture. The
task-success-rate and multi-turn-memory results are unaffected by this and
are safe to state plainly; raw latency numbers are not, unless measured on
a paid tier.

---

## 9. Known limitations / what's *not* production-ready yet

Being able to name these unprompted is itself a good interview signal —
it shows you understand the difference between "works for a demo" and
"ready for real traffic."

1. **No authentication or authorization.** Anyone who finds the endpoint can
   use it, burn API quota, and create real DB writes.
2. **No rate limiting** on `/api/chat` itself (only the benchmark script
   rate-limits *itself* as a test client).
3. **`thread_id` trust**: any client can pass any `thread_id` and read/resume
   that conversation. Fine for a single-user demo; a real deployment needs
   thread ownership tied to an authenticated session.
4. **Abandoned interrupts never expire** (§5.6).
5. **No schema migration framework.** Adding the `product_id`/`quantity`/
   `total_price` columns to `orders` required a hand-written one-off script
   (`migration_001.py`) because `Base.metadata.create_all()` only creates
   missing tables, never alters existing ones. A real project would use
   Alembic.
6. **Sync SQLAlchemy inside an async app.** Tool functions do blocking DB
   calls; `ToolNode` runs sync tools in a thread pool so it doesn't freeze
   the event loop, but a fully async SQLAlchemy engine would be more
   consistent and scale better under real concurrency.
7. **Single free-tier Gemini API key** — real RPM/RPD limits, and
   deprioritized relative to paid traffic (directly observed during
   benchmarking, §8).
8. **No automated test suite / CI** beyond the manual benchmark script.

---

## 10. Local setup

**Backend:**
```bash
cd ai-service
pip install -r requirements.txt
# .env needs: DATABASE_URL, GOOGLE_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME, ALLOWED_ORIGINS
python seed_db.py               # creates tables + demo orders/products
python migration_001.py         # adds order_id/quantity/total_price columns (one-time)
python seed_policies.py         # embeds and uploads policy docs to Pinecone
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
# .env.local needs: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

**Benchmark:**
```bash
cd benchmark
pip install httpx --break-system-packages
python benchmark.py --concurrency 1 --requests 8 --max-rpm 6
```

---

## 11. Likely interview questions and how to answer them

**"Walk me through what happens when a user sends a message."**
→ Use §5.5's numbered walkthrough (adapt to a non-ordering example if
they want the simpler path: HumanMessage in, `chatbot_node` streams via
`llm.astream()`, tool call detected by `tools_condition`, routed to
`ToolNode`, result appended to state, back to `chatbot_node`, final answer
streamed out as `AIMessageChunk`s via SSE).

**"Why LangGraph instead of a plain LangChain agent or your own loop?"**
→ Checkpointed persistence is the deciding feature — it's what makes both
multi-turn memory *and* the HITL interrupt possible with a handful of lines,
instead of hand-building a state-persistence layer yourself.

**"What was the hardest bug you hit?"**
→ The `AIMessageChunk` vs `"ai"` type-string mismatch (§2.5) is a great
answer: it's subtle, version-specific, silent (no error, no crash — just
nothing streams), and required actually reading LangChain's message class
hierarchy to find.

**"How do you keep the agent from hallucinating policies?"**
→ RAG + an explicit system-prompt constraint to answer *exclusively* from
retrieved context, with an instruction to say "I don't know" and offer a
support ticket rather than guess (§4.4).

**"How do you handle an action that shouldn't happen without human review?"**
→ The full `interrupt()`/`Command(resume=...)` explanation in §5, including
the "re-runs from the top" gotcha and why the write happens strictly after
the confirmation check.

**"What would you change before shipping this to real users?"**
→ Straight to §9 — auth, thread ownership, rate limiting, interrupt TTL,
Alembic migrations, async DB layer.

---

## 12. Resume bullets (ATS-friendly)

> **AI Customer Support Agent** — FastAPI · LangGraph · Google Gemini · PostgreSQL · Pinecone · Next.js
> - Architected a full-stack agentic support platform using FastAPI and LangGraph, orchestrating a multi-tool ReAct agent (order lookup, product search, RAG-based policy retrieval, ticket escalation, order placement) with PostgreSQL-backed conversation state persisted across sessions.
> - Implemented a human-in-the-loop order-placement flow using LangGraph's interrupt()/Command(resume=...) primitives, pausing agent execution mid-tool-call to require explicit user confirmation before any state-mutating action, with atomic order creation and inventory decrement.
> - Built token-level response streaming end-to-end over Server-Sent Events (FastAPI to Next.js), diagnosing and resolving production reliability issues including stale connection-pool handling, message-stream type-filtering bugs, and SSE line-buffering data loss.
> - Designed and ran a labeled evaluation harness measuring task success rate across five intent categories and multi-turn memory retention, achieving a 100% automated pass rate on regression tests.

Swap in real latency/throughput numbers from a paid-tier benchmark run if
you get them (§8) — otherwise these four stand on their own without needing
a contestable performance claim.
