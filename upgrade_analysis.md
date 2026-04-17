# XOAI Upgrade Summary

## Scope of This Pass
This pass implemented the coordinated architecture upgrade requested for:

- deeper query-run trace UI
- richer topology planning with parallel/retry/verifier branches
- stronger success-vs-failure comparison and utility scoring
- replay-based prompt benchmarking before promotion
- prompt version history, diff, and rollback
- MCP health/reconnect policy and role-aware exposure
- broader frontend i18n cleanup on priority user-facing views
- automated backend tests for runtime/experience/MCP behavior

This file is intended as a handoff artifact for the next engineer or agent.

## What Is Complete

### 1. Query Runtime / Topology
Implemented in:

- [backend/xoai/agents/topology.py](/home/haku/projects/1.xoai/backend/xoai/agents/topology.py:1)
- [backend/xoai/agents/runtime.py](/home/haku/projects/1.xoai/backend/xoai/agents/runtime.py:1)
- [backend/xoai/agents/experience.py](/home/haku/projects/1.xoai/backend/xoai/agents/experience.py:1)

Current behavior:

- `ExecutionNode` now carries:
  - `branch_type`
  - `parallel_group`
  - `retry_of`
  - `verifier_for`
  - `max_retries`
  - `entry_condition`
- planner remains template-based, but now supports:
  - `clarify_then_execute`
  - `execute_then_verify_then_retry`
  - `research_parallel_compare_synthesize`
  - `architect_parallel_research_then_execute`
- runtime no longer executes only linearly
- parallel nodes in the same `parallel_group` execute in the same batch
- verifier nodes can fail a path and trigger retry eligibility
- retry branches are bounded to one retry
- skipped retry nodes are persisted as skipped node runs

Persisted query-run detail now includes:

- full execution plan
- node runs
- branch metadata
- output chunks
- tool events
- failure modes

### 2. Experience Library / Comparative Scoring
Implemented in:

- [backend/xoai/agents/experience.py](/home/haku/projects/1.xoai/backend/xoai/agents/experience.py:1)
- [backend/xoai/agents/experience_consolidator.py](/home/haku/projects/1.xoai/backend/xoai/agents/experience_consolidator.py:1)

Current behavior:

- lessons now store explicit utility components:
  - `success_delta`
  - `reuse_rate`
  - `severity`
  - `freshness`
  - `confidence`
  - computed `utility_score`
- profile insights are recomputed from kept lessons
- insights now include:
  - `contrasts`
  - `recommended_behaviors`
  - `comparative_summary`
  - aggregated `utility_components`
- consolidation continues to operate on active kept lessons

### 3. Prompt Evolution / Benchmark / Versioning
Implemented in:

- [backend/xoai/agents/evolution.py](/home/haku/projects/1.xoai/backend/xoai/agents/evolution.py:1)
- [backend/xoai/agents/prompt_bench.py](/home/haku/projects/1.xoai/backend/xoai/agents/prompt_bench.py:1)
- [backend/xoai/prompts/manager.py](/home/haku/projects/1.xoai/backend/xoai/prompts/manager.py:1)

Current behavior:

- prompt candidates now store:
  - prompt source name
  - current prompt content
  - proposed prompt content
  - latest benchmark score/summary
- replay benchmark runs are stored in `prompt_bench_runs`
- promotion is gated:
  - candidate must meet benchmark threshold before promotion
- promotion now creates `prompt_versions`
- version history supports:
  - list
  - detail
  - parent diff
  - rollback
- runtime prompt loading now checks active prompt versions before falling back to the prompt file on disk

### 4. MCP Health / Reconnect / Role Exposure
Implemented in:

- [backend/xoai/mcp/client.py](/home/haku/projects/1.xoai/backend/xoai/mcp/client.py:1)
- [backend/xoai/mcp/router.py](/home/haku/projects/1.xoai/backend/xoai/mcp/router.py:1)
- [backend/xoai/agents/tool_registry.py](/home/haku/projects/1.xoai/backend/xoai/agents/tool_registry.py:1)

Current behavior:

- MCP server records now support:
  - `last_heartbeat_at`
  - `last_error`
  - `reconnect_count`
  - `allowed_roles`
- MCP manager now:
  - pings existing sessions before reuse
  - reconnects on failed tool call up to a bounded limit
  - persists heartbeat/error/reconnect updates
- MCP tool injection is role-aware
- admin/user tool exposure now respects `allowed_roles`

### 5. Admin APIs
Implemented in:

- [backend/xoai/admin/router.py](/home/haku/projects/1.xoai/backend/xoai/admin/router.py:1)

Added or extended endpoints:

- `GET /api/admin/query-runs/{query_id}`
- `POST /api/admin/prompt-candidates/{id}/benchmark`
- `GET /api/admin/prompt-candidates/{id}/benchmarks`
- `GET /api/admin/prompt-versions`
- `GET /api/admin/prompt-versions/{id}`
- `POST /api/admin/prompt-versions/{id}/rollback`

### 6. Admin Frontend
Implemented in:

- [frontend/src/services/api.js](/home/haku/projects/1.xoai/frontend/src/services/api.js:1)
- [frontend/src/views/AdminDashboard.vue](/home/haku/projects/1.xoai/frontend/src/views/AdminDashboard.vue:1)

Current runtime/admin UI behavior:

- query runs can now be inspected in detail
- run detail shows:
  - topology metadata
  - node timeline
  - branch metadata
  - tool events
  - output chunks
  - final output
  - failure summary
- experience lessons show utility component data
- prompt candidates support benchmark action
- prompt versions are listed and can be inspected / rolled back
- MCP form now supports allowed roles
- MCP list shows heartbeat, reconnect count, allowed roles, and last error

### 7. i18n Cleanup
Updated:

- [frontend/src/views/ChatView.vue](/home/haku/projects/1.xoai/frontend/src/views/ChatView.vue:1)
- [frontend/src/views/WorkspaceView.vue](/home/haku/projects/1.xoai/frontend/src/views/WorkspaceView.vue:1)
- [frontend/src/views/UserSettingsView.vue](/home/haku/projects/1.xoai/frontend/src/views/UserSettingsView.vue:1)
- [frontend/src/i18n/locales/en.json](/home/haku/projects/1.xoai/frontend/src/i18n/locales/en.json:1)
- [frontend/src/i18n/locales/vi.json](/home/haku/projects/1.xoai/frontend/src/i18n/locales/vi.json:1)

Completed in this pass:

- major hardcoded text in the prioritized main views was moved to i18n
- new admin runtime / MCP / prompt-version strings were added to i18n
- work-chat notifications, workspace labels, settings labels, and major action strings now switch with locale

### 8. Automated Tests
Added:

- [backend/tests/test_topology_runtime.py](/home/haku/projects/1.xoai/backend/tests/test_topology_runtime.py:1)
- [backend/tests/test_experience_consolidator.py](/home/haku/projects/1.xoai/backend/tests/test_experience_consolidator.py:1)
- [backend/tests/test_evolution.py](/home/haku/projects/1.xoai/backend/tests/test_evolution.py:1)
- [backend/tests/test_tool_registry_mcp.py](/home/haku/projects/1.xoai/backend/tests/test_tool_registry_mcp.py:1)

Covered areas:

- topology template generation
- parallel batch selection
- retry/verifier helper behavior
- utility component aggregation
- comparative summary generation
- prompt promotion benchmark gating
- prompt version creation on promotion
- MCP role-based tool injection

## Validation Run

These validations were run successfully after the final changes:

- `.venv/bin/python -m compileall -q backend/xoai`
- `node --max-old-space-size=4096 ./node_modules/vite/bin/vite.js build`
- `/home/haku/projects/1.xoai/.venv/bin/python -m pytest backend/tests`
- `.venv/bin/python -c "from xoai.main import create_app; app=create_app(); print(app.title)"`

Latest test result:

- `10 passed in 2.14s`

Frontend build notes:

- build passed
- existing non-blocking warning remains:
  - mixed static/dynamic import of `frontend/src/i18n/index.js`
- existing chunk-size warnings remain due large bundles, especially image/Monaco-related assets

## What Is Partial

These items are now present but still first-version rather than fully mature:

### Topology Planner

- template-based only
- not free-form DAG synthesis
- retry policy is bounded and simple
- verifier failure detection is heuristic text/error based
- parallel execution is batch-based, not a full scheduler

### Prompt Evolution

- active prompt versioning works
- replay benchmarking exists
- promotion is gated
- but benchmark scoring is still heuristic and derived from recent query runs, not a true offline benchmark corpus

### MCP Health

- lazy health/reconnect is implemented
- no continuous background monitor yet
- stdio only in this pass

### i18n Cleanup

- priority views were cleaned up
- repo-wide cleanup is improved, but not exhaustive across every component and utility view

## What Still Remains

These are the highest-value remaining items:

1. Strengthen replay benchmarking
- use persisted benchmark cases instead of only recent query runs
- add richer per-role scoring rubrics
- show benchmark history more deeply in admin UI

2. Deepen runtime trace UX
- add collapsible node cards with better event formatting
- show dependency graph / branch visualization
- surface retry ancestry more visually

3. Expand prompt version UX
- benchmark comparison view against current active prompt
- side-by-side diff UI
- promotion/rollback history timeline

4. Improve verifier/retry semantics
- make verifier output structured instead of keyword-based
- support more than one bounded retry policy per topology when appropriate
- add node-level retry reason codes

5. Broader i18n sweep
- shared components still contain hardcoded text in places
- some non-priority views/components were not fully swept in this pass

6. More automated tests
- add query-run detail API tests
- add admin router endpoint tests
- add MCP manager reconnect tests at a deeper integration layer
- add frontend component tests or e2e coverage if desired

## Recommended Next Order

Recommended next implementation order for the next agent:

1. add structured verifier output and retry reason codes
2. deepen admin trace visualization for query runs
3. add richer prompt benchmark datasets and comparison UI
4. expand MCP health management and permissions beyond lazy stdio-only checks
5. finish the remaining repo-wide i18n sweep
6. add API-level tests for admin/runtime/evolution routes

## Important Notes For The Next Agent

- The repo is already in a dirty worktree with many user-owned changes. Continue carefully and avoid broad refactors unless necessary.
- `prompt_versions` are now part of runtime prompt loading through [backend/xoai/prompts/manager.py](/home/haku/projects/1.xoai/backend/xoai/prompts/manager.py:1). Do not assume prompt files are the only source of truth anymore.
- MCP exposure now depends on `allowed_roles`. Any future tool-registry work must preserve that filter.
- The current admin dashboard already has the new runtime/version/MCP controls. Extend those surfaces rather than creating parallel routes unless there is a strong reason.
