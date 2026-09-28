# CMN-C1-171 — Design Specification

**Template ID**: CMN-C1-171
**Title**: Enterprise Agent Skill Routing & Task Classification Agent
**Category**: Cat 1 (single technical capability)
**Industry**: CMN
**L1 Base type**: `AgentBaseGraph` (L1 direct). Follows the VectorRAG pattern as a reference
only, NOT as an inheritance target.

---

## 1. Purpose

Route a natural-language enterprise request to the right AGENTIC STAR template. The structured
result carries `template_id`, `confidence`, `rationale` and `top_candidates`; the caller is handed
readable text, since a rendered dict shows an id beside a confidence of 0.0 with equal weight and
reads as a recommendation whatever the number says.

Certainty decides the shape of the answer. Above the threshold it names one template. Below it, the
matches are listed as a shortlist that is explicitly not a recommendation. With nothing matched, it
says so and asks for a fuller description — it never names a template the catalog did not support.

`confidence` measures two things together: how much of the request the top match rests on
(**evidence**), and how clearly it beats the runner-up (**separation**). Both are needed. Sharing out
the total score — the earlier measure — handed a lone one-word match the entire mass and returned
1.0, the strongest claim available from the weakest evidence.

## 2. Architecture — Cat 1 (flat AgentBaseGraph backbone)

```
initialize -> pre_process (QueryNormalize) -> main (TemplateKBRetrieve + IntentClassify + RoutingRecommend) -> post_process (ResponseGenerate + ResponseValidate S-3) -> finalize
```

The 6 logical steps of the workflow map onto the fixed 3-slot Cat 1 backbone +
service layer (single technical capability, no inner subgraph):

- `pre_process` = QueryNormalize
- `main` = TemplateKBRetrieve + IntentClassify + RoutingRecommend (via `src/services/`)
- `post_process` = ResponseGenerate + ResponseValidate (S-3 membership gate)

## 3. State schema (`src/schemas/state.py` - `class State(AgentState)`)

Flat TypedDict extending `AgentState`. Agent-specific fields (no credentials, no Pydantic):

| Field | Type | Written by |
|---|---|---|
| `normalized_query` | `str` | pre_process |
| `candidates` | `list[dict]` `{template_id, industry, pattern, description, score}` | main |
| `intent` | `dict` `{industry, pattern, confidence}` | main |
| `routing_recommendation` | `dict` `{template_id, confidence, rationale, top_candidates[]}` | main |
| `catalog_kb_version` | `str` | main |

## 4. Nodes & services

| Component | Slot | Key logic | Output |
|---|---|---|---|
| `QueryNormalizeNode` | pre_process | S-1/S-2 input guard: empty reject, whitespace collapse, 2000-char cap | `normalized_query` |
| `RoutingNode` | main | `retrieve_candidates` (catalog KB) -> `classify_intent` -> `recommend` (confidence threshold, top-N); S-4 audit | `candidates`, `intent`, `routing_recommendation`, `catalog_kb_version` |
| `ResponseValidateNode` | post_process | format response + **S-3 deterministic membership gate** (every routed template_id must be a catalog member, else ERROR); S-4 audit | `formatted_output` |
| `catalog_kb_service` | service | curated, versioned catalog fixture + `retrieve_candidates` + `is_valid_template_id` | candidates / membership |
| `routing_service` | service | `classify_intent` + `recommend` (deterministic scorer) | intent / recommendation |

## 5. Security (5-layer)

- **S-1**: `required_trust_level: VERIFIED_EXTERNAL` (agent default, `config/agent.yaml`).
- **S-2**: framework `_security_gate_input()` (`@final`) + domain input guard in `QueryNormalizeNode`.
- **S-3**: framework `_security_gate_output()` (`@final`) + domain deterministic membership gate in
  `ResponseValidateNode.execute()` — every returned `template_id` (recommendation + candidates) must
  exist in the catalog KB (dict lookup, NOT LLM self-check); on violation drop output + return ERROR.
- **S-4**: `emit_trace_event()` in `RoutingNode` and `ResponseValidateNode` — template_id + confidence
  only (no PII).
- **S-5**: no credentials in source/state; routing output carries no PII. Secrets (if an LLM is wired)
  via entry-point `bound_secrets`/`secrets_factory`/`provision_secrets` (`src/api/server.py`).

## 6. Catalog KB - mock sample data, deterministic-core

The shipped catalog is **mock sample data**: ten placeholder entries (`SAMPLE-RAG-01`,
`SAMPLE-FIN-01`, ...) that illustrate the schema. They are not real templates. Replace `_CATALOG`
in `src/services/catalog_kb_service.py` with your own template catalog before use; the routing
logic and the S-3 membership gate work unchanged on any IDs. An embedding model is deferred.
Retrieval is a deterministic keyword/intent match over the catalog. Each entry carries
Japanese triggers alongside the English ones, matched against the original request text rather than
the lowercased copy: requests arrive in Japanese, and an English-only trigger set scored every entry
at zero for them, leaving the ranking to catalog order
(`src/services/catalog_kb_service.py`, `CATALOG_KB_VERSION` surfaced in every recommendation).
When the embedding dependency is approved, swap the matcher for dense retrieval behind the same
`retrieve_candidates` signature — no node change. The S-3 membership check (`is_valid_template_id`)
is already deterministic and catalog-backed.

## 7. Deployment entry points

The agent is reachable through two entry points, and both resolve their runtime inputs the same way.

| Entry point | File | Used by |
|---|---|---|
| Standalone HTTP | `src/api/server.py` | staging rehearsal, direct invocation |
| Marketplace one-shot Pod | `cli.py` | the platform runner (container `CMD`) |

Both read runtime parameters from `config/config.yaml` — the manifest carries discovery metadata
only — and both scope secrets to the same location (`namespace=cmn`, `agent_name=cmn-c1-171`), so a
secret provisioned for one path resolves identically on the other.

**No LLM client is constructed at either entry point.** The pipeline is deterministic; a client
may still be injected through `config["llm"]` by a caller that has one.

**Progress events.** Each pipeline stage emits a non-terminal progress event at its start, so a
caller sees the run advancing. Outside the Marketplace runtime the emitter resolves to a no-op, so
the same code is safe on every path. Terminal events belong to the platform runner and are never
emitted by this agent.

**Caller authentication at the standalone entry point.** A caller that no upstream middleware
vouched for stays anonymous unless it presents a deployment-level credential: the external bearer
token grants the verified-external level, and a separate staging-only runner credential is the only
way to reach the internal level. Trust established upstream is never changed.
