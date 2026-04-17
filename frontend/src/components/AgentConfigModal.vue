<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="close">
    <div class="modal-content glass-panel">
      <div class="modal-header">
        <div class="agent-info">
          <div class="cog-icon-large" :class="{ spinning: isSaving }">
             <svg viewBox="0 0 24 24"><path d="M12,15.5H12V15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.35 19.43,11.03L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.47,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.53,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11.03C4.53,11.35 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.04 4.95,18.95L7.44,17.95C7.96,18.34 8.53,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.47,18.68 16.04,18.34 16.56,17.95L19.05,18.95C19.27,19.04 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" /></svg>
          </div>
          <div class="text">
            <h2>{{ agent.name }} Configuration</h2>
            <p>Set independent intelligence parameters for {{ agent.shortName }}.</p>
          </div>
        </div>
        <button class="close-btn" @click="close">×</button>
      </div>

      <div class="modal-body">
        <div class="setting-item">
          <label>AI Provider</label>
          <CSelect 
            v-model="config.provider" 
            :options="providerOptions"
          />
        </div>

        <div class="setting-item">
          <label>Model ID</label>
          <input v-model="config.model" placeholder="e.g. gemini-1.5-pro" />
        </div>

        <div class="setting-item">
          <label>Agent-Specific API Key</label>
          <div class="input-reveal">
            <input :type="showKey ? 'text' : 'password'" v-model="config.apiKey" placeholder="Leave empty to use global key" />
            <button class="btn-text-action" @click="showKey = !showKey">
              {{ showKey ? 'HIDE' : 'SHOW' }}
            </button>
          </div>
        </div>

        <div class="setting-item">
          <label>System Prompt Override</label>
          <textarea v-model="config.systemPrompt" rows="4" :placeholder="`Implicit instructions for ${agent.name}...`"></textarea>
        </div>
      </div>

      <div class="modal-footer">
        <button class="cancel-btn" @click="close">Cancel</button>
        <button class="mango-button" @click="save" :disabled="isSaving">
          {{ isSaving ? 'Saving...' : 'Save Configuration' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import CSelect from './common/CSelect.vue'

const props = defineProps(['isOpen', 'agent', 'initialConfig'])
const emit = defineEmits(['close', 'save'])

const providerOptions = [
  { label: 'Google Gemini', value: 'gemini' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Ollama (Local)', value: 'ollama' }
]

const config = ref({
  provider: 'gemini',
  model: '',
  apiKey: '',
  systemPrompt: ''
})
const showKey = ref(false)
const isSaving = ref(false)

watch(() => props.isOpen, (val) => {
  if (val && props.initialConfig) {
    config.value = { ...props.initialConfig }
  }
})

const close = () => {
  emit('close')
}

const save = async () => {
  isSaving.value = true
  // Mock API delay
  await new Promise(r => setTimeout(r, 800))
  emit('save', { agentId: props.agent.id, config: config.value })
  isSaving.value = false
  close()
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(8px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  width: 100%;
  max-width: 500px;
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.agent-info {
  display: flex;
  gap: 16px;
  align-items: center;
}

.cog-icon-large {
  width: 48px;
  height: 48px;
  color: var(--mango-primary);
}

.cog-icon-large svg { fill: currentColor; }

.cog-icon-large.spinning svg {
  animation: spin 2s linear infinite;
}

.text h2 { margin: 0; font-size: 1.25rem; }
.text p { margin: 4px 0 0; font-size: 0.9rem; opacity: 0.6; }

.close-btn { background: none; border: none; font-size: 2rem; color: var(--text-primary); opacity: 0.5; cursor: pointer; }
.close-btn:hover { opacity: 1; }

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-item label {
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 800;
  opacity: 0.5;
  letter-spacing: 0.05rem;
}

input, select, textarea {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  padding: 12px;
  border-radius: 10px;
  color: white;
  font-size: 14px;
  outline: none;
}

input:focus, select:focus, textarea:focus {
  border-color: var(--mango-primary);
}

.input-reveal {
  display: flex;
  gap: 8px;
}
.input-reveal input { flex: 1; }
.input-reveal button { background: none; border: none; cursor: pointer; font-size: 1.2rem; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.cancel-btn {
  background: transparent;
  border: none;
  color: var(--text-primary);
  opacity: 0.6;
  cursor: pointer;
  font-size: 14px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
