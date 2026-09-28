# CMN-C1-171 — Test Specification

**Template ID**: CMN-C1-171 | **Category**: Cat 1 | **Industry**: CMN

Tests live under `tests/unit/`, `tests/integration/`, `tests/proof_of_boundary/` and run via
`python -m pytest tests/` (CI `run-tests`). Framework from the `agenticstar-agentcore==1.0.0`
wheel.

## 1. Unit tests (per node: success + error/edge)

| File | Node | Cases |
|---|---|---|
| `test_query_normalize_node.py` | QueryNormalizeNode | success (normalize + cap); empty-input ERROR (S-2) |
| `test_routing_node.py` | RoutingNode | routes financial request -> SAMPLE-FIN-01; ambiguous -> top candidates; missing query ERROR |
| `test_response_validate_node.py` | ResponseValidateNode | valid template_id passes; **S-3 rejects unknown recommendation id**; S-3 rejects unknown candidate id |

The catalog is mock sample data (`SAMPLE-*` IDs); tests assert against those placeholder entries.
`test_catalog_kb_service.py` also pins that membership is exact: an unknown ID is rejected.

## 2. Integration tests (`tests/integration/test_graph.py`)

Full Cat 1 graph `Graph().compile()` + `invoke(query, ctx=...)`:

| Case | Expectation |
|---|---|
| Healthcare request | SUCCESS; routes to SAMPLE-HCR-01; kb_version + top_candidates present |
| Ambiguous query | SUCCESS (no crash) |
| Empty input | does not crash; no template_id |
| node_history | includes QueryNormalizeNode, RoutingNode, ResponseValidateNode |

## 3. Proof-of-Boundary (`tests/proof_of_boundary/`)

| File | PB | Checks |
|---|---|---|
| `test_import_isolation.py` | PB-4 | no `agenticstar` / Level-0 imports in `src/` (AST) |
| `test_state_safety.py` | PB-2/PB-5 | State holds only msgpack-safe primitives; no Pydantic / InvocationContext / credential fields |

## 4. Mapping to the framework compliance TCs

| TC | Covered by |
|---|---|
| TC-01 State contract | PB state_safety + `State(AgentState)` flat TypedDict |
| TC-02 input reject | QueryNormalizeNode empty test |
| TC-03 No JWT/keys in src | `gate-credential-scan` CI |
| TC-05 Audit logging | `emit_trace_event` in RoutingNode + ResponseValidateNode |
| TC-06/07 gates non-bypassable | framework `@final` gates + S-3 membership gate in ResponseValidateNode |
| TC-08 trust level | `required_trust_level: VERIFIED_EXTERNAL` in agent.yaml |

All `test_*` functions contain real assertions (no all-stub files — `gate-stub-check` passes).

## 5. Deployment path tests

### TC-DEP-01 Marketplace entry point identity — `tests/unit/test_cli_entry_point.py`

| Case | Expected |
|---|---|
| Identity is concrete | `agent_name` / `namespace` are non-empty and not the runner default |
| Identity matches the HTTP entry point | the values equal what `src/api/server.py` passes to `secrets_factory`; where that entry point provisions no secrets, they equal the manifest `namespace` and the lower-cased template id |
| The runner call uses the constants | `run_agent_marketplace` is called with the module constants, not inline literals |

### TC-DEP-02 Standalone entry point boundary — `tests/proof_of_boundary/test_server_llm_injection.py`

| Case | Expected |
|---|---|
| Boots with no credential provisioned | the module imports and the app/agent objects are constructed |
| External bearer never reaches the internal level | resolves to the verified-external level |
| Staging runner credential reaches the internal level | resolves to the internal level |
| Wrong or missing bearer while auth is enabled | rejected with 401 |
