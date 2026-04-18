<template>
  <div class="admin-page-container">
    <aside class="admin-sidebar">
      <router-link to="/chat" class="back-link">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="3">
          <path d="M19 12H5M12 19l-7-7 7-7" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ t('admin.dashboard.back_to_workspace') }}
      </router-link>
      <div class="sidebar-brand">
        XO<span class="mango-text">AI</span> <span>Control</span>
      </div>
      <nav class="admin-nav">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          class="nav-item"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <div class="nav-icon" v-html="getIcon(tab.id)"></div>
          {{ tab.label }}
        </button>
      </nav>
      <div class="sidebar-spacer"></div>
      <div class="system-status">
        <div class="status-indicator">
          <span class="pulse"></span>
          <span>{{ t('admin.dashboard.system_online') }}</span>
        </div>
      </div>
    </aside>

    <main class="admin-main scrollable">
      <header class="pane-header">
        <div class="breadcrumb">{{ t('admin.dashboard.breadcrumb') }} / {{ currentTab.label }}</div>
        <h1>{{ currentTab.label }}</h1>
        <p>{{ currentTab.description }}</p>
      </header>

      <!-- USERS TAB -->
      <div v-if="activeTab === 'users'" class="tab-pane">
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-label">{{ t('admin.dashboard.users.stats.total_citizens') }}</span>
            <span class="stat-value">{{ stats.total }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">{{ t('admin.dashboard.users.stats.pending_approval') }}</span>
            <span class="stat-value accent">{{ stats.pending }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">{{ t('admin.dashboard.users.stats.active_workspaces') }}</span>
            <span class="stat-value">{{ users.length }}</span>
          </div>
        </div>

        <div class="table-container glass-panel mt-6">
          <table class="admin-table">
            <thead>
              <tr>
                <th>{{ t('admin.dashboard.users.table.identifier') }}</th>
                <th>{{ t('admin.dashboard.users.table.status') }}</th>
                <th>{{ t('admin.dashboard.users.table.quota_storage') }}</th>
                <th>{{ t('admin.dashboard.users.table.governance') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in users" :key="u.id">
                <td>
                  <div class="u-info">
                    <strong>{{ u.name || u.username }}</strong>
                    <span>{{ u.email }}</span>
                  </div>
                </td>
                <td><span class="badge" :class="u.status">{{ u.status }}</span></td>
                <td>
                  <div class="quota-progress-wrapper">
                    <div class="quota-text">{{ formatSize(u.quota_used_bytes) }} / {{ formatSize(u.quota_limit_bytes) }}</div>
                    <div class="quota-bar"><div class="quota-fill" :style="{ width: (u.quota_used_bytes / u.quota_limit_bytes * 100) + '%' }"></div></div>
                  </div>
                </td>
                <td>
                  <div class="action-cell">
                    <button class="btn-micro" @click="updateQuota(u)">{{ t('admin.dashboard.users.actions.quota') }}</button>
                    <button class="btn-micro" @click="resetUserPassword(u)">{{ t('admin.dashboard.users.actions.reset_password') }}</button>
                    <button v-if="u.status === 'pending'" class="btn-micro success" @click="approveUser(u)">{{ t('admin.dashboard.users.actions.approve') }}</button>
                    <button v-if="u.status === 'approved'" class="btn-micro danger" @click="suspendUser(u)">{{ t('admin.dashboard.users.actions.suspend') }}</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- AGENTS TAB -->
      <div v-if="activeTab === 'agents'" class="tab-pane">
        <div class="agent-grid">
          <div v-for="agent in agents" :key="agent.id" class="agent-config-card glass-panel">
            <div class="agent-header">
              <div class="agent-id">{{ agent.id.toUpperCase() }}</div>
              <h3>{{ agent.name }}</h3>
            </div>
            <div class="agent-body">
              <div class="input-group">
                <label>{{ t('admin.dashboard.agents.provider') }}</label>
                <CSelect 
                  v-model="agent.provider" 
                  :options="providerOptions" 
                />
              </div>
              <div class="input-group mt-3">
                <label>{{ t('admin.dashboard.agents.api_key') }}</label>
                <input type="password" v-model="agent.key" placeholder="••••••••••••••••" />
              </div>
              <div class="row mt-3">
                <div class="input-group flex-2">
                  <div class="label-with-action">
                    <label>{{ t('admin.dashboard.agents.model_id') }}</label>
                    <button 
                      class="btn-text-action" 
                      @click="fetchAgentModels(agent)"
                      :disabled="agent.fetching"
                    >
                      {{ agent.fetching ? t('admin.dashboard.agents.fetching') : t('admin.dashboard.agents.fetch_models') }}
                    </button>
                  </div>
                  <CSelect 
                    v-if="agent.availableModels.length > 0"
                    v-model="agent.model" 
                    :options="agent.availableModels"
                    :placeholder="t('admin.dashboard.agents.select_model')"
                  />
                  <input v-else v-model="agent.model" :placeholder="t('admin.dashboard.agents.model_placeholder')" />
                </div>
                <div class="input-group flex-3">
                  <label>{{ t('admin.dashboard.agents.base_url') }}</label>
                  <input v-model="agent.endpoint" :placeholder="t('admin.dashboard.agents.base_url_placeholder')" />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="action-bar-sticky">
          <button class="mango-button" @click="saveAgentSettings">{{ t('admin.dashboard.agents.save') }}</button>
        </div>
        <section class="glass-panel runtime-panel mt-6">
          <div class="section-head">
            <div>
              <h3>Titan Agent Profiles</h3>
              <p>Database-driven swarm agents with explicit prompt, tools, concurrency, and network policy.</p>
            </div>
            <button class="btn-micro" @click="runStorageGcPreview(true)">Preview GC</button>
          </div>
          <div class="form-grid">
            <div class="input-group">
              <label>Agent Key</label>
              <input v-model="agentProfileForm.agent_key" placeholder="executor_research" />
            </div>
            <div class="input-group">
              <label>Role</label>
              <input v-model="agentProfileForm.role" placeholder="executor" />
            </div>
            <div class="input-group">
              <label>Display Name</label>
              <input v-model="agentProfileForm.display_name" placeholder="Executor Research" />
            </div>
            <div class="input-group">
              <label>Prompt</label>
              <input v-model="agentProfileForm.prompt_name" placeholder="executor" />
            </div>
            <div class="input-group">
              <label>Provider</label>
              <input v-model="agentProfileForm.provider" placeholder="gemini" />
            </div>
            <div class="input-group">
              <label>Model</label>
              <input v-model="agentProfileForm.model" placeholder="gemini-1.5-flash" />
            </div>
            <div class="input-group">
              <label>Network Mode</label>
              <input v-model="agentProfileForm.risk_policy.network_mode" placeholder="network_disabled" />
            </div>
            <div class="input-group">
              <label>Tool Allowlist</label>
              <input :value="agentProfileForm.tool_allowlist.join(', ')" @input="agentProfileForm.tool_allowlist = $event.target.value.split(',').map(v => v.trim()).filter(Boolean)" placeholder="list_files, read_file" />
            </div>
          </div>
          <div class="action-bar-sticky">
            <button class="mango-button" @click="saveAgentProfile">Save Agent Profile</button>
            <button class="btn-micro" @click="runStorageGcPreview(false)">Run Storage GC</button>
          </div>
          <div v-if="gcPreview" class="runtime-detail-block mt-4">
            <label>Storage GC</label>
            <pre>{{ JSON.stringify(gcPreview, null, 2) }}</pre>
          </div>
          <div class="candidate-table mt-4">
            <div v-for="profile in agentProfiles" :key="profile.agent_key" class="candidate-row">
              <div class="candidate-main">
                <div><strong>{{ profile.display_name }}</strong> · <span class="runtime-meta">{{ profile.role }} · {{ profile.provider }} / {{ profile.model }}</span></div>
                <div class="candidate-reason">{{ profile.agent_key }} · tools={{ (profile.tool_allowlist || []).join(', ') || 'all' }}</div>
              </div>
              <div class="action-cell">
                <button class="btn-micro" @click="loadAgentProfile(profile)">Load</button>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- INFRA TAB -->
      <div v-if="activeTab === 'infra'" class="tab-pane">
        <div class="infra-grid">
          <section class="infra-panel glass-panel">
            <h3>{{ t('admin.dashboard.infra.smtp_title') }}</h3>
            <div class="form-grid">
              <div class="input-group">
                <label>{{ t('admin.dashboard.infra.hostname') }}</label>
                <input v-model="smtp.host" :placeholder="t('admin.dashboard.infra.hostname_placeholder')" />
              </div>
              <div class="input-group">
                <label>{{ t('admin.dashboard.infra.port') }}</label>
                <input v-model="smtp.port" :placeholder="t('admin.dashboard.infra.port_placeholder')" />
              </div>
              <div class="input-group">
                <label>{{ t('admin.dashboard.infra.username') }}</label>
                <input v-model="smtp.sender_email" :placeholder="t('admin.dashboard.infra.username_placeholder')" />
              </div>
              <div class="input-group">
                <label>{{ t('admin.dashboard.infra.secret') }}</label>
                <input type="password" v-model="smtp.password" placeholder="••••••••" />
              </div>
            </div>
          </section>

          <section class="infra-panel glass-panel">
            <h3>{{ t('admin.dashboard.infra.workspace_title') }}</h3>
            <div class="input-group">
              <label>{{ t('admin.dashboard.infra.default_local_path') }}</label>
              <input v-model="settings.workspacePath" :placeholder="t('admin.dashboard.infra.default_local_path_placeholder')" />
            </div>
            <div class="toggle-setting mt-4">
              <div class="toggle-info">
                <strong>{{ t('admin.dashboard.infra.bridge_mode') }}</strong>
                <p>{{ t('admin.dashboard.infra.bridge_mode_desc') }}</p>
              </div>
              <button class="toggle-btn" :class="{ active: settings.bridgeMode }" @click="settings.bridgeMode = !settings.bridgeMode">
                {{ settings.bridgeMode ? t('admin.dashboard.common.enabled') : t('admin.dashboard.common.disabled') }}
              </button>
            </div>
          </section>
        </div>
        <div class="action-bar-sticky">
          <button class="mango-button" @click="saveInfraSettings">{{ t('admin.dashboard.infra.save') }}</button>
        </div>
      </div>

      <!-- RUNTIME TAB -->
      <div v-if="activeTab === 'runtime'" class="tab-pane">
        <div class="stats-grid runtime-stats">
          <div class="stat-card">
            <span class="stat-label">{{ t('admin.dashboard.runtime.stats.query_runs') }}</span>
            <span class="stat-value">{{ queryRuns.length }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">{{ t('admin.dashboard.runtime.stats.insights') }}</span>
            <span class="stat-value accent">{{ experienceInsights.length }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">{{ t('admin.dashboard.runtime.stats.prompt_candidates') }}</span>
            <span class="stat-value">{{ promptCandidates.length }}</span>
          </div>
        </div>

        <section class="glass-panel runtime-panel">
          <div class="section-head">
            <div>
              <h3>{{ t('admin.dashboard.runtime.query_runs_title') }}</h3>
              <p>{{ t('admin.dashboard.runtime.query_runs_desc') }}</p>
            </div>
            <button class="btn-micro" @click="fetchRuntimeData">{{ t('admin.dashboard.common.refresh') }}</button>
          </div>
          <div class="runtime-list">
            <div v-for="run in queryRuns" :key="run.id" class="runtime-item">
              <div class="runtime-row">
                <div>
                  <strong>{{ run.intent_profile }}</strong>
                  <div class="runtime-meta">{{ run.topology_type }} · {{ run.user_role }} · {{ formatDate(run.created_at) }}</div>
                </div>
                <div class="action-cell">
                  <span class="badge" :class="run.status">{{ run.status }}</span>
                  <button class="btn-micro" @click="inspectQueryRun(run)">{{ t('admin.dashboard.runtime.inspect') }}</button>
                </div>
              </div>
              <div class="runtime-request">{{ run.input }}</div>
              <div class="runtime-node-strip">
                <span v-for="node in run.execution_plan?.nodes || []" :key="node.id" class="runtime-node">{{ node.role }} / {{ node.action }}</span>
              </div>
            </div>
            <div v-if="queryRuns.length === 0" class="empty-state">{{ t('admin.dashboard.runtime.no_query_runs') }}</div>
          </div>
          <div v-if="selectedQueryRun" class="runtime-detail glass-panel">
            <div class="section-head">
              <div>
                <h4>{{ t('admin.dashboard.runtime.detail_title') }}</h4>
                <p>{{ selectedQueryRun.query_id }} · {{ selectedQueryRun.topology_type }} · {{ selectedQueryRun.intent_profile }}</p>
              </div>
              <button class="btn-micro" @click="closeQueryRunDetail">{{ t('actions.close') }}</button>
            </div>
            <div class="runtime-detail-grid">
              <div class="runtime-detail-block">
                <label>{{ t('admin.dashboard.runtime.final_output') }}</label>
                <pre>{{ selectedQueryRun.final_output || '-' }}</pre>
              </div>
              <div class="runtime-detail-block">
                <label>{{ t('admin.dashboard.runtime.failure_summary') }}</label>
                <pre>{{ (selectedQueryRun.failure_modes || []).join('\n') || '-' }}</pre>
              </div>
            </div>
            <div class="trace-map">
              <div class="trace-map-head">
                <div>
                  <h4>{{ t('admin.dashboard.runtime.trace_map_title') }}</h4>
                  <p>{{ t('admin.dashboard.runtime.trace_map_desc') }}</p>
                </div>
                <div class="trace-legend">
                  <span class="legend-pill primary">{{ t('admin.dashboard.runtime.branch_primary') }}</span>
                  <span class="legend-pill parallel">{{ t('admin.dashboard.runtime.branch_parallel') }}</span>
                  <span class="legend-pill verifier">{{ t('admin.dashboard.runtime.branch_verifier') }}</span>
                  <span class="legend-pill retry">{{ t('admin.dashboard.runtime.branch_retry') }}</span>
                </div>
              </div>
              <div class="trace-group-list">
                <div
                  v-for="group in selectedTraceGroups"
                  :key="group.id"
                  class="trace-group"
                  :class="{ parallel: group.type === 'parallel' }"
                >
                  <div class="trace-group-label">
                    <span>{{ group.label }}</span>
                    <small>{{ group.nodes.length }} {{ t('admin.dashboard.runtime.trace_nodes') }}</small>
                  </div>
                  <div class="trace-group-nodes" :class="{ parallel: group.type === 'parallel' }">
                    <div
                      v-for="nodeRun in group.nodes"
                      :key="nodeRun.node_id"
                      class="trace-node-card"
                      :class="traceNodeClasses(nodeRun)"
                    >
                      <div class="trace-node-top">
                        <div>
                          <div class="trace-node-title">{{ nodeRun.node_id }}</div>
                          <div class="runtime-meta">
                            {{ nodeRun.role }} / {{ nodeRun.action }} · {{ branchLabel(nodeRun) }}
                          </div>
                        </div>
                        <span class="badge" :class="nodeRun.status">{{ nodeRun.status }}</span>
                      </div>
                      <div class="trace-chip-row">
                        <span v-if="nodeRun.parallel_group" class="trace-chip parallel">
                          {{ t('admin.dashboard.runtime.parallel_group') }}: {{ nodeRun.parallel_group }}
                        </span>
                        <span v-if="nodeRun.verifier_for" class="trace-chip verifier">
                          {{ t('admin.dashboard.runtime.verifier_for') }}: {{ nodeRun.verifier_for }}
                        </span>
                        <span v-if="nodeRun.retry_of" class="trace-chip retry">
                          {{ t('admin.dashboard.runtime.retry_of') }}: {{ nodeRun.retry_of }}
                        </span>
                        <span v-if="nodeRun.structured_output?.reason_code" class="trace-chip reason" :class="reasonCodeClass(nodeRun.structured_output.reason_code)">
                          {{ t('admin.dashboard.runtime.reason_code') }}: {{ nodeRun.structured_output.reason_code }}
                        </span>
                      </div>
                      <div v-if="nodeRun.structured_output?.feedback" class="verifier-feedback">
                        {{ nodeRun.structured_output.feedback }}
                      </div>
                      <pre class="trace-input">{{ nodeRun.input }}</pre>
                      <div class="trace-events">
                        <div v-for="(toolEvent, index) in nodeRun.tool_events || []" :key="`${nodeRun.node_id}-tool-${index}`" class="trace-event">
                          <strong>{{ toolEvent.type }}</strong>
                          <span class="runtime-meta">{{ toolEvent.tool }}</span>
                          <pre>{{ JSON.stringify(toolEvent.args || toolEvent.result || {}, null, 2) }}</pre>
                        </div>
                      </div>
                      <details class="trace-output">
                        <summary>{{ t('admin.dashboard.runtime.output_chunks') }} ({{ (nodeRun.output_chunks || []).length }})</summary>
                        <pre>{{ (nodeRun.output_chunks || []).join('') || nodeRun.output || '-' }}</pre>
                      </details>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="glass-panel runtime-panel">
          <div class="section-head">
            <div>
              <h3>{{ t('admin.dashboard.runtime.insights_title') }}</h3>
              <p>{{ t('admin.dashboard.runtime.insights_desc') }}</p>
            </div>
          </div>
          <div class="insight-grid">
            <div v-for="insight in experienceInsights" :key="insight.id" class="insight-card">
              <div class="insight-head">
                <strong>{{ insight.profile_key }}</strong>
                <span>{{ formatDate(insight.updated_at) }}</span>
              </div>
              <div class="insight-block">
                <label>{{ t('admin.dashboard.runtime.recommended') }}</label>
                <ul>
                  <li v-for="(item, index) in (insight.recommended_behaviors || []).slice(0, 3)" :key="`${insight.id}-rec-${index}`">{{ item }}</li>
                </ul>
              </div>
              <div class="insight-block muted">
                <label>{{ t('admin.dashboard.runtime.failure_signals') }}</label>
                <ul>
                  <li v-for="(item, index) in (insight.failure_patterns || []).slice(0, 2)" :key="`${insight.id}-fail-${index}`">{{ item }}</li>
                </ul>
              </div>
            </div>
            <div v-if="experienceInsights.length === 0" class="empty-state">{{ t('admin.dashboard.runtime.no_insights') }}</div>
          </div>
        </section>

        <section class="glass-panel runtime-panel">
          <div class="section-head">
            <div>
              <h3>{{ t('admin.dashboard.runtime.lessons_title') }}</h3>
              <p>{{ t('admin.dashboard.runtime.lessons_desc') }}</p>
            </div>
          </div>
          <div class="candidate-table">
            <div v-for="lesson in experienceLessons" :key="lesson.id" class="candidate-row">
              <div class="candidate-main">
                <div><strong>{{ lesson.profile_key }}</strong> · <span class="runtime-meta">{{ lesson.lesson_type }} · {{ lesson.keep_state }} · utility {{ lesson.utility_score }}</span></div>
                <div class="candidate-reason">{{ lesson.statement }}</div>
                <div class="runtime-meta">
                  delta={{ lesson.utility_components?.success_delta ?? '-' }} ·
                  reuse={{ lesson.utility_components?.reuse_rate ?? '-' }} ·
                  severity={{ lesson.utility_components?.severity ?? '-' }} ·
                  confidence={{ lesson.utility_components?.confidence ?? '-' }}
                </div>
              </div>
              <div class="action-cell">
                <button class="btn-micro" @click="applyLessonAction(lesson, 'keep')">{{ t('admin.dashboard.runtime.keep') }}</button>
                <button class="btn-micro" @click="applyLessonAction(lesson, 'add')">{{ t('admin.dashboard.runtime.add') }}</button>
                <button class="btn-micro danger" @click="applyLessonAction(lesson, 'prune')">{{ t('admin.dashboard.runtime.prune') }}</button>
                <button class="btn-micro" @click="mergeLesson(lesson)">{{ t('admin.dashboard.runtime.merge') }}</button>
              </div>
            </div>
            <div v-if="experienceLessons.length === 0" class="empty-state">{{ t('admin.dashboard.runtime.no_lessons') }}</div>
          </div>
        </section>

        <section class="glass-panel runtime-panel">
          <div class="section-head">
            <div>
              <h3>{{ t('admin.dashboard.runtime.consolidations_title') }}</h3>
              <p>{{ t('admin.dashboard.runtime.consolidations_desc') }}</p>
            </div>
          </div>
          <div class="candidate-table">
            <div v-for="entry in experienceConsolidations" :key="entry.id" class="candidate-row">
              <div class="candidate-main">
                <div><strong>{{ entry.profile_key }}</strong> · <span class="runtime-meta">{{ entry.action }} · {{ formatDate(entry.created_at) }}</span></div>
                <div class="runtime-meta">source={{ entry.source_lesson_id || '-' }} target={{ entry.target_lesson_id || '-' }}</div>
              </div>
            </div>
            <div v-if="experienceConsolidations.length === 0" class="empty-state">{{ t('admin.dashboard.runtime.no_consolidations') }}</div>
          </div>
        </section>

        <section class="glass-panel runtime-panel">
          <div class="section-head">
            <div>
              <h3>{{ t('admin.dashboard.runtime.candidates_title') }}</h3>
              <p>{{ t('admin.dashboard.runtime.candidates_desc') }}</p>
            </div>
          </div>
          <div class="candidate-table">
            <div v-for="candidate in promptCandidates" :key="candidate.id" class="candidate-row">
              <div>
                <strong>{{ candidate.role }}</strong>
                <div class="runtime-meta">{{ candidate.profile_key }} · {{ candidate.promotion_status }}</div>
              </div>
              <div class="candidate-main">
                <div class="candidate-reason">{{ candidate.mutation_reason }}</div>
                <div v-if="candidate.evaluation_summary" class="runtime-meta">{{ candidate.evaluation_summary }}</div>
                <div v-if="candidate.latest_benchmark_summary" class="runtime-meta">{{ candidate.latest_benchmark_summary }}</div>
              </div>
              <div class="action-cell">
                <button class="btn-micro" @click="evaluatePromptCandidate(candidate)">{{ t('admin.dashboard.runtime.evaluate') }}</button>
                <button class="btn-micro" @click="benchmarkPromptCandidate(candidate)">{{ t('admin.dashboard.runtime.benchmark') }}</button>
                <button class="btn-micro success" @click="promotePromptCandidate(candidate)">{{ t('admin.dashboard.runtime.promote') }}</button>
                <button class="btn-micro danger" @click="rejectPromptCandidate(candidate)">{{ t('admin.dashboard.runtime.reject') }}</button>
              </div>
            </div>
            <div v-if="promptCandidates.length === 0" class="empty-state">{{ t('admin.dashboard.runtime.no_candidates') }}</div>
          </div>
        </section>

        <section class="glass-panel runtime-panel">
          <div class="section-head">
            <div>
              <h3>{{ t('admin.dashboard.runtime.prompt_versions_title') }}</h3>
              <p>{{ t('admin.dashboard.runtime.prompt_versions_desc') }}</p>
            </div>
          </div>
          <div class="candidate-table">
            <div v-for="version in promptVersions" :key="version.id" class="candidate-row">
              <div class="candidate-main">
                <div><strong>{{ version.role }}</strong> · <span class="runtime-meta">{{ version.version_label }} · {{ version.status }}</span></div>
                <div class="candidate-reason">{{ version.mutation_reason }}</div>
              </div>
              <div class="action-cell">
                <button class="btn-micro" @click="loadPromptVersion(version)">{{ t('admin.dashboard.runtime.inspect') }}</button>
                <button v-if="version.status !== 'active'" class="btn-micro danger" @click="rollbackVersion(version)">{{ t('admin.dashboard.runtime.rollback') }}</button>
              </div>
            </div>
            <div v-if="promptVersions.length === 0" class="empty-state">{{ t('admin.dashboard.runtime.no_prompt_versions') }}</div>
          </div>
          <div v-if="selectedPromptVersion" class="runtime-detail glass-panel">
            <div class="section-head">
              <div>
                <h4>{{ selectedPromptVersion.role }} · {{ selectedPromptVersion.version_label }}</h4>
                <p>{{ selectedPromptVersion.status }}</p>
              </div>
            </div>
            <div class="runtime-detail-grid">
              <div class="runtime-detail-block">
                <label>{{ t('admin.dashboard.runtime.prompt_content') }}</label>
                <pre>{{ selectedPromptVersion.content }}</pre>
              </div>
              <div class="runtime-detail-block">
                <label>{{ t('admin.dashboard.runtime.prompt_diff') }}</label>
                <pre>{{ selectedPromptVersion.diff || '-' }}</pre>
              </div>
            </div>
          </div>
        </section>
        <PromptEditor :prompts="promptFamilies" :versions="promptVersions" @refresh="fetchRuntimeData" />
      </div>

      <!-- MCP TAB -->
      <div v-if="activeTab === 'mcp'" class="tab-pane">
        <div class="infra-grid">
          <section class="infra-panel glass-panel">
            <div class="section-head">
              <div>
                <h3>{{ mcpEditingId ? t('admin.dashboard.mcp.edit_title') : t('admin.dashboard.mcp.register_title') }}</h3>
                <p>{{ t('admin.dashboard.mcp.register_desc') }}</p>
              </div>
              <button v-if="mcpEditingId" class="btn-micro" @click="resetMcpForm">{{ t('actions.cancel') }}</button>
            </div>
            <div class="form-grid mcp-form-grid">
              <div class="input-group">
                <label>{{ t('admin.dashboard.mcp.name') }}</label>
                <input v-model="mcpForm.name" :placeholder="t('admin.dashboard.mcp.name_placeholder')" />
              </div>
              <div class="input-group">
                <label>{{ t('admin.dashboard.mcp.transport') }}</label>
                <CSelect v-model="mcpForm.transport" :options="mcpTransportOptions" />
              </div>
              <div class="input-group">
                <label>{{ t('admin.dashboard.mcp.scope') }}</label>
                <CSelect v-model="mcpForm.scope" :options="mcpScopeOptions" />
              </div>
              <div class="input-group">
                <label>{{ t('admin.dashboard.mcp.enabled_label') }}</label>
                <CSelect v-model="mcpForm.enabled" :options="enabledOptions" />
              </div>
              <div class="input-group full-span">
                <label>{{ t('admin.dashboard.mcp.allowed_roles') }}</label>
                <div class="role-checkboxes">
                  <label v-for="role in mcpRoleOptions" :key="role.value" class="role-check">
                    <input type="checkbox" :checked="mcpForm.allowedRoles.includes(role.value)" @change="toggleAllowedRole(role.value)" />
                    <span>{{ role.label }}</span>
                  </label>
                </div>
              </div>
              <div v-if="mcpForm.scope === 'user'" class="input-group full-span">
                <label>{{ t('admin.dashboard.mcp.user_scope') }}</label>
                <CSelect v-model="mcpForm.userId" :options="userScopeOptions" :placeholder="t('admin.dashboard.mcp.select_user')" />
              </div>
              <div class="input-group full-span">
                <label>{{ t('admin.dashboard.mcp.command') }}</label>
                <input v-model="mcpForm.command" :placeholder="t('admin.dashboard.mcp.command_placeholder')" />
              </div>
              <div class="input-group full-span">
                <label>{{ t('admin.dashboard.mcp.args') }}</label>
                <input v-model="mcpForm.argsText" :placeholder="t('admin.dashboard.mcp.args_placeholder')" />
              </div>
              <div class="input-group full-span">
                <label>{{ t('admin.dashboard.mcp.env_json') }}</label>
                <textarea v-model="mcpForm.envText" rows="5" :placeholder="t('admin.dashboard.mcp.env_placeholder')"></textarea>
              </div>
            </div>
            <div class="action-row">
              <button class="mango-button" @click="saveMcpServer">{{ mcpEditingId ? t('admin.dashboard.mcp.update') : t('admin.dashboard.mcp.add') }}</button>
            </div>
          </section>

          <section class="infra-panel glass-panel">
            <h3>{{ t('admin.dashboard.mcp.connected_title') }}</h3>
            <div class="mcp-server-list">
              <div v-for="server in mcpServers" :key="server.id" class="mcp-server-item">
                <div class="runtime-row">
                  <div>
                    <strong>{{ server.name }}</strong>
                    <div class="runtime-meta">{{ server.command }} {{ (server.args || []).join(' ') }}</div>
                  </div>
                  <span class="badge" :class="server.status || 'idle'">{{ server.status || 'unknown' }}</span>
                </div>
                <div class="runtime-meta">{{ t('admin.dashboard.mcp.server_meta', { transport: server.transport || 'stdio', scope: server.scope, user: server.user_id ? resolveUserLabel(server.user_id) : '-', tools: (server.tools_cache || []).length }) }}</div>
                <div class="runtime-meta">
                  {{ t('admin.dashboard.mcp.server_health', {
                    heartbeat: formatDate(server.last_heartbeat_at),
                    reconnects: server.reconnect_count || 0,
                    roles: (server.allowed_roles || []).join(', ') || '-'
                  }) }}
                </div>
                <div v-if="server.last_error" class="runtime-meta danger-text">{{ server.last_error }}</div>
                <div class="action-cell mt-3">
                  <button class="btn-micro" @click="editMcpServer(server)">{{ t('admin.dashboard.mcp.edit') }}</button>
                  <button class="btn-micro" @click="refreshMcpServer(server)">{{ t('admin.dashboard.common.refresh') }}</button>
                  <button class="btn-micro danger" @click="deleteMcpServer(server)">{{ t('actions.delete') }}</button>
                </div>
              </div>
              <div v-if="mcpServers.length === 0" class="empty-state">{{ t('admin.dashboard.mcp.no_servers') }}</div>
            </div>
          </section>
        </div>
      </div>

      <!-- SCHEDULER TAB -->
      <div v-if="activeTab === 'scheduler'" class="tab-pane">
        <section class="glass-panel runtime-panel">
          <div class="section-head">
            <div>
              <h3>Scheduler</h3>
              <p>Create and manage recurring scheduled tasks backed by your agent swarm.</p>
            </div>
            <button class="btn-micro" @click="fetchSchedulerData">Refresh</button>
          </div>
          <div class="form-grid">
            <div class="input-group">
              <label>Task Name</label>
              <input v-model="schedulerForm.name" placeholder="weekly_report_gen" />
            </div>
            <div class="input-group">
              <label>Cron Expression</label>
              <input v-model="schedulerForm.cron" placeholder="0 8 * * 1" :class="{ 'input-error': cronError }" @input="validateCron" />
              <div v-if="cronError" class="field-error">{{ cronError }}</div>
              <div v-else-if="schedulerForm.cron && !cronError" class="field-hint">Valid cron expression</div>
            </div>
            <div class="input-group">
              <label>Agent Key</label>
              <input v-model="schedulerForm.agent_key" placeholder="executor" />
            </div>
            <div class="input-group">
              <label>Timezone</label>
              <input v-model="schedulerForm.timezone" placeholder="UTC" />
            </div>
            <div class="input-group full-span">
              <label>Payload (JSON)</label>
              <textarea v-model="schedulerForm.payloadText" rows="3" placeholder='{"key": "value"}'></textarea>
            </div>
          </div>
          <div class="action-bar-sticky">
            <button class="mango-button" @click="saveScheduledTask">{{ schedulerEditingId ? 'Update Task' : 'Create Task' }}</button>
            <button v-if="schedulerEditingId" class="btn-micro" @click="resetSchedulerForm">Cancel</button>
          </div>
          <div class="candidate-table mt-4">
            <div v-for="task in scheduledTasks" :key="task.id" class="candidate-row">
              <div class="candidate-main">
                <div>
                  <strong>{{ task.name }}</strong>
                  <span class="runtime-meta"> · {{ task.cron }} · {{ task.timezone || 'UTC' }}</span>
                </div>
                <div class="candidate-reason">agent={{ task.agent_key }} · {{ task.enabled ? '✅ enabled' : '⏸ disabled' }}</div>
                <div class="runtime-meta">last={{ formatDate(task.last_run_at) }} · next={{ formatDate(task.next_run_at) }}</div>
              </div>
              <div class="action-cell">
                <button class="btn-micro" @click="editScheduledTask(task)">Edit</button>
                <button class="btn-micro" :class="task.enabled ? 'danger' : 'success'" @click="toggleTask(task)">{{ task.enabled ? 'Disable' : 'Enable' }}</button>
                <button class="btn-micro danger" @click="deleteTask(task)">Delete</button>
              </div>
            </div>
            <div v-if="scheduledTasks.length === 0" class="empty-state">No scheduled tasks configured.</div>
          </div>
        </section>

        <section class="glass-panel runtime-panel mt-6">
          <div class="section-head">
            <div>
              <h3>Engram Compaction</h3>
              <p>Manually trigger memory compaction to summarize stale conversations into dense engrams.</p>
            </div>
          </div>
          <div class="form-grid">
            <div class="input-group">
              <label>Stale Days Threshold</label>
              <input type="number" v-model.number="engramCompaction.staleDays" min="1" max="365" />
            </div>
            <div class="input-group">
              <label>Batch Size</label>
              <input type="number" v-model.number="engramCompaction.batchSize" min="1" max="500" />
            </div>
          </div>
          <div class="action-bar-sticky">
            <button class="mango-button" :disabled="engramCompaction.running" @click="runEngramCompaction">{{ engramCompaction.running ? 'Running...' : 'Run Compaction' }}</button>
          </div>
          <div v-if="engramCompaction.result" class="runtime-detail-block mt-4">
            <label>Compaction Result</label>
            <pre>{{ JSON.stringify(engramCompaction.result, null, 2) }}</pre>
          </div>
        </section>
      </div>

      <!-- GODMODE TAB -->
      <div v-if="activeTab === 'godMode'" class="tab-pane">
        <div class="godmode-warning glass-panel">
          <div class="warning-icon">
             <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
               <path d="M12 2L1 21h22L12 2zm0 3.99L19.53 19H4.47L12 5.99zM11 16h2v2h-2v-2zm0-6h2v4h-2v-4z"/>
             </svg>
          </div>
          <div class="warning-text">
            <h3>{{ t('admin.dashboard.godmode.title') }}</h3>
            <p>{{ t('admin.dashboard.godmode.desc') }}</p>
          </div>
        </div>
        <div class="audit-grid">
          <div v-for="u in users" :key="u.id" class="audit-strip glass-panel">
            <div class="u-brief">
              <strong>{{ u.name || u.username }}</strong>
              <span>{{ u.status }}</span>
            </div>
            <div class="audit-stats">
              <div class="a-stat"><span>{{ t('admin.dashboard.godmode.last_act') }}</span><strong>2m ago</strong></div>
              <div class="a-stat"><span>{{ t('admin.dashboard.godmode.active_ws') }}</span><strong>2</strong></div>
            </div>
            <div class="audit-actions">
              <button class="btn-micro" :disabled="proxyLaunchingUserId === u.id || u.status !== 'approved'" @click="launchGodMode(u)">
                {{ proxyLaunchingUserId === u.id ? t('admin.dashboard.godmode.opening') : t('admin.dashboard.godmode.mirror') }}
              </button>
              <button class="btn-micro" @click="mockAction(t('admin.dashboard.godmode.audit_logs'), u.username)">{{ t('admin.dashboard.godmode.logs') }}</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../services/api'
import { useUIStore } from '../stores/ui'
import CSelect from '../components/common/CSelect.vue'
import PromptEditor from '../components/PromptEditor.vue'

const uiStore = useUIStore()
const { t } = useI18n()
const proxyLaunchingUserId = ref(null)

const activeTab = ref('users')
const tabs = computed(() => [
  { id: 'users', label: t('admin.dashboard.tabs.users.label'), description: t('admin.dashboard.tabs.users.desc') },
  { id: 'agents', label: t('admin.dashboard.tabs.agents.label'), description: t('admin.dashboard.tabs.agents.desc') },
  { id: 'runtime', label: t('admin.dashboard.tabs.runtime.label'), description: t('admin.dashboard.tabs.runtime.desc') },
  { id: 'mcp', label: t('admin.dashboard.tabs.mcp.label'), description: t('admin.dashboard.tabs.mcp.desc') },
  { id: 'infra', label: t('admin.dashboard.tabs.infra.label'), description: t('admin.dashboard.tabs.infra.desc') },
  { id: 'scheduler', label: 'Scheduler', description: 'Manage scheduled tasks & engram compaction jobs.' },
  { id: 'godMode', label: t('admin.dashboard.tabs.godMode.label'), description: t('admin.dashboard.tabs.godMode.desc') }
])

const getIcon = (id) => {
  switch(id) {
    case 'users': return '<svg viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5s-3 1.34-3 3 1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>'
    case 'agents': return '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8 0-.29.02-.58.05-.86 2.36-1.05 4.23-2.98 5.21-5.37C11.07 8.33 14.05 10 17.42 10c.78 0 1.53-.09 2.25-.26.21.41.33.88.33 1.37 0 4.41-3.59 8-8 8z"/></svg>'
    case 'runtime': return '<svg viewBox="0 0 24 24"><path d="M4 4h7v7H4V4m9 0h7v4h-7V4M4 13h4v7H4v-7m6 0h10v7H10v-7Z"/></svg>'
    case 'mcp': return '<svg viewBox="0 0 24 24"><path d="M7 2v11H3l5 9 5-9H9V2H7m9 0a3 3 0 0 0-3 3v6h2V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v6h2V5a3 3 0 0 0-3-3h-2m-1 11v9h2v-9h-2m4 0v9h2v-9h-2Z"/></svg>'
    case 'infra': return '<svg viewBox="0 0 24 24"><path d="M21 16.5C21 16.88 20.79 17.21 20.47 17.38L12.57 21.82C12.41 21.94 12.21 22 12 22C11.79 22 11.59 21.94 11.43 21.82L3.53 17.38C3.21 17.21 3 16.88 3 16.5V7.5C3 7.12 3.21 6.79 3.53 6.62L11.43 2.18C11.59 2.06 11.79 2 12 2C12.21 2 12.41 2.06 12.57 2.18L20.47 6.62C20.79 6.79 21 7.12 21 7.5V16.5Z"/></svg>'
    case 'scheduler': return '<svg viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>'
    case 'godMode': return '<svg viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>'
    default: return ''
  }
}

const currentTab = computed(() => tabs.value.find(tab => tab.id === activeTab.value))

// State
const users = ref([])
const stats = reactive({ total: 0, pending: 0, tickets: 0 })
const agents = ref([
  { id: 'a0', name: 'Agent 0 (Supervisor)', provider: 'gemini', key: '', model: '', endpoint: '', fetching: false, availableModels: [] },
  { id: 'a1', name: 'Agent 1 (Architect)', provider: 'gemini', key: '', model: '', endpoint: '', fetching: false, availableModels: [] },
  { id: 'a2', name: 'Agent 2 (Executor)', provider: 'gemini', key: '', model: '', endpoint: '', fetching: false, availableModels: [] }
])

const providerOptions = computed(() => [
  { label: t('admin.dashboard.agents.providers.gemini'), value: 'gemini' },
  { label: t('admin.dashboard.agents.providers.openai'), value: 'openai' },
  { label: t('admin.dashboard.agents.providers.anthropic'), value: 'anthropic' },
  { label: t('admin.dashboard.agents.providers.ollama'), value: 'ollama' },
  { label: t('admin.dashboard.agents.providers.custom'), value: 'custom' }
])
const mcpTransportOptions = computed(() => [
  { label: 'STDIO', value: 'stdio' }
])
const mcpScopeOptions = computed(() => [
  { label: t('admin.dashboard.mcp.scope_global'), value: 'global' },
  { label: t('admin.dashboard.mcp.scope_user'), value: 'user' }
])
const enabledOptions = computed(() => [
  { label: t('admin.dashboard.common.enabled'), value: true },
  { label: t('admin.dashboard.common.disabled'), value: false }
])
const mcpRoleOptions = computed(() => [
  { label: t('admin.dashboard.roles.admin'), value: 'admin' },
  { label: t('admin.dashboard.roles.user'), value: 'user' }
])
const smtp = reactive({ host: '', port: 587, sender_email: '', password: '' })
const settings = reactive({ bridgeMode: false, workspacePath: '/' })
const queryRuns = ref([])
const experienceInsights = ref([])
const experienceLessons = ref([])
const experienceConsolidations = ref([])
const promptCandidates = ref([])
const promptVersions = ref([])
const promptFamilies = ref([])
const selectedQueryRun = ref(null)
const selectedPromptVersion = ref(null)
const candidateBenchmarks = ref({})
const agentProfiles = ref([])
const gcPreview = ref(null)
const agentProfileForm = reactive({
  agent_key: '',
  role: '',
  display_name: '',
  prompt_name: '',
  provider: 'gemini',
  model: '',
  key: '',
  base_url: '',
  tool_allowlist: [],
  risk_policy: { network_mode: 'network_disabled' },
  enabled: true,
  max_concurrency: 1,
})
const scheduledTasks = ref([])
const schedulerEditingId = ref(null)
const schedulerForm = reactive({
  name: '',
  cron: '0 8 * * 1',
  timezone: 'UTC',
  agent_key: 'executor',
  payloadText: '{}',
})
const cronError = ref('')
const engramCompaction = reactive({
  staleDays: 7,
  batchSize: 50,
  running: false,
  result: null,
})
const mcpServers = ref([])
const mcpEditingId = ref(null)
const mcpForm = reactive({
  name: '',
  transport: 'stdio',
  scope: 'global',
  userId: '',
  enabled: true,
  allowedRoles: ['admin', 'user'],
  command: '',
  argsText: '',
  envText: ''
})

const userScopeOptions = computed(() => users.value.map(user => ({
  label: `${user.name || user.username} (${user.email || user.id})`,
  value: user.id
})))

const selectedTraceGroups = computed(() => {
  const nodeRuns = selectedQueryRun.value?.node_runs || []
  const groups = []
  const parallelGroups = new Map()

  for (const nodeRun of nodeRuns) {
    if (nodeRun.parallel_group) {
      const key = `parallel:${nodeRun.parallel_group}`
      if (!parallelGroups.has(key)) {
        const group = {
          id: key,
          type: 'parallel',
          label: `${t('admin.dashboard.runtime.branch_parallel')} · ${nodeRun.parallel_group}`,
          nodes: []
        }
        parallelGroups.set(key, group)
        groups.push(group)
      }
      parallelGroups.get(key).nodes.push(nodeRun)
      continue
    }

    groups.push({
      id: `node:${nodeRun.node_id}`,
      type: nodeRun.branch_type || 'primary',
      label: branchLabel(nodeRun),
      nodes: [nodeRun]
    })
  }

  return groups
})

const branchLabel = (nodeRun) => {
  if (nodeRun.branch_type === 'verifier') return t('admin.dashboard.runtime.branch_verifier')
  if (nodeRun.branch_type === 'retry') return t('admin.dashboard.runtime.branch_retry')
  if (nodeRun.parallel_group) return t('admin.dashboard.runtime.branch_parallel')
  return t('admin.dashboard.runtime.branch_primary')
}

const reasonCodeClass = (reasonCode = '') => {
  const normalized = reasonCode.toLowerCase()
  if (['valid', 'passed', 'no_issue'].includes(normalized)) return 'valid'
  if (normalized.includes('invalid') || normalized.includes('runtime') || normalized.includes('unsafe')) return 'critical'
  return 'warning'
}

const traceNodeClasses = (nodeRun) => ({
  verifier: nodeRun.branch_type === 'verifier',
  retry: nodeRun.branch_type === 'retry',
  parallel: Boolean(nodeRun.parallel_group),
  failed: nodeRun.status === 'failed',
  skipped: nodeRun.status === 'skipped',
  warning: nodeRun.branch_type === 'retry' || reasonCodeClass(nodeRun.structured_output?.reason_code) === 'warning',
  critical: reasonCodeClass(nodeRun.structured_output?.reason_code) === 'critical'
})

const fetchStats = async () => {
  try {
    const data = await api.admin.stats()
    Object.assign(stats, {
      total: data.total_users,
      pending: data.pending_users,
      tickets: data.open_tickets
    })
  } catch (err) {}
}

const fetchUsers = async () => {
  try {
    users.value = await api.admin.listUsers()
  } catch (err) {}
}

const fetchAgentProfiles = async () => {
  try {
    agentProfiles.value = await api.admin.listAgentProfiles()
  } catch (err) {
    uiStore.notify(err.message, 'danger')
  }
}

const fetchSettings = async () => {
  // Graceful helper for individual settings
  const getSafe = async (key) => {
    try { return await api.admin.getSetting(key) }
    catch (e) { return { value: null } }
  }

  // Load Bridge Mode
  const bridgeResp = await getSafe('agent_0_bridge_mode')
  settings.bridgeMode = bridgeResp.value?.enabled || false
  
  // Load Workspace Path
  const pathResp = await getSafe('admin_workspace_path')
  settings.workspacePath = pathResp.value?.path || '/'

  // Load SMTP
  const smtpResp = await getSafe('smtp')
  if (smtpResp.value) Object.assign(smtp, smtpResp.value)

  // Load Agent Settings
  for (const a of agents.value) {
    const aResp = await getSafe(`agent_${a.id}_config`)
    if (aResp.value) {
      Object.assign(a, aResp.value)
    }
  }
}

const saveInfraSettings = async () => {
  try {
    await api.admin.updateSetting('agent_0_bridge_mode', { enabled: settings.bridgeMode })
    await api.admin.updateSetting('admin_workspace_path', { path: settings.workspacePath })
    await api.admin.updateSetting('smtp', { ...smtp })
    uiStore.notify(t('admin.dashboard.notifications.infra_saved'), 'success')
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.sync_failed', { error: err.message }), 'danger')
  }
}

const saveAgentSettings = async () => {
  try {
    for (const a of agents.value) {
      await api.admin.updateSetting(`agent_${a.id}_config`, {
        provider: a.provider,
        key: a.key,
        model: a.model,
        endpoint: a.endpoint
      })
    }
    uiStore.notify(t('admin.dashboard.notifications.agent_saved'), 'success')
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.agent_failed', { error: err.message }), 'danger')
  }
}

const loadAgentProfile = (profile) => {
  Object.assign(agentProfileForm, {
    agent_key: profile.agent_key,
    role: profile.role,
    display_name: profile.display_name,
    prompt_name: profile.prompt_name,
    provider: profile.provider,
    model: profile.model,
    key: profile.key || '',
    base_url: profile.base_url || '',
    tool_allowlist: [...(profile.tool_allowlist || [])],
    risk_policy: { ...(profile.risk_policy || { network_mode: 'network_disabled' }) },
    enabled: profile.enabled !== false,
    max_concurrency: profile.max_concurrency || 1,
  })
}

const saveAgentProfile = async () => {
  try {
    await api.admin.saveAgentProfile({
      ...agentProfileForm,
      tool_allowlist: agentProfileForm.tool_allowlist.filter(Boolean),
    })
    uiStore.notify(`Saved agent profile ${agentProfileForm.agent_key}`, 'success')
    fetchAgentProfiles()
  } catch (err) {
    uiStore.notify(err.message, 'danger')
  }
}

const runStorageGcPreview = async (dryRun = true) => {
  try {
    gcPreview.value = await api.admin.runStorageGc(dryRun)
    uiStore.notify(dryRun ? 'Storage GC dry run complete' : 'Storage GC completed', 'success')
  } catch (err) {
    uiStore.notify(err.message, 'danger')
  }
}

const fetchAgentModels = async (agent) => {
  if (!agent.key) {
    uiStore.notify(t('admin.dashboard.notifications.api_key_required'), 'warning')
    return
  }
  
  agent.fetching = true
  try {
    // 1. Save settings first as approved
    await saveAgentSettings()
    
    // 2. Call backend fetch
    const resp = await api.admin.fetchModels({
      provider: agent.provider,
      key: agent.key,
      base_url: agent.endpoint
    })
    
    if (resp.models && resp.models.length > 0) {
      agent.availableModels = resp.models.map(m => ({ label: m, value: m }))
      uiStore.notify(t('admin.dashboard.notifications.models_fetched', { count: resp.models.length, agent: agent.id.toUpperCase() }), 'success')
    } else {
      uiStore.notify(t('admin.dashboard.notifications.no_models'), 'info')
    }
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.fetch_failed', { error: err.message }), 'danger')
  } finally {
    agent.fetching = false
  }
}

const updateQuota = async (user) => {
  const currentGB = (user.quota_limit_bytes / (1024 ** 3)).toFixed(1)
  const newLimit = await uiStore.prompt(t('admin.dashboard.users.prompts.modify_quota', { user: user.username }), t('admin.dashboard.users.prompts.enter_quota'), currentGB)
  
  if (newLimit === null || newLimit === undefined) return
  
  const bytes = parseFloat(newLimit) * 1024 ** 3
  if (isNaN(bytes)) return uiStore.notify(t('admin.dashboard.notifications.invalid_number'), 'warning')

  try {
    await api.admin.updateQuota(user.id, bytes)
    uiStore.notify(t('admin.dashboard.notifications.quota_updated', { user: user.username, limit: newLimit }), 'success')
    fetchUsers()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.quota_failed', { error: err.message }), 'danger')
  }
}

const resetUserPassword = async (user) => {
  const newPwd = await uiStore.prompt(t('admin.dashboard.users.prompts.reset_password', { user: user.username }), t('admin.dashboard.users.prompts.enter_new_password'))
  if (!newPwd) return
  
  try {
    await api.request(`/users/${user.id}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ password: newPwd })
    })
    uiStore.notify(t('admin.dashboard.notifications.password_updated', { user: user.username }), 'success')
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.reset_failed', { error: err.message }), 'danger')
  }
}

const approveUser = async (u) => {
  try {
    await api.request(`/users/${u.id}/approve`, { method: 'POST' })
    uiStore.notify(t('admin.dashboard.notifications.user_approved', { user: u.username }), 'success')
    fetchUsers()
    fetchStats()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.grant_failed', { error: err.message }), 'danger')
  }
}

const suspendUser = async (u) => {
  const ok = await uiStore.confirm(t('admin.dashboard.users.prompts.revoke_access'), t('admin.dashboard.users.prompts.confirm_suspend', { user: u.username }))
  if (!ok) return
  
  try {
    await api.request(`/users/${u.id}/disable`, { method: 'POST' })
    uiStore.notify(t('admin.dashboard.notifications.user_suspended', { user: u.username }), 'info')
    fetchUsers()
    fetchStats()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.revoke_failed', { error: err.message }), 'danger')
  }
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const mockAction = (action, target) => {
    uiStore.notify(t('admin.dashboard.notifications.action_initiated', { action, target }), 'info')
}

const launchGodMode = async (user) => {
  proxyLaunchingUserId.value = user.id
  try {
    const response = await api.admin.createProxySession(user.id)
    const params = new URLSearchParams({
      god_mode: 'true',
      handoff: response.handoff_token,
    })
    window.open(`/workspace?${params.toString()}`, '_blank', 'noopener')
    uiStore.notify(t('admin.dashboard.notifications.god_mode_opened', { user: user.name || user.username }), 'success')
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.god_mode_failed', { error: err.message }), 'danger')
  } finally {
    proxyLaunchingUserId.value = null
  }
}

const fetchRuntimeData = async () => {
  try {
    const [runs, insights, lessons, consolidations, candidates, versions, prompts] = await Promise.all([
      api.admin.listQueryRuns(),
      api.admin.listExperienceInsights(),
      api.admin.listExperienceLessons(),
      api.admin.listExperienceConsolidations(),
      api.admin.listPromptCandidates(),
      api.admin.listPromptVersions(),
      api.admin.listPrompts(),
    ])
    queryRuns.value = runs
    experienceInsights.value = insights
    experienceLessons.value = lessons
    experienceConsolidations.value = consolidations
    promptCandidates.value = candidates
    promptVersions.value = versions
    promptFamilies.value = prompts
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.runtime_load_failed', { error: err.message }), 'danger')
  }
}

const fetchMcpData = async () => {
  try {
    mcpServers.value = await api.mcp.list()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.mcp_load_failed', { error: err.message }), 'danger')
  }
}

const saveMcpServer = async () => {
  if (!mcpForm.name || !mcpForm.command) {
    uiStore.notify(t('admin.dashboard.notifications.mcp_name_command_required'), 'warning')
    return
  }
  if (mcpForm.scope === 'user' && !mcpForm.userId) {
    uiStore.notify(t('admin.dashboard.notifications.mcp_user_required'), 'warning')
    return
  }

  try {
    let env = undefined
    if (mcpForm.envText.trim()) {
      env = JSON.parse(mcpForm.envText)
    }

    const payload = {
      name: mcpForm.name,
      transport: mcpForm.transport,
      user_id: mcpForm.scope === 'user' ? mcpForm.userId : null,
      enabled: mcpForm.enabled,
      allowed_roles: [...mcpForm.allowedRoles],
      command: mcpForm.command,
      args: mcpForm.argsText.trim() ? mcpForm.argsText.trim().split(/\s+/) : [],
      env,
    }

    if (mcpEditingId.value) {
      await api.mcp.update(mcpEditingId.value, payload)
      uiStore.notify(t('admin.dashboard.notifications.mcp_updated', { name: mcpForm.name }), 'success')
    } else {
      await api.mcp.create(payload)
      uiStore.notify(t('admin.dashboard.notifications.mcp_created', { name: mcpForm.name }), 'success')
    }
    resetMcpForm()
    fetchMcpData()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.mcp_save_failed', { error: err.message }), 'danger')
  }
}

const refreshMcpServer = async (server) => {
  try {
    await api.mcp.refresh(server.id)
    uiStore.notify(t('admin.dashboard.notifications.mcp_refreshed', { name: server.name }), 'success')
    fetchMcpData()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.mcp_refresh_failed', { error: err.message }), 'danger')
  }
}

const editMcpServer = (server) => {
  mcpEditingId.value = server.id
  Object.assign(mcpForm, {
    name: server.name || '',
    transport: server.transport || 'stdio',
    scope: server.user_id ? 'user' : 'global',
    userId: server.user_id || '',
    enabled: server.enabled !== false,
    allowedRoles: [...(server.allowed_roles || (server.user_id ? ['user'] : ['admin', 'user']))],
    command: server.command || '',
    argsText: (server.args || []).join(' '),
    envText: server.env ? JSON.stringify(server.env, null, 2) : ''
  })
}

const deleteMcpServer = async (server) => {
  const ok = await uiStore.confirm(t('admin.dashboard.mcp.delete_title'), t('admin.dashboard.mcp.delete_confirm', { name: server.name }))
  if (!ok) return

  try {
    await api.mcp.delete(server.id)
    uiStore.notify(t('admin.dashboard.notifications.mcp_deleted', { name: server.name }), 'info')
    if (mcpEditingId.value === server.id) resetMcpForm()
    fetchMcpData()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.mcp_delete_failed', { error: err.message }), 'danger')
  }
}

const applyLessonAction = async (lesson, action) => {
  try {
    await api.admin.consolidateExperienceLesson(lesson.id, { action })
    uiStore.notify(t('admin.dashboard.notifications.lesson_action', { action }), action === 'prune' ? 'info' : 'success')
    fetchRuntimeData()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.lesson_action_failed', { action, error: err.message }), 'danger')
  }
}

const mergeLesson = async (lesson) => {
  const targetId = await uiStore.prompt(
    t('admin.dashboard.runtime.merge_lesson_title'),
    t('admin.dashboard.runtime.merge_lesson_prompt'),
    ''
  )
  if (!targetId) return

  try {
    await api.admin.consolidateExperienceLesson(lesson.id, {
      action: 'merge',
      target_lesson_id: targetId,
    })
    uiStore.notify(t('admin.dashboard.notifications.lesson_merged'), 'success')
    fetchRuntimeData()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.lesson_merge_failed', { error: err.message }), 'danger')
  }
}

const evaluatePromptCandidate = async (candidate) => {
  try {
    await api.admin.evaluatePromptCandidate(candidate.id)
    uiStore.notify(t('admin.dashboard.notifications.candidate_evaluated', { role: candidate.role }), 'success')
    fetchRuntimeData()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.candidate_evaluate_failed', { error: err.message }), 'danger')
  }
}

const benchmarkPromptCandidate = async (candidate) => {
  try {
    const result = await api.admin.benchmarkPromptCandidate(candidate.id)
    candidateBenchmarks.value = {
      ...candidateBenchmarks.value,
      [candidate.id]: [result, ...(candidateBenchmarks.value[candidate.id] || [])],
    }
    uiStore.notify(t('admin.dashboard.notifications.candidate_benchmarked', { role: candidate.role }), 'success')
    fetchRuntimeData()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.candidate_benchmark_failed', { error: err.message }), 'danger')
  }
}

const promotePromptCandidate = async (candidate) => {
  try {
    await api.admin.promotePromptCandidate(candidate.id)
    uiStore.notify(t('admin.dashboard.notifications.candidate_promoted', { role: candidate.role }), 'success')
    fetchRuntimeData()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.candidate_promote_failed', { error: err.message }), 'danger')
  }
}

const rejectPromptCandidate = async (candidate) => {
  try {
    await api.admin.rejectPromptCandidate(candidate.id)
    uiStore.notify(t('admin.dashboard.notifications.candidate_rejected', { role: candidate.role }), 'info')
    fetchRuntimeData()
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.candidate_reject_failed', { error: err.message }), 'danger')
  }
}

const resetMcpForm = () => {
  mcpEditingId.value = null
  Object.assign(mcpForm, {
    name: '',
    transport: 'stdio',
    scope: 'global',
    userId: '',
    enabled: true,
    allowedRoles: ['admin', 'user'],
    command: '',
    argsText: '',
    envText: ''
  })
}

const formatDate = (value) => {
  if (!value) return 'n/a'
  return new Date(value).toLocaleString()
}

const resolveUserLabel = (userId) => {
  const user = users.value.find(entry => entry.id === userId)
  return user ? (user.name || user.username || user.id) : userId
}

const inspectQueryRun = async (run) => {
  try {
    selectedQueryRun.value = await api.admin.getQueryRun(run.query_id)
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.query_run_failed', { error: err.message }), 'danger')
  }
}

const closeQueryRunDetail = () => {
  selectedQueryRun.value = null
}

const loadPromptVersion = async (version) => {
  try {
    selectedPromptVersion.value = await api.admin.getPromptVersion(version.id)
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.prompt_version_failed', { error: err.message }), 'danger')
  }
}

const rollbackVersion = async (version) => {
  try {
    await api.admin.rollbackPromptVersion(version.id)
    uiStore.notify(t('admin.dashboard.notifications.prompt_version_rolled_back', { role: version.role, version: version.version_label }), 'success')
    await fetchRuntimeData()
    await loadPromptVersion(version)
  } catch (err) {
    uiStore.notify(t('admin.dashboard.notifications.prompt_version_rollback_failed', { error: err.message }), 'danger')
  }
}

const toggleAllowedRole = (role) => {
  if (mcpForm.allowedRoles.includes(role)) {
    mcpForm.allowedRoles = mcpForm.allowedRoles.filter((item) => item !== role)
    return
  }
  mcpForm.allowedRoles = [...mcpForm.allowedRoles, role]
}

// Scheduler methods
const fetchSchedulerData = async () => {
  try {
    scheduledTasks.value = await api.admin.listScheduledTasks()
  } catch (err) {
    uiStore.notify(err.message, 'danger')
  }
}

const validateCron = () => {
  const expr = schedulerForm.cron.trim()
  if (!expr) {
    cronError.value = ''
    return
  }
  // Standard 5-field cron: minute hour dom month dow
  const parts = expr.split(/\s+/)
  if (parts.length < 5 || parts.length > 6) {
    cronError.value = `Expected 5 fields (min hour dom mon dow), got ${parts.length}`
    return
  }
  // Field ranges
  const ranges = [
    { name: 'minute', min: 0, max: 59 },
    { name: 'hour', min: 0, max: 23 },
    { name: 'day', min: 1, max: 31 },
    { name: 'month', min: 1, max: 12 },
    { name: 'weekday', min: 0, max: 7 },
  ]
  // cron field regex: allows *, */N, N, N-M, N-M/S, and comma-separated values
  const fieldPattern = /^(\*|[0-9]+(-[0-9]+)?)(\/[0-9]+)?(,(\*|[0-9]+(-[0-9]+)?)(\/[0-9]+)?)*$/
  for (let i = 0; i < 5; i++) {
    if (!fieldPattern.test(parts[i])) {
      cronError.value = `Invalid ${ranges[i].name} field: "${parts[i]}"`
      return
    }
  }
  cronError.value = ''
}

const saveScheduledTask = async () => {
  if (!schedulerForm.name || !schedulerForm.cron || !schedulerForm.agent_key) {
    uiStore.notify('Name, cron, and agent key are required.', 'warning')
    return
  }
  // Validate cron before sending
  validateCron()
  if (cronError.value) {
    uiStore.notify(`Invalid cron expression: ${cronError.value}`, 'danger')
    return
  }
  let payload = {}
  try {
    payload = schedulerForm.payloadText.trim() ? JSON.parse(schedulerForm.payloadText) : {}
  } catch {
    uiStore.notify('Invalid JSON in payload.', 'warning')
    return
  }
  const data = {
    name: schedulerForm.name,
    cron: schedulerForm.cron,
    timezone: schedulerForm.timezone,
    agent_key: schedulerForm.agent_key,
    enabled: true,
    payload,
  }
  try {
    if (schedulerEditingId.value) {
      await api.admin.updateScheduledTask(schedulerEditingId.value, data)
      uiStore.notify(`Updated task ${data.name}`, 'success')
    } else {
      await api.admin.createScheduledTask(data)
      uiStore.notify(`Created task ${data.name}`, 'success')
    }
    resetSchedulerForm()
    fetchSchedulerData()
  } catch (err) {
    uiStore.notify(err.message, 'danger')
  }
}

const editScheduledTask = (task) => {
  schedulerEditingId.value = task.id
  Object.assign(schedulerForm, {
    name: task.name,
    cron: task.cron,
    timezone: task.timezone || 'UTC',
    agent_key: task.agent_key,
    payloadText: JSON.stringify(task.payload || {}, null, 2),
  })
}

const toggleTask = async (task) => {
  try {
    await api.admin.toggleScheduledTask(task.id, !task.enabled)
    uiStore.notify(`${task.name} ${task.enabled ? 'disabled' : 'enabled'}`, 'success')
    fetchSchedulerData()
  } catch (err) {
    uiStore.notify(err.message, 'danger')
  }
}

const deleteTask = async (task) => {
  const ok = await uiStore.confirm('Delete Task', `Delete scheduled task "${task.name}"?`)
  if (!ok) return
  try {
    await api.admin.deleteScheduledTask(task.id)
    uiStore.notify(`Deleted task ${task.name}`, 'info')
    if (schedulerEditingId.value === task.id) resetSchedulerForm()
    fetchSchedulerData()
  } catch (err) {
    uiStore.notify(err.message, 'danger')
  }
}

const resetSchedulerForm = () => {
  schedulerEditingId.value = null
  cronError.value = ''
  Object.assign(schedulerForm, {
    name: '',
    cron: '0 8 * * 1',
    timezone: 'UTC',
    agent_key: 'executor',
    payloadText: '{}',
  })
}

const runEngramCompaction = async () => {
  engramCompaction.running = true
  try {
    engramCompaction.result = await api.admin.runEngramCompaction({
      stale_days: engramCompaction.staleDays,
      batch_size: engramCompaction.batchSize,
    })
    uiStore.notify('Engram compaction complete', 'success')
  } catch (err) {
    uiStore.notify(err.message, 'danger')
  } finally {
    engramCompaction.running = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'runtime') fetchRuntimeData()
  if (tab === 'mcp') fetchMcpData()
  if (tab === 'agents') fetchAgentProfiles()
  if (tab === 'scheduler') fetchSchedulerData()
})

onMounted(() => {
  fetchSettings()
  fetchStats()
  fetchUsers()
  fetchAgentProfiles()
})
</script>

<style scoped>
.admin-page-container {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
  overflow: hidden;
}

.admin-sidebar {
  width: 260px;
  border-right: 1px solid var(--border-subtle);
  padding: 24px;
  display: flex;
  flex-direction: column;
  background: var(--bg-glass);
}

.back-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 24px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  border-radius: 12px;
  transition: all 0.2s;
  border: 1px solid transparent;
}
.back-link:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  border-color: var(--border-subtle);
}
.back-link svg {
  opacity: 0.6;
  transition: transform 0.2s;
}
.back-link:hover svg {
  opacity: 1;
  transform: translateX(-3px);
}

.sidebar-brand {
  font-size: 24px;
  font-weight: 900;
  padding: 0 16px 32px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sidebar-brand span:last-child {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 2px;
  opacity: 0.4;
  margin-top: 4px;
}

.admin-nav { display: flex; flex-direction: column; gap: 8px; }
.nav-item {
  display: flex; align-items: center; gap: 14px; padding: 14px 18px; border-radius: 12px;
  background: transparent; border: none; color: var(--text-secondary); font-weight: 700; font-size: 14px;
  cursor: pointer; text-align: left; transition: all 0.2s;
}
.nav-item:hover, .nav-item.active { background: rgba(255,255,255,0.05); color: var(--text-primary); }
.nav-item.active { color: var(--mango-primary); background: rgba(255, 170, 0, 0.05); border: 1px solid rgba(255, 170, 0, 0.1); }
.nav-icon { width: 20px; height: 20px; opacity: 0.7; }
.nav-item.active .nav-icon { opacity: 1; color: var(--mango-primary); }
.nav-icon :deep(svg) { width: 100%; height: 100%; fill: currentColor; }

.sidebar-spacer { flex: 1; }
.status-indicator { display: flex; align-items: center; gap: 10px; font-size: 12px; font-weight: 800; color: var(--success); padding: 16px; }
.pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--success); box-shadow: 0 0 12px var(--success); }

.admin-main { flex: 1; padding: 60px 80px; overflow-y: auto; background: var(--bg-primary); }

.pane-header { margin-bottom: 48px; }
.breadcrumb { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; opacity: 0.4; margin-bottom: 12px; font-weight: 800; }
.pane-header h1 { font-size: 2.5rem; font-weight: 900; margin-bottom: 8px; letter-spacing: -1px; }
.pane-header p { color: var(--text-secondary); font-size: 15px; max-width: 600px; line-height: 1.6; }

.tab-pane { display: flex; flex-direction: column; gap: 48px; max-width: 1200px; }

/* Dashboard Styles */
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }
.stat-card {
  padding: 32px; border-radius: 24px; background: var(--bg-glass); border: 1px solid var(--border-subtle);
  display: flex; flex-direction: column; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}
.stat-label { font-size: 11px; text-transform: uppercase; font-weight: 800; opacity: 0.5; }
.stat-value { font-size: 32px; font-weight: 900; margin-top: 8px; }
.stat-value.accent { color: var(--mango-primary); }

.table-container { border-radius: 16px; overflow: hidden; }
.admin-table { width: 100%; border-collapse: collapse; }
.admin-table th { background: rgba(255,255,255,0.02); padding: 16px; text-align: left; font-size: 11px; opacity: 0.5; text-transform: uppercase; }
.admin-table td { padding: 16px; border-bottom: 1px solid var(--border-subtle); font-size: 13px; }

.u-info { display: flex; flex-direction: column; gap: 2px; }
.u-info span { font-size: 11px; opacity: 0.4; }

.quota-progress-wrapper { width: 100%; max-width: 150px; }
.quota-text { font-size: 10px; font-weight: 800; margin-bottom: 4px; opacity: 0.5; }
.quota-bar { height: 4px; background: rgba(255,255,255,0.05); border-radius: 10px; overflow: hidden; }
.quota-fill { height: 100%; background: var(--mango-primary); }

.action-cell { display: flex; gap: 8px; }
.btn-micro {
  padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border-strong);
  background: transparent; color: var(--text-primary); font-size: 11px; font-weight: 700; cursor: pointer;
}
.btn-micro:hover { background: rgba(255,255,255,0.05); border-color: var(--mango-primary); }
.btn-micro.success { border-color: var(--success); color: var(--success); }
.btn-micro.danger { border-color: var(--danger); color: var(--danger); }

/* Agent Grid */
.agent-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
.agent-config-card { padding: 24px; border-radius: 20px; }
.agent-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
.agent-id {
  background: var(--mango-primary); color: #000; padding: 4px 10px; border-radius: 6px;
  font-size: 11px; font-weight: 900;
}

.input-group label { display: block; font-size: 11px; font-weight: 800; color: var(--mango-primary); text-transform: uppercase; margin-bottom: 8px; }

.field-error {
  font-size: 11px;
  color: #ff5050;
  margin-top: 4px;
  font-weight: 600;
  letter-spacing: 0.3px;
}
.field-hint {
  font-size: 11px;
  color: #50c878;
  margin-top: 4px;
  font-weight: 600;
  opacity: 0.8;
  letter-spacing: 0.3px;
}
.input-error {
  border-color: #ff5050 !important;
  box-shadow: 0 0 0 1px rgba(255, 80, 80, 0.3);
}

.label-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.label-with-action label {
  margin-bottom: 0;
}
.btn-text-action {
  background: transparent;
  border: none;
  color: var(--mango-primary);
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
  opacity: 0.8;
}
.btn-text-action:hover:not(:disabled) {
  opacity: 1;
  background: rgba(var(--mango-primary-rgb, 255, 170, 0), 0.1);
}
.btn-text-action:disabled {
  opacity: 0.4;
  cursor: wait;
}
.row { display: flex; gap: 16px; }
.flex-2 { flex: 2; }
.flex-3 { flex: 3; }

/* Infra */
.infra-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
.infra-panel { padding: 32px; border-radius: 20px; }
.infra-panel h3 { font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 24px; opacity: 0.7; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.toggle-setting { display: flex; justify-content: space-between; align-items: center; padding: 16px; border-radius: 12px; border: 1px dashed var(--border-strong); }
.toggle-info strong { font-size: 14px; display: block; }
.toggle-info p { font-size: 11px; opacity: 0.5; }

.action-bar-sticky {
  position: sticky; bottom: 0; background: var(--bg-primary); padding: 20px 0; border-top: 1px solid var(--border-subtle);
}

.runtime-panel { padding: 28px; border-radius: 20px; }
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}
.section-head h3 {
  font-size: 15px;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 6px;
}
.section-head p {
  font-size: 12px;
  opacity: 0.55;
}
.runtime-list,
.mcp-server-list,
.candidate-table {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.runtime-item,
.mcp-server-item,
.candidate-row,
.insight-card {
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 18px;
  background: rgba(255,255,255,0.02);
}
.runtime-row,
.insight-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}
.runtime-meta {
  font-size: 11px;
  opacity: 0.5;
  margin-top: 4px;
}
.runtime-request,
.candidate-reason {
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.5;
}
.candidate-main {
  flex: 1;
}
.runtime-node-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}
.runtime-node {
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(255, 170, 0, 0.08);
  color: var(--mango-primary);
}
.trace-map {
  margin-top: 24px;
  border: 1px solid var(--border-subtle);
  border-radius: 22px;
  padding: 20px;
  background:
    radial-gradient(circle at top left, rgba(255, 170, 0, 0.08), transparent 32%),
    rgba(255,255,255,0.018);
}
.trace-map-head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  margin-bottom: 18px;
}
.trace-map-head h4 {
  margin: 0 0 6px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.trace-map-head p {
  margin: 0;
  font-size: 12px;
  opacity: 0.55;
}
.trace-legend,
.trace-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.legend-pill,
.trace-chip {
  border-radius: 999px;
  padding: 5px 9px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  border: 1px solid var(--border-subtle);
  background: rgba(255,255,255,0.035);
}
.legend-pill.parallel,
.trace-chip.parallel {
  color: #7dd3fc;
  border-color: rgba(125, 211, 252, 0.35);
  background: rgba(125, 211, 252, 0.08);
}
.legend-pill.verifier,
.trace-chip.verifier,
.trace-chip.reason.valid {
  color: var(--success);
  border-color: rgba(57, 211, 83, 0.35);
  background: rgba(57, 211, 83, 0.08);
}
.legend-pill.retry,
.trace-chip.retry,
.trace-chip.reason.warning {
  color: var(--warning);
  border-color: rgba(255, 170, 0, 0.4);
  background: rgba(255, 170, 0, 0.09);
}
.trace-chip.reason.critical {
  color: var(--danger);
  border-color: rgba(255, 80, 80, 0.4);
  background: rgba(255, 80, 80, 0.09);
}
.trace-group-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.trace-group {
  position: relative;
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 16px;
}
.trace-group::before {
  content: "";
  position: absolute;
  left: 139px;
  top: 12px;
  bottom: -18px;
  width: 1px;
  background: linear-gradient(to bottom, var(--border-strong), transparent);
}
.trace-group:last-child::before {
  display: none;
}
.trace-group-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--mango-primary);
  font-size: 11px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.7px;
}
.trace-group-label small {
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 700;
  opacity: 0.55;
}
.trace-group-nodes {
  display: grid;
  gap: 14px;
}
.trace-group-nodes.parallel {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}
.trace-node-card {
  position: relative;
  border: 1px solid var(--border-subtle);
  border-radius: 18px;
  padding: 16px;
  background: rgba(10, 12, 16, 0.42);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}
.trace-node-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  border-radius: 18px 0 0 18px;
  background: var(--mango-primary);
  opacity: 0.7;
}
.trace-node-card.parallel::before { background: #7dd3fc; }
.trace-node-card.verifier::before { background: var(--success); }
.trace-node-card.retry::before,
.trace-node-card.warning::before { background: var(--warning); }
.trace-node-card.critical::before,
.trace-node-card.failed::before { background: var(--danger); }
.trace-node-card.skipped { opacity: 0.65; }
.trace-node-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.trace-node-title {
  font-size: 14px;
  font-weight: 900;
}
.verifier-feedback {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 170, 0, 0.18);
  background: rgba(255, 170, 0, 0.05);
  font-size: 12px;
  line-height: 1.45;
}
.trace-input,
.trace-output pre,
.trace-event pre {
  margin-top: 12px;
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
  background: rgba(0,0,0,0.2);
  padding: 12px;
  font-size: 11px;
  line-height: 1.45;
  color: var(--text-secondary);
}
.trace-events {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}
.trace-event {
  border-radius: 12px;
  border: 1px dashed var(--border-subtle);
  padding: 10px;
}
.trace-output {
  margin-top: 12px;
  font-size: 12px;
}
.trace-output summary {
  cursor: pointer;
  color: var(--mango-primary);
  font-weight: 800;
}
.insight-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.insight-block {
  margin-top: 14px;
}
.insight-block label {
  display: block;
  margin-bottom: 8px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  opacity: 0.55;
}
.insight-block ul {
  margin: 0;
  padding-left: 18px;
}
.insight-block li {
  margin-bottom: 6px;
  font-size: 12px;
  line-height: 1.4;
}
.insight-block.muted li {
  opacity: 0.7;
}
.empty-state {
  padding: 18px;
  border: 1px dashed var(--border-strong);
  border-radius: 14px;
  font-size: 12px;
  opacity: 0.6;
}
.mcp-form-grid .full-span {
  grid-column: 1 / -1;
}
textarea {
  width: 100%;
  resize: vertical;
  min-height: 110px;
  border-radius: 12px;
  border: 1px solid var(--border-strong);
  background: rgba(255,255,255,0.03);
  color: var(--text-primary);
  padding: 12px 14px;
}
.action-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

/* Godmode */
.godmode-warning {
  padding: 24px; border-radius: 16px; display: flex; align-items: center; gap: 24px;
  border: 1px solid var(--warning); background: rgba(255, 170, 0, 0.05); color: var(--warning);
}
.warning-icon { font-size: 2rem; }
.audit-grid { display: flex; flex-direction: column; gap: 12px; }
.audit-strip { padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }
.u-brief { display: flex; flex-direction: column; }
.u-brief span { font-size: 11px; opacity: 0.5; }
.audit-stats { display: flex; gap: 32px; }
.a-stat { display: flex; flex-direction: column; align-items: center; }
.a-stat span { font-size: 10px; opacity: 0.4; text-transform: uppercase; }
.a-stat strong { font-size: 14px; }

.scrollable { overflow-y: auto; }
.mt-3 { margin-top: 12px; }
.mt-4 { margin-top: 16px; }
.mt-6 { margin-top: 24px; }
</style>
