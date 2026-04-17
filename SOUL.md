# XOAI Project SOUL (System Operating Unified Logic)

**Version**: 4.0.0-ULTIMATE-LEXICON
**Objective**: Transform a standard LLM chat interface into a highly secure, containerized, extensible, multi-agent, omni-channel operating system (The Tri-Agent OS/Mango OS).


---

## 1. Core Architecture & Infrastructure

### 1.1 The Secure Docker Sandbox & Permissions
- **Host User Mapping**: All containerized operations execute under the host user's UID/GID (`haku`), ensuring consistent file permissions and seamless host integration.
- **External Storage**: Explicitly mapped via `.env` (`${XOAI_STORAGE_PATH}:/app/storage/`), ensuring data persistence outside container lifecycle.
- **Dynamic Prompting**: System-level instructions reside in `/app/prompts/*.md`, allowing hot-swappable agent behaviors.
- **Backend Stack**: Built with **FastAPI** the core logic utilizes **WebSockets** for low-latency multi-agent console streaming.

### 1.2 The State Machine & Asynchronous Autonomy (Unkillable Architecture)
- **Offline Execution**: Intelligence loops (Architect/Executor) operate as background processes independent of active browser sessions.
- **State Persistence**: 
    - Every granular execution step is logged to MongoDB (e.g., `Status: Step 4 In Progress`).
    - Post-reboot, the system auto-resumes by identifying the last known-good checkpoint in the State Machine.
- **Atomic File Edits (Crash Recovery)**: 
    - Automatic backup (`.bak`) creation before any `write_file` operation.
    - If a write is interrupted (e.g., power loss), the State Machine restores the backup and re-routes the task.

### 1.3 User Provisioning & Admin Bridge Mode
- **Agent U (User Agent)**: Standard users bring their own LLM API keys. These are encrypted via **Fernet** at rest and used only for their personal agent workflows.
- **Admin Bridge Mode**: Global administrative toggle for Agent 0 (Supervisor) routing:
    - **Bridge OFF (Direct Stream)**: A0 collects support tickets from all users, created via "Contact Support" button, decides if it's minor or big changes, then informs the admin.
    - **Bridge ON (Assisted Routing)**: A0 acts as a debloater for user requests sent to Agent U, with a rate limit of **15 requests/min**.
- **God Mode Access**: Admins retain absolute visibility into system health, performance metrics, and global agent orchestration.

---

## 2. Intelligence Framework (The 3-Agent Triad)

### 2.1 The Execution & Self-Healing Loop
- **A1 (Architect) Planning**: Logic begins with the Architect drafting a comprehensive `implementation_plan.md`. Work only begins after explicit user/admin acceptance.
- **A1 Dispatches A2 (Executor)**: The task is decomposed into atomic steps. A1 monitors A2's terminal output and file diffs for quality control.
- **Intelligence Orchestration (`backend/xoai/agents/llm_pool.py`)**: Provider-agnostic interface supporting Gemini, OpenAI, and Anthropic with recursive tool-calling.

### 2.2 Deep Web Self-Healing
- **Native Browsing**: Agents utilize **SearXNG**, **DuckDuckGo**, and **Playwright (Headless Chromium)** for real-time research.
- **RAM Safety Queue**: A global hardware protection layer enforces a limit of **Max 3 active Playwright sessions** server-wide to prevent OOM (Out Of Memory) crashes.
- **The Strikeout System**: 
    - **2 Errors**: Triggers an automatic Web Search for the error stack trace to find community fixes.
    - **Persistent Failures**: The agent enters a "Wait" state and pings the human supervisor (Work Chat) for intervention.

---

## 3. UI Design System & Omni-Channel Routing

### 3.1 Mango OS Desktop
- **Window Manager**: A premium Vue-based interface featuring draggable, resizable windows. 
- **Edge-Snapping**: Implements modern desktop logic for 50/50 split-screen snapping.
- **Workspace Explorer**: Full IDE capabilities powered by **Monaco Editor** integration, featuring syntax highlighting and real-time file tree synchronization.
- **Visual Aesthetic**: Sleek Obsidian base with Mango Gold highlights, using Glassmorphism (`blur(16px)`) for layering.

### 3.2 Notification Routing & Omni-Channel Flow
- **Omni-Channel Memory**: 
    - The Web UI supports standard private chats.
    - **ONE Persistent "Work Chat"**: Acts as the master triage and agent-log hub.
    - External platform messages (Discord, Telegram, Zalo) synchronize **only** to the designated Work Chat.
- **Favorite Channel Workflow**: 
    - Admins can designate a "Favorite Channel" (e.g., Zalo). 
    - Task completions or errors are pushed proactively to this channel.
    - **Remote Command Execution**: Users can issue continuation commands (e.g., "Deploy it" or "Retry Step 4") directly from the side-channel without re-opening the Web OS.

---

## 4. Development & Operations

### 4.1 CLI Lifecycle (`run_xoai.sh`)
- `up/down`: Service orchestration via Docker Compose.
- `rebuild`: Cache-less container image refresh.
- `drop-db`: Secure Python-based database cleaning script.
- `add admin`: CLI command to initialize primary God Mode accounts.

---
*Created and Maintained by Antigravity AI Engine.*
