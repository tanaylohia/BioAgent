# Plan.md – Unified Implementation Blueprint

Tanay, this markdown file condenses everything we have discussed into a single, build‑ready plan: purpose, goals, architecture, component stack, libraries, and rollout milestones. One point per heading, as requested.

---

## 1. Goal

Deliver a modular, FastAPI‑based agent system that turns a user query into validated gene‑level insights by orchestrating 60‑70+ MCP‑exposed bio tools with traceable reasoning, low latency, and hot‑pluggable extensibility.

---

## 2. Architectural Pattern

- **Micro‑service mesh** of agent services (Planner, Dump, Hypothesis, Validation, Executor, Analysis) orchestrated by a **FastAPI Orchestrator**.
- **Event‑bus** backbone (Redis Streams or NATS JetStream) for non‑blocking artifact flow.
- **OpenAI Agents SDK + ToolRegistry + MCP extension** as the runtime layer for tool discovery, schema validation, and execution.
- **Object store + Postgres** for immutable artifacts and lineage metadata.

---

## 3. Service Components

1. **orchestrator\_service** – entrypoint, task lifecycle, tool hot‑reload.
2. **web\_planner\_service** – deep Think → ResearchPlan (LLM + prompts).
3. **research\_dump\_service** – high‑recall search, doc normalization.
4. **hypothesis\_service** – mining, clustering, confidence scoring.
5. **gene\_validation\_planner\_service** – maps hypotheses → tools.
6. **tool\_executor\_service** – async MCP calls, caching, retries.
7. **analysis\_service** – integrates evidence → AnalysisReport.
8. **response\_composer\_service** – formats user output.

Each is its own FastAPI app with `/run` and `/healthz` routes.

---

## 4. Data & Artifact Schemas (Pydantic)

| Model              | Key Fields                                  |
| ------------------ | ------------------------------------------- |
| `TaskSpec`         | id, user\_query, constraints                |
| `ResearchPlan`     | goals[], query\_templates[], depth\_params  |
| `ResearchDump`     | doc\_manifest\_url, embedding\_store\_ref   |
| `HypothesisSet`    | hypotheses[], evidence\_refs[], confidence  |
| `ValidationPlan`   | hypothesis\_id, tool\_sequence[], bindings  |
| `ToolResultBundle` | call\_id, status, payload, provenance       |
| `AnalysisReport`   | findings[], next\_steps, confidence\_matrix |

Artifact JSON is versioned and written to S3/GCS; Postgres stores pointers & metadata.

---

## 5. Libraries & Frameworks

- **FastAPI** – HTTP micro‑services.
- **Pydantic v2** – strict schema enforcement.
- **openai‑agents‑python** – Agent abstraction, tracing.
- **openai‑agents‑mcp** – MCP tool integration.
- **Redis Streams** (or **NATS JetStream**) – message bus.
- **SQLAlchemy** + **Postgres** – metadata persistence.
- **Boto3 / Google‑cloud‑storage** – object store client.
- **Sentence‑Transformers** – tool & doc embeddings.
- **LangChain‑TextSplit** or **tiktoken** – chunking.
- **Prometheus + Grafana** – metrics dashboard.
- **OpenTelemetry** – distributed tracing.
- **Docker + Kubernetes** – packaging & autoscale.
- **GitHub Actions** – CI/CD pipeline.

---

## 6. Control Flow (Condensed)

1. `POST /task` → Orchestrator ↳ Streams `TaskSpec`.
2. Planner picks up → writes `ResearchPlan` → stream.
3. Dump worker fetches corpus → emits `ResearchDump`.
4. Hypothesis Synth consumes dump → `HypothesisSet`.
5. Gene Validation Planner queries ToolRegistry → `ValidationPlan`.
6. Executor batches MCP calls → `ToolResultBundle`.
7. Analysis ingests all → `AnalysisReport`.
8. Composer formats and notifies user.

---

## 7. ToolRegistry Integration Steps

1. **Startup**: Orchestrator scans `tools/*.plugin.json` and registers with `ToolRegistry.register_from_mcp()`.
2. **Planner**: calls `registry.nearest_tools(query,k)` → embeds only top‑K schemas into LLM context.
3. **Executor**: uses `registry.execute_tools(batch, parallel=True)`; caching layer keyed on `(tool_id,args_hash)`.
4. **Hot Reload**: `POST /reload_tools` triggers `registry.refresh()` without downtime.

---

## 8. Security & Governance

- Secrets via **Vault** or **AWS Secrets Manager**.
- Signed artifact hashes for tamper detection.
- Per‑tool data classification; denylist PII egress.
- RBAC on FastAPI endpoints using JWT (Auth0 / Cognito).

---

## 9. Observability

- **Middleware** adds `trace_id`, `task_id`, `user_id` to every log.
- **Prometheus** scraping `/metrics` from each service.
- **Grafana dashboards**: token usage, MCP latency, hypothesis yield.
- **Agents SDK tracing UI** for prompt+tool call inspection.

---

## 10. Deployment Modes

- **Local dev**: `docker‑compose up`, uses local Redis and MinIO.
- **Staging**: Kubernetes (EKS/GKE), small autoscale, separate Redis.
- **Prod**: High‑availability Redis/NATS, S3/GCS, horizontal pod autoscale, Cloud NAT for MCP calls.

---

## 11. Incremental Milestones

1. **M0** – Repo skeleton, Pydantic models, CI checks.
2. **M1** – Orchestrator + Redis Streams + `POST /task` stub.
3. **M2** – MVP Planner → generates 5 search queries.
4. **M3** – ResearchDump service fetches docs into S3.
5. **M4** – ToolRegistry boot with 3 sample MCP tools.
6. **M5** – Executor fan‑out, cache, retry.
7. **M6** – End‑to‑end slice validates one hypothesis.
8. **M7** – Observability, security hardening.
9. **M8** – Scale to 70 tools, performance tuning.

---

## 12. Open Questions

- Choose **Redis vs NATS**? (feature vs ops burden).
- Preferred **LLM provider** (OpenAI vs local model).
- Which **object store** (S3 vs GCS) aligns with infra.

---

## 13. OpenAI Agents SDK – Core Function Reference

Below is a concise cheat‑sheet of **all the OpenAI Agents SDK primitives we will rely on**. Keep this as your single source when wiring services – no other orchestration frameworks are referenced.

| Category                | Function / Class                  | Purpose                                                               | Notes                                                         |
| ----------------------- | --------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------- |
| **Tool declaration**    | `@function_tool`                  | Wrap a local Python function as a callable tool                       | Auto‑generates JSON schema from type hints & docstring        |
|                         | `mcp_tool(server,name)`           | Register one endpoint of a remote MCP server as a tool                | Requires `openai‑agents‑mcp` extension                        |
| **MCP helper**          | `MCPServerStreamableHttp(url)`    | Describes a Streamable‑HTTP MCP server (exposes `/schema`, `/invoke`) | Use for all bio‑tools hosted in your VPC                      |
| **Agent core**          | `Agent(...)`                      | Create an agent with `name`, `model`, `instructions`, `tools`, etc    | Model can be OpenAI or any chat‑completion‑compatible backend |
| **Execution**           | `Runner(agent)`                   | Wraps retry, streaming, and tool‑call parsing                         | Instantiate once per service                                  |
|                         | `Runner.run_sync(prompt, **opts)` | Blocking call → `RunResult`                                           | Use in ordinary FastAPI endpoints                             |
|                         | `Runner.run(prompt)`              | Async coroutine version                                               | Use inside async worker tasks                                 |
|                         | `Runner.run_streamed()`           | Streams tokens & tool events                                          | Good for websocket progress updates                           |
| **Run result**          | `RunResult.response`              | Final text/string reply                                               |                                                               |
|                         | `RunResult.tool_calls`            | List of each call: id, args, output                                   | Feed into provenance logs                                     |
|                         | `RunResult.usage`                 | token counts                                                          | Cost accounting                                               |
| **Sessions / memory**   | `Session(agent)`                  | Maintains conversational history                                      | Persist `session.history` if you need long‑running context    |
| **Low‑level tool exec** | `tool.run_sync(**kwargs)`         | Directly invoke a tool without the LLM                                | Executor service uses this when arguments are pre‑validated   |
| **Tracing**             | CLI `agents trace serve`          | Launch local trace dashboard                                          | Inspect prompts, calls, latency                               |
|                         | `agents.trace.get_trace(id)`      | Fetch trace programmatically                                          | Pipe into observability pipeline                              |
| **Fine‑tuning utils**   | `agents.ft.export_trace(id,path)` | Convert trace into FT dataset                                         | Optional, for model iteration                                 |

### Minimal usage pattern inside a FastAPI micro‑service

```python
from fastapi import APIRouter
from agents import Agent, Runner, function_tool
from agents_mcp import MCPServerStreamableHttp, mcp_tool

router = APIRouter()

# 1. Register tools
server = MCPServerStreamableHttp("http://gene-align:8080")
align_tool = mcp_tool(server, name="align_gene_seq")

@function_tool
def is_ortholog(seq_a: str, seq_b: str) -> bool:
    """Return True if sequences are orthologs using a simple heuristic."""
    # ...implementation...

# 2. Build agent and runner
agent = Agent(
    name="GeneValidator",
    model="gpt-4o-mini",
    instructions="Validate gene–trait hypotheses using registered tools.",
    tools=[align_tool, is_ortholog],
    temperature=0.0,
)
runner = Runner(agent)

# 3. FastAPI endpoint
@router.post("/run")
async def run(payload: dict):
    prompt = payload["prompt"]
    result = await runner.run(prompt)
    return {
        "response": result.response,
        "tool_calls": result.tool_calls,
        "usage": result.usage,
    }
```

This pattern is repeated in each service (Planner, Validation, Analysis) with service‑specific instructions and tool lists.

---

##
