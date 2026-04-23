<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { api } from '../services/api'
import { useUIStore } from '../stores/ui'
import CSelect from './common/CSelect.vue'

const props = defineProps({
  prompts: {
    type: Array,
    default: () => []
  },
  versions: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['refresh'])
const uiStore = useUIStore()

const selectedRole = ref('')
const mutationReason = ref('manual_titan_edit')
const draftContent = ref('')
const loading = ref(false)
const showDiffMode = ref(false)
const diffBase = ref({ label: '', content: '' })
const diffTarget = ref({ label: '', content: '' })
const editorContainer = ref(null)
const diffEditorContainer = ref(null)
const monacoLoading = ref(true)
const monacoFailed = ref(false)
const diffLoading = ref(false)
let monacoEditor = null
let monacoDiffEditor = null

const roleOptions = computed(() => props.prompts.map(prompt => prompt.role))
const filteredVersions = computed(() => props.versions.filter(version => version.role === selectedRole.value))

watch(roleOptions, (roles) => {
  if (!selectedRole.value && roles.length) {
    selectedRole.value = roles[0]
  }
}, { immediate: true })

watch([selectedRole, () => props.versions], async () => {
  const active = filteredVersions.value.find(version => version.status === 'active') || filteredVersions.value[0]
  if (!active) return
  try {
    const detail = await api.admin.getPromptVersion(active.id)
    draftContent.value = detail.content || ''
    if (monacoEditor) {
      monacoEditor.setValue(draftContent.value)
    }
  } catch (error) {
    uiStore.notify(error.message, 'danger')
  }
}, { immediate: true })

const initMonacoEditor = async () => {
  if (!editorContainer.value) return
  monacoLoading.value = true
  monacoFailed.value = false
  try {
    const monaco = await import('monaco-editor')
    monacoEditor = monaco.editor.create(editorContainer.value, {
      value: draftContent.value,
      language: 'markdown',
      theme: uiStore.theme === 'dark' ? 'vs-dark' : 'vs',
      minimap: { enabled: false },
      wordWrap: 'on',
      lineNumbers: 'on',
      fontSize: 13,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
      scrollBeyondLastLine: false,
      automaticLayout: true,
      padding: { top: 12 },
      renderLineHighlight: 'none',
    })
    monacoEditor.onDidChangeModelContent(() => {
      draftContent.value = monacoEditor.getValue()
    })
    monacoLoading.value = false
  } catch (e) {
    monacoLoading.value = false
    monacoFailed.value = true
  }
}

const initDiffEditor = async (baseContent, targetContent, baseLabel, targetLabel) => {
  await nextTick()
  if (!diffEditorContainer.value) return
  diffLoading.value = true
  try {
    const monaco = await import('monaco-editor')
    if (monacoDiffEditor) {
      monacoDiffEditor.dispose()
      monacoDiffEditor = null
    }
    monacoDiffEditor = monaco.editor.createDiffEditor(diffEditorContainer.value, {
      theme: uiStore.theme === 'dark' ? 'vs-dark' : 'vs',
      readOnly: true,
      renderSideBySide: true,
      minimap: { enabled: false },
      wordWrap: 'on',
      fontSize: 13,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
      scrollBeyondLastLine: false,
      automaticLayout: true,
      padding: { top: 12 },
    })
    monacoDiffEditor.setModel({
      original: monaco.editor.createModel(baseContent, 'markdown'),
      modified: monaco.editor.createModel(targetContent, 'markdown'),
    })
    diffLoading.value = false
  } catch (e) {
    diffLoading.value = false
  }
}

onMounted(() => {
  initMonacoEditor()
})

onBeforeUnmount(() => {
  if (monacoEditor) {
    monacoEditor.dispose()
    monacoEditor = null
  }
  if (monacoDiffEditor) {
    monacoDiffEditor.dispose()
    monacoDiffEditor = null
  }
})

const saveDraft = async () => {
  if (!selectedRole.value || !draftContent.value.trim()) return
  loading.value = true
  try {
    await api.admin.createPromptVersion(selectedRole.value, {
      content: draftContent.value,
      mutation_reason: mutationReason.value,
    })
    uiStore.notify(`Prompt version created for ${selectedRole.value}`, 'success')
    emit('refresh')
  } catch (error) {
    uiStore.notify(error.message, 'danger')
  } finally {
    loading.value = false
  }
}

const activateVersion = async (version) => {
  try {
    await api.admin.activatePromptVersion(version.id)
    uiStore.notify(`Activated ${version.version_label}`, 'success')
    emit('refresh')
  } catch (error) {
    uiStore.notify(error.message, 'danger')
  }
}

const inspectVersion = async (version) => {
  try {
    const detail = await api.admin.getPromptDiff(version.id)
    draftContent.value = detail.content || ''
    if (monacoEditor) {
      monacoEditor.setValue(draftContent.value)
    }
  } catch (error) {
    uiStore.notify(error.message, 'danger')
  }
}

const showVersionDiff = async (version) => {
  try {
    const detail = await api.admin.getPromptDiff(version.id)
    const targetContent = detail.content || ''

    // Find the previous version to compare against
    const versions = filteredVersions.value
    const idx = versions.findIndex(v => v.id === version.id)
    let baseContent = ''
    let baseLabel = 'previous'

    if (idx >= 0 && idx < versions.length - 1) {
      // Load the next version in the list (older)
      const prevVersion = versions[idx + 1]
      try {
        const prevDetail = await api.admin.getPromptDiff(prevVersion.id)
        baseContent = prevDetail.content || ''
        baseLabel = prevVersion.version_label
      } catch {
        baseContent = ''
      }
    }

    diffBase.value = { label: baseLabel, content: baseContent }
    diffTarget.value = { label: version.version_label, content: targetContent }
    showDiffMode.value = true

    await initDiffEditor(baseContent, targetContent, baseLabel, version.version_label)
  } catch (error) {
    uiStore.notify(error.message, 'danger')
  }
}

const closeDiffMode = () => {
  showDiffMode.value = false
  if (monacoDiffEditor) {
    monacoDiffEditor.dispose()
    monacoDiffEditor = null
  }
}

const rollbackToVersion = async (version) => {
  try {
    await api.admin.rollbackPromptVersion(version.id)
    uiStore.notify(`Rolled back to ${version.version_label}`, 'success')
    emit('refresh')
  } catch (error) {
    uiStore.notify(error.message, 'danger')
  }
}
</script>

<template>
  <section class="glass-panel prompt-editor">
    <div class="section-head">
      <div>
        <h3>Prompt Editor</h3>
        <p>Database-backed prompt versions with Monaco diff comparison and rollback-safe edits.</p>
      </div>
    </div>
    <div class="prompt-grid">
      <div class="input-group">
        <label>Prompt Family</label>
        <CSelect v-model="selectedRole" :options="roleOptions.map(r => ({ label: r, value: r }))" />
      </div>
      <div class="input-group">
        <label>Mutation Reason</label>
        <input v-model="mutationReason" />
      </div>
    </div>

    <!-- Diff Viewer Overlay -->
    <transition name="menu-pop">
      <div v-if="showDiffMode" class="diff-overlay">
        <div class="diff-header">
          <div class="diff-labels">
            <span class="diff-label base">{{ diffBase.label }}</span>
            <span class="diff-arrow">&rarr;</span>
            <span class="diff-label target">{{ diffTarget.label }}</span>
          </div>
          <button class="btn-micro" @click="closeDiffMode">Close</button>
        </div>
        <!-- Diff Loading Skeleton -->
        <div v-if="diffLoading" class="editor-skeleton">
          <div class="skeleton-pulse"></div>
          <div class="skeleton-text">Loading diff editor...</div>
        </div>
        <div ref="diffEditorContainer" class="diff-editor-container" v-show="!diffLoading"></div>
        <!-- Fallback if Monaco not loaded -->
        <div v-if="!diffEditorContainer && !diffLoading" class="diff-fallback">
          <div class="diff-panel">
            <label>{{ diffBase.label }}</label>
            <pre>{{ diffBase.content }}</pre>
          </div>
          <div class="diff-panel">
            <label>{{ diffTarget.label }}</label>
            <pre>{{ diffTarget.content }}</pre>
          </div>
        </div>
      </div>
    </transition>

    <div class="prompt-layout" v-show="!showDiffMode">
      <div class="editor-wrapper">
        <!-- Monaco Loading Skeleton -->
        <div v-if="monacoLoading" class="editor-skeleton">
          <div class="skeleton-pulse"></div>
          <div class="skeleton-shimmer">
            <div class="shimmer-line" v-for="n in 12" :key="n" :style="{ width: (40 + Math.random() * 55) + '%', animationDelay: (n * 0.06) + 's' }"></div>
          </div>
          <div class="skeleton-text">Loading editor...</div>
        </div>
        <div ref="editorContainer" class="monaco-editor-container" v-show="!monacoLoading && !monacoFailed"></div>
        <!-- Fallback textarea if Monaco fails to load -->
        <textarea v-if="monacoFailed" v-model="draftContent" class="prompt-textarea" spellcheck="false"></textarea>
      </div>
      <div class="prompt-versions">
        <div v-for="version in filteredVersions" :key="version.id" class="prompt-version-item">
          <div>
            <strong>{{ version.version_label }}</strong>
            <div class="runtime-meta">{{ version.status }} · {{ version.mutation_reason }}</div>
          </div>
          <div class="action-cell">
            <button class="btn-micro" @click="inspectVersion(version)">Load</button>
            <button class="btn-micro diff-btn" @click="showVersionDiff(version)">Diff</button>
            <button v-if="version.status !== 'active'" class="btn-micro success" @click="activateVersion(version)">Activate</button>
            <button v-if="version.status !== 'active'" class="btn-micro danger" @click="rollbackToVersion(version)">Rollback</button>
          </div>
        </div>
      </div>
    </div>
    <div class="action-bar-sticky">
      <button class="mango-button" :disabled="loading" @click="saveDraft">{{ loading ? 'Saving...' : 'Create Version' }}</button>
    </div>
  </section>
</template>

<style scoped>
.prompt-editor {
  margin-top: 24px;
  padding: 20px;
}

.prompt-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.prompt-layout {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
  gap: 16px;
}

.editor-wrapper {
  position: relative;
  min-height: 420px;
}

.monaco-editor-container {
  min-height: 420px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

.prompt-textarea {
  min-height: 420px;
  width: 100%;
  resize: vertical;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
  color: var(--text-primary);
  padding: 14px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

/* ── Skeleton Loading State ── */
.editor-skeleton {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 420px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
  position: relative;
  overflow: hidden;
}

.skeleton-pulse {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(var(--mango-primary-rgb, 255, 170, 0), 0.04) 40%,
    rgba(var(--mango-primary-rgb, 255, 170, 0), 0.08) 50%,
    rgba(var(--mango-primary-rgb, 255, 170, 0), 0.04) 60%,
    transparent 100%
  );
  animation: skeleton-sweep 2s ease-in-out infinite;
}

.skeleton-shimmer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 24px;
  width: 100%;
  z-index: 1;
}

.shimmer-line {
  height: 12px;
  border-radius: 4px;
  background: var(--border-subtle);
  opacity: 0.4;
  animation: shimmer-fade 1.5s ease-in-out infinite alternate;
}

.skeleton-text {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--text-secondary);
  opacity: 0.5;
  z-index: 1;
  margin-top: 12px;
  animation: skeleton-text-pulse 2s ease-in-out infinite;
}

@keyframes skeleton-sweep {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@keyframes shimmer-fade {
  0% { opacity: 0.2; }
  100% { opacity: 0.5; }
}

@keyframes skeleton-text-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}

/* ── Version List ── */
.prompt-versions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow: auto;
}

.prompt-version-item {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  background: var(--bg-secondary);
}

.action-cell {
  display: flex;
  gap: 4px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.diff-btn {
  border-color: var(--mango-primary) !important;
  color: var(--mango-primary) !important;
}

/* Diff Overlay */
.diff-overlay {
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 16px;
  background: var(--bg-secondary);
}

.diff-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-tertiary);
}

.diff-labels {
  display: flex;
  align-items: center;
  gap: 12px;
}

.diff-label {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.diff-label.base {
  background: rgba(255, 80, 80, 0.15);
  color: #ff5050;
  border: 1px solid rgba(255, 80, 80, 0.3);
}

.diff-label.target {
  background: rgba(80, 255, 136, 0.15);
  color: #50ff88;
  border: 1px solid rgba(80, 255, 136, 0.3);
}

.diff-arrow {
  font-size: 16px;
  opacity: 0.4;
  font-weight: 900;
}

.diff-editor-container {
  height: 500px;
  width: 100%;
}

.diff-fallback {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}

.diff-panel {
  padding: 14px;
  border-right: 1px solid var(--border-subtle);
  overflow: auto;
  max-height: 400px;
}

.diff-panel:last-child {
  border-right: none;
}

.diff-panel label {
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  opacity: 0.5;
  margin-bottom: 8px;
  display: block;
}

.diff-panel pre {
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 960px) {
  .prompt-grid,
  .prompt-layout {
    grid-template-columns: 1fr;
  }
}
</style>
