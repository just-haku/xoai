# Night Shift Report

Branch: `xoai`
Date: `2026-04-17`

## Scope Executed

This pass covered backend hardening, channel attachment resilience, frontend workspace/file-viewer UX, prompt/runtime cleanup, and regression coverage.

## What Changed

### Phase 1: Security Hardening & State Resilience

- Hardened workspace jail enforcement in `backend/xoai/workspace/service.py` with:
  - absolute-path resolution
  - `os.path.commonpath` checks
  - `os.path.commonprefix` checks
  - explicit rejection of `../` traversal payloads
- Added atomic file writes with `.bak` recovery state in:
  - `backend/xoai/workspace/service.py`
  - `backend/xoai/agents/tools/filesystem.py`
  - `backend/xoai/workspace/router.py`
- Added Mongo-backed file operation tracking and startup recovery in:
  - `backend/xoai/db/mongo.py`
  - `backend/xoai/main.py`
- Tightened request validation in:
  - `backend/xoai/auth/router.py`
  - `backend/xoai/users/router.py`
- Kept JWTs on short access-token lifetime and rotating refresh sessions from the previous hardening pass.
- Disabled CORS by default and shifted to internal same-origin communication via `settings.enable_cors = false`.
- Rechecked backend logger hygiene. `print()` calls under `backend/xoai/` are gone.

### Phase 2: Omni-Channel Attachment Router

- Rebuilt channel bridges:
  - `backend/xoai/channels/zalo_bridge.py`
  - `backend/xoai/channels/telegram_bridge.py`
  - `backend/xoai/channels/discord_bridge.py`
- Zalo now fails soft on empty/attachment-only payloads and replies:
  - `I cannot read this attachment via Zalo. Please open your MangOS Web Interface to upload and view this file.`
- Telegram and Discord now persist incoming attachments into user workspace channel-upload folders under storage.
- Added shared outbound file delivery logic in `backend/xoai/channels/file_delivery.py`.
- Added channel-aware file dispatch helpers in:
  - `backend/xoai/agents/tools/zalo.py`
  - `backend/xoai/agents/tools/discord.py`
  - `backend/xoai/agents/tools/telegram.py`
  - `backend/xoai/channels/discord.py`
  - `backend/xoai/channels/telegram.py`
- Fixed legacy decrypt helper mismatches in:
  - `backend/xoai/channels/manager.py`
  - `backend/xoai/channels/notifier.py`

### Phase 3: Mango OS Frontend Polish

- Added viewport clamping and snap helpers in `frontend/src/stores/ui.js`.
- Wired split/full snapping through `frontend/src/views/ChatView.vue` so windows cannot drift off-screen and split mode stays gap-free.
- Improved drag-and-drop uploads in `frontend/src/components/WorkspaceContent.vue`:
  - path-aware uploads
  - drag overlay state
  - success/error notifications
  - i18n extraction for new strings
- Fixed file-viewer contracts in:
  - `backend/xoai/workspace/router.py`
  - `frontend/src/services/api.js`
  - `frontend/src/views/FileViewerPage.vue`
- `FileViewerPage.vue` now:
  - relies on JWT in `localStorage`
  - uses authenticated fetch helpers
  - loads code/docx/xlsx/image content through the backend correctly

### Phase 4: Agent Topology & Prompt Debloating

- Integrated dynamic Gemini REST model discovery into `backend/xoai/agents/prompt_bench.py`.
- Reinforced verifier schema signaling in `backend/xoai/agents/topology.py`.
- Rewrote prompts into concise `<ROLE>`, `<OBJECTIVE>`, `<CONSTRAINTS>` format:
  - `backend/xoai/prompts/supervisor.md`
  - `backend/xoai/prompts/executor.md`
  - `backend/xoai/prompts/architect.md`
  - `backend/xoai/prompts/ticket_triage.md`

### Phase 5: Technical Debt & Tests

- Removed a few obvious unused frontend imports/functions in:
  - `frontend/src/components/WorkspaceDesktop.vue`
  - `frontend/src/components/viewers/MonacoEditor.vue`
  - `frontend/src/components/viewers/XlsxViewer.vue`
- Added/updated tests:
  - `backend/tests/test_workspace_safety.py`
  - `backend/tests/test_topology_runtime.py`
  - `backend/tests/test_auth_session_service.py`
  - `backend/tests/test_shell_tool.py`
  - `backend/tests/test_message_migration.py`
  - `backend/tests/test_channels_manager.py`

## Architectural Decisions

- Kept same-origin communication as the default path and made CORS opt-in instead of mandatory.
- Reused the existing auth/session hardening work already in the repo rather than replacing it with a second parallel auth model.
- Implemented channel file routing around a single shared backend delivery helper instead of embedding platform-specific logic in every agent tool.
- Kept background jobs in-process with persisted Mongo state. No external queue was introduced.
- Preserved the existing admin runtime DAG UI scaffold because it was already present and functional enough; this pass focused on ensuring the underlying runtime/file flows no longer broke the surrounding experience.

## Verification Results

- Backend tests:
  - `./.venv/bin/pytest -q backend/tests`
  - Result: `30 passed`
- Frontend build:
  - `npm run build`
  - Result: success

## Warnings / Non-Blocking Issues

- Frontend build still emits the existing Vite warning about `frontend/src/i18n/index.js` being both dynamically and statically imported.
- Frontend build still emits chunk-size warnings, primarily from Monaco/ImageViewer bundles. Build succeeds, but bundle splitting can be improved later.
- `backend/=1.0` exists in the worktree and was left untouched because it appears unrelated to this pass.
- Discord outbound file sending currently uses a short-lived client login flow. It is functional but heavier than a persistent shared client or webhook-based approach.
- Telegram/Discord attachment support was implemented conservatively around the currently installed SDKs. If production traffic is high, this should be followed by dedicated transport/load testing.

## Files Added

- `backend/xoai/jobs.py`
- `backend/xoai/job_handlers.py`
- `backend/xoai/metrics.py`
- `backend/xoai/channels/file_delivery.py`
- `backend/xoai/agents/tools/discord.py`
- `backend/xoai/agents/tools/telegram.py`
- `backend/tests/test_auth_session_service.py`
- `backend/tests/test_shell_tool.py`
- `backend/tests/test_message_migration.py`
- `backend/tests/test_channels_manager.py`

## Files With Major Edits

- `backend/xoai/main.py`
- `backend/xoai/workspace/service.py`
- `backend/xoai/workspace/router.py`
- `backend/xoai/agents/tools/filesystem.py`
- `backend/xoai/channels/zalo_bridge.py`
- `backend/xoai/channels/telegram_bridge.py`
- `backend/xoai/channels/discord_bridge.py`
- `backend/xoai/auth/router.py`
- `backend/xoai/users/router.py`
- `frontend/src/views/ChatView.vue`
- `frontend/src/components/WorkspaceContent.vue`
- `frontend/src/views/FileViewerPage.vue`

## What Failed

- No blocking test failures remained at end of run.
- No blocking frontend build failures remained at end of run.
- Remaining issues are warnings only and are listed above.
