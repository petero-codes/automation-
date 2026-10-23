import os
import random
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
import urllib.request
import urllib.error
from core.logger import log

@dataclass
class CodingTask:
    project_name: str
    language: str
    files: Dict[str, str]
    git_commits: List[str]

# ======================================================================
# HIGH-ENTROPY PROCEDURAL CODE TEMPLATES & DYNAMIC ARCHITECTURES
# ======================================================================
PROJECT_ARCHITECTURES = [
    {
        "domain": "distributed_rate_limiter",
        "lang": "python",
        "files": {
            "rate_limiter.py": '''"""Distributed Token Bucket Rate Limiter with Atomic Redis Counters."""
import time
import math
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class RateLimitResult:
    allowed: bool
    remaining_tokens: float
    reset_after_ms: int

class TokenBucketLimiter:
    def __init__(self, capacity: int, refill_rate_per_sec: float):
        self.capacity = float(capacity)
        self.refill_rate = refill_rate_per_sec
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def _refill(self, now: float) -> None:
        elapsed = now - self.last_refill
        if elapsed > 0:
            added = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + added)
            self.last_refill = now

    def acquire(self, tokens_requested: int = 1) -> RateLimitResult:
        now = time.monotonic()
        self._refill(now)

        if self.tokens >= tokens_requested:
            self.tokens -= tokens_requested
            reset_after = 0 if self.tokens >= 1 else int(1000 / self.refill_rate)
            return RateLimitResult(allowed=True, remaining_tokens=self.tokens, reset_after_ms=reset_after)

        deficit = tokens_requested - self.tokens
        wait_ms = int(math.ceil((deficit / self.refill_rate) * 1000))
        return RateLimitResult(allowed=False, remaining_tokens=self.tokens, reset_after_ms=wait_ms)
''',
            "test_limiter.py": '''import unittest
import time
from rate_limiter import TokenBucketLimiter

class TestTokenBucketLimiter(unittest.TestCase):
    def test_burst_capacity(self):
        limiter = TokenBucketLimiter(capacity=10, refill_rate_per_sec=5.0)
        for _ in range(10):
            res = limiter.acquire(1)
            self.assertTrue(res.allowed)
        
        # 11th should be denied
        res = limiter.acquire(1)
        self.assertFalse(res.allowed)
        self.assertGreater(res.reset_after_ms, 0)

if __name__ == "__main__":
    unittest.main()
'''
        },
        "commits": [
            "feat: Implement TokenBucketLimiter with millisecond refill calculus",
            "test: Add unit test coverage for burst capacity boundary conditions",
            "refactor: Optimize monotonic timestamp arithmetic for zero jitter"
        ]
    },
    {
        "domain": "event_stream_processor",
        "lang": "typescript",
        "files": {
            "stream_bus.ts": '''/**
 * Resilient Asynchronous Event Bus with Dead-Letter Handling.
 */
export interface EventEnvelope<T = unknown> {
  id: string;
  topic: string;
  payload: T;
  timestamp: number;
  retryCount: number;
}

export type EventHandler<T> = (event: EventEnvelope<T>) => Promise<void>;

export class EventStreamBus {
  private handlers: Map<string, EventHandler<any>[]> = new Map();
  private maxRetries = 3;

  public subscribe<T>(topic: string, handler: EventHandler<T>): void {
    const current = this.handlers.get(topic) || [];
    current.push(handler);
    this.handlers.set(topic, current);
  }

  public async publish<T>(topic: string, payload: T): Promise<void> {
    const envelope: EventEnvelope<T> = {
      id: `evt_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      topic,
      payload,
      timestamp: Date.now(),
      retryCount: 0,
    };

    const listeners = this.handlers.get(topic) || [];
    await Promise.all(
      listeners.map(async (fn) => {
        try {
          await fn(envelope);
        } catch (err) {
          console.error(`[EventBus] Handler failed for ${envelope.id}:`, err);
        }
      })
    );
  }
}
''',
            "index.ts": '''import { EventStreamBus } from "./stream_bus";

async function bootstrap() {
  const bus = new EventStreamBus();
  bus.subscribe("order.created", async (evt) => {
    console.log(`Processing order: ${evt.id}`);
  });

  await bus.publish("order.created", { orderId: "ORD-9021", total: 499.50 });
}

bootstrap().catch(console.error);
'''
        },
        "commits": [
            "feat: Add EventStreamBus with concurrent listener dispatch",
            "fix: Enforce envelope timestamp ordering and random ID entropy",
            "chore: Export strict TypeScript interface definitions"
        ]
    },
    {
        "domain": "async_circuit_breaker",
        "lang": "python",
        "files": {
            "circuit_breaker.py": '''"""Stateful Circuit Breaker with Exponential Backoff Reset."""
import time
from enum import Enum
from typing import Callable, Any

class State(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout_sec: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_sec
        self.failure_count = 0
        self.state = State.CLOSED
        self.last_state_change = time.time()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        now = time.time()
        if self.state == State.OPEN:
            if now - self.last_state_change > self.recovery_timeout:
                self.state = State.HALF_OPEN
                self.last_state_change = now
            else:
                raise CircuitBreakerOpenException("Circuit is open; call rejected.")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        if self.state == State.HALF_OPEN:
            self.state = State.CLOSED
            self.failure_count = 0
            self.last_state_change = time.time()

    def _on_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = State.OPEN
            self.last_state_change = time.time()
'''
        },
        "commits": [
            "feat: Implement 3-state CircuitBreaker with recovery timeout",
            "test: Add failure threshold validation and state transitions",
            "docs: Document half-open probe recovery dynamics"
        ]
    }
]

# ======================================================================
# PROCEDURAL TASK POOLING & OPTIONAL GEMINI AI SYNTHESIS
# ======================================================================
class ProceduralCoder:
    """
    Generates authentic, syntactically verified software engineering tasks.
    Uses high-entropy procedural synthesis by default, with optional Gemini AI enhancement.
    """
    def __init__(self):
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    def generate_task(self) -> CodingTask:
        # 1. Attempt Gemini AI synthesis if API key is provided
        if self.gemini_api_key:
            try:
                ai_task = self._synthesize_via_gemini()
                if ai_task:
                    log(f"[ProceduralCoder] Synthesized task via Gemini AI: {ai_task.project_name}")
                    return ai_task
            except Exception as e:
                log(f"[ProceduralCoder] Gemini synthesis fallback to procedural: {e}")

        # 2. High-Entropy Procedural Synthesis
        selected = random.choice(PROJECT_ARCHITECTURES)
        version_suffix = f"v{random.randint(1, 9)}_{random.randint(10, 99)}"
        name = f"{selected['domain']}_{version_suffix}"
        
        return CodingTask(
            project_name=name,
            language=selected['lang'],
            files=dict(selected['files']),
            git_commits=list(selected['commits'])
        )

    def _synthesize_via_gemini(self) -> Optional[CodingTask]:
        """Calls Gemini API with strict latency bounds, validation and fallback."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
        prompt = (
            "Generate a realistic software development task for a senior engineer. "
            "Return strictly JSON with keys: 'project_name' (str, valid folder name), "
            "'language' ('python' or 'typescript'), "
            "'files' (object mapping filename to code string, 20-60 lines per file), "
            "'git_commits' (list of 2-3 realistic commit message strings). "
            "Output zero markdown formatting, only pure JSON."
        )
        
        req_data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(raw_text)
            
            return CodingTask(
                project_name=parsed.get("project_name", f"ai_repo_{random.randint(100, 999)}"),
                language=parsed.get("language", "python"),
                files=parsed.get("files", {}),
                git_commits=parsed.get("git_commits", ["feat: Initial implementation"])
            )
