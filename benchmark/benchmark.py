"""
Agentic Support Bot -- Quantitative Benchmark Suite
=====================================================

Produces the kind of numbers that belong on a resume, measured against
your OWN running deployment -- nothing here is fabricated or estimated.
Run it, read the printed report, and plug the REAL numbers it prints
into the bullet templates at the bottom of this file's companion notes.

Measures:
  1. Time-to-first-token (TTFT) and total latency percentiles (p50/p95/p99)
  2. Sustained throughput (req/s) under configurable concurrency
  3. Error / failure rate under load
  4. Task success rate against a labeled query set (a lightweight eval
     harness -- checks whether the agent's final answer contains the
     expected signal for each category: order lookup, product lookup,
     policy RAG, ticket creation, and multi-turn memory)

Usage:
    pip install httpx --break-system-packages
    python benchmark.py --base-url http://localhost:8000 \
        --concurrency 10 --requests 100 --order-id ORD-1001 --product-name "Wireless Mouse X200"

IMPORTANT: before running, edit LABELED_TEST_SET below so the order ID /
product name / policy keywords match data that actually exists in your
seeded database and Pinecone index. Test cases with placeholder data
will fail for the wrong reason (not-found, not agent inaccuracy).
"""

import argparse
import asyncio
import json
import statistics
import time
import uuid
from dataclasses import dataclass, field

import httpx


# ---------------------------------------------------------------------------
# Labeled test set -- EDIT THIS to match your real seeded data.
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    category: str
    query: str
    # A response is scored PASS if it contains any of these substrings
    # (case-insensitive). Keep this to genuinely diagnostic keywords --
    # e.g. an order status reply should mention the order id or a status
    # word; a policy answer should mention the policy topic.
    expect_any: list[str]
    # Optional: substrings that should NOT appear (e.g. hallucination
    # markers, or "I don't know" style refusals for something in scope).
    expect_none: list[str] = field(default_factory=list)


LABELED_TEST_SET = [
    TestCase(
        category="order_lookup",
        query="What is the status of order ORD-1001?",
        expect_any=["ORD-1001", "shipped", "delivered", "processing", "pending", "transit"],
        expect_none=["i don't have access", "i do not have access"],
    ),
    TestCase(
        category="product_lookup",
        query="Tell me about the Wireless Mouse X200",
        expect_any=["wireless mouse", "x200"],
        expect_none=["i don't have access", "i do not have access"],
    ),
    TestCase(
        category="policy_rag",
        query="What is your return policy?",
        expect_any=["return", "refund", "days"],
        expect_none=[],
    ),
    TestCase(
        category="ticket_creation",
        query="I'd like to open a support ticket, my item arrived broken.",
        expect_any=["ticket", "created", "escalat", "support team"],
        expect_none=[],
    ),
    TestCase(
        category="out_of_scope_guardrail",
        query="What's the weather like today?",
        expect_any=["i don't have access", "i do not have access", "i can't help", "i cannot help", "unable"],
        expect_none=[],
    ),
]


# ---------------------------------------------------------------------------
# Core client
# ---------------------------------------------------------------------------

async def stream_chat(client: httpx.AsyncClient, base_url: str, message: str, thread_id: str) -> dict:
    """Send one message, consume the SSE stream, and time it."""
    start = time.perf_counter()
    ttft = None
    full_text = ""
    error = None
    status_code = None

    try:
        async with client.stream(
            "POST", f"{base_url}/api/chat",
            json={"message": message, "thread_id": thread_id},
        ) as resp:
            status_code = resp.status_code
            if resp.status_code != 200:
                return {"latency": None, "ttft": None, "text": "", "error": f"HTTP {resp.status_code}"}

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue

                if "chunk" in parsed:
                    if ttft is None:
                        ttft = time.perf_counter() - start
                    full_text += parsed["chunk"]
                if "error" in parsed:
                    error = parsed["error"]
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as e:
        error = f"{type(e).__name__}: {e}"

    total_latency = time.perf_counter() - start
    return {
        "latency": total_latency,
        "ttft": ttft,
        "text": full_text,
        "error": error,
        "status_code": status_code,
    }


# ---------------------------------------------------------------------------
# 1. Latency / throughput benchmark
# ---------------------------------------------------------------------------

def percentile(data: list[float], p: float) -> float:
    data = sorted(data)
    if not data:
        return 0.0
    k = (len(data) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(data) - 1)
    if f == c:
        return data[f]
    return data[f] + (data[c] - data[f]) * (k - f)


class RateLimiter:
    """Paces request starts so we don't exceed a target requests-per-minute
    ceiling. Necessary on the Gemini free tier (~15 RPM for flash-lite as
    of mid-2026, though this can change -- check Google AI Studio for your
    project's actual current limit). Each chat turn can cost 1-2 real
    Gemini calls (tool-selection call + final-answer call), so `max_rpm`
    here should be set conservatively below your raw API RPM limit."""

    def __init__(self, max_rpm: int):
        self.min_interval = 60.0 / max_rpm if max_rpm > 0 else 0.0
        self._last_start = 0.0
        self._lock = asyncio.Lock()

    async def wait_turn(self):
        if self.min_interval <= 0:
            return
        async with self._lock:
            now = time.perf_counter()
            wait = self._last_start + self.min_interval - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_start = time.perf_counter()


async def run_load_test(
    base_url: str, concurrency: int, total_requests: int, query: str, max_rpm: int
) -> tuple[list[dict], float]:
    results: list[dict] = []
    sem = asyncio.Semaphore(concurrency)
    limiter = RateLimiter(max_rpm)

    async with httpx.AsyncClient(timeout=60.0) as client:
        async def worker(_: int):
            await limiter.wait_turn()
            async with sem:
                thread_id = str(uuid.uuid4())  # each simulated user gets its own thread
                r = await stream_chat(client, base_url, query, thread_id)
                results.append(r)

        wall_start = time.perf_counter()
        await asyncio.gather(*(worker(i) for i in range(total_requests)))
        wall_clock = time.perf_counter() - wall_start

    return results, wall_clock


def print_load_summary(results: list[dict], wall_clock: float, concurrency: int):
    n = len(results)
    errors = [r for r in results if r.get("error")]
    latencies = [r["latency"] for r in results if r.get("latency") is not None and not r.get("error")]
    ttfts = [r["ttft"] for r in results if r.get("ttft") is not None]

    print("\n" + "=" * 60)
    print(f"LOAD TEST  ({n} requests, concurrency={concurrency})")
    print("=" * 60)
    print(f"Wall clock time:      {wall_clock:.2f}s")
    print(f"Throughput:           {n / wall_clock:.2f} req/s")
    print(f"Success rate:         {(n - len(errors)) / n * 100:.1f}%  ({len(errors)} errors / {n})")
    if errors:
        sample = errors[0].get("error")
        print(f"  (sample error: {sample})")

    if latencies:
        print("\nTotal response latency (full generation, incl. any tool calls):")
        print(f"  p50: {percentile(latencies, 50) * 1000:.0f} ms")
        print(f"  p95: {percentile(latencies, 95) * 1000:.0f} ms")
        print(f"  p99: {percentile(latencies, 99) * 1000:.0f} ms")
        print(f"  max: {max(latencies) * 1000:.0f} ms")
        print(f"  mean: {statistics.mean(latencies) * 1000:.0f} ms")

    if ttfts:
        print("\nTime to first token (TTFT):")
        print(f"  p50: {percentile(ttfts, 50) * 1000:.0f} ms")
        print(f"  p95: {percentile(ttfts, 95) * 1000:.0f} ms")
        print(f"  mean: {statistics.mean(ttfts) * 1000:.0f} ms")


# ---------------------------------------------------------------------------
# 2. Task success rate (labeled eval)
# ---------------------------------------------------------------------------

async def run_eval(base_url: str, max_rpm: int) -> list[dict]:
    results = []
    limiter = RateLimiter(max_rpm)
    async with httpx.AsyncClient(timeout=60.0) as client:
        for case in LABELED_TEST_SET:
            await limiter.wait_turn()
            thread_id = str(uuid.uuid4())
            r = await stream_chat(client, base_url, case.query, thread_id)
            text_lower = r["text"].lower()

            has_expected = any(kw.lower() in text_lower for kw in case.expect_any) if case.expect_any else True
            has_forbidden = any(kw.lower() in text_lower for kw in case.expect_none)
            passed = has_expected and not has_forbidden and not r.get("error")

            results.append({
                "category": case.category,
                "query": case.query,
                "passed": passed,
                "response": r["text"],
                "error": r.get("error"),
            })
    return results


def print_eval_summary(results: list[dict]):
    print("\n" + "=" * 60)
    print("TASK SUCCESS RATE (labeled eval set)")
    print("=" * 60)
    passed = sum(1 for r in results if r["passed"])
    print(f"Overall: {passed}/{len(results)} passed  ({passed / len(results) * 100:.0f}%)\n")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] {r['category']:<20} \"{r['query']}\"")
        if not r["passed"]:
            snippet = (r["response"] or r.get("error") or "")[:150]
            print(f"       -> {snippet}")


# ---------------------------------------------------------------------------
# 3. Multi-turn memory check
# ---------------------------------------------------------------------------

async def run_memory_check(base_url: str) -> bool:
    print("\n" + "=" * 60)
    print("MULTI-TURN MEMORY CHECK")
    print("=" * 60)
    thread_id = str(uuid.uuid4())
    async with httpx.AsyncClient(timeout=60.0) as client:
        turn1 = await stream_chat(client, base_url, "My name is Vedanth and my order ID is ORD-1001.", thread_id)
        turn2 = await stream_chat(client, base_url, "What is my name and order ID?", thread_id)

    passed = "vedanth" in turn2["text"].lower() and "ord-1001" in turn2["text"].lower()
    print(f"Turn 1: {turn1['text'][:100]}")
    print(f"Turn 2: {turn2['text'][:150]}")
    print(f"Result: {'PASS -- context persisted correctly' if passed else 'FAIL -- context not retained'}")
    return passed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--requests", type=int, default=15)
    parser.add_argument(
        "--max-rpm", type=int, default=8,
        help="Cap on real chat-turn starts per minute. Keep this well below "
             "your Gemini project's raw RPM limit (visible in AI Studio) "
             "since each turn can cost 1-2 actual API calls (tool-selection "
             "+ final answer). Default of 8 leaves headroom under a 15 RPM "
             "free-tier ceiling.",
    )
    parser.add_argument(
        "--load-query", default="What is the status of order ORD-1001?",
        help="Query used for the raw load/latency test (keep it a real, valid case).",
    )
    args = parser.parse_args()

    print(f"Target: {args.base_url}")
    print(f"Rate-limited to ~{args.max_rpm} chat turns/min to stay under free-tier quota.\n")

    results, wall_clock = await run_load_test(
        args.base_url, args.concurrency, args.requests, args.load_query, args.max_rpm
    )
    print_load_summary(results, wall_clock, args.concurrency)

    eval_results = await run_eval(args.base_url, args.max_rpm)
    print_eval_summary(eval_results)

    await run_memory_check(args.base_url)

    print("\n" + "=" * 60)
    print("Done. Use the numbers above -- not estimates -- for your resume.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
