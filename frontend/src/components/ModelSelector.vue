<template>
  <div class="model-selector-container">
    <div v-if="label" class="selector-label">{{ label }}</div>
    <div class="selector-trigger" :class="{ locked: !hasApiKey }" @click="toggleDropdown">
      <span class="provider-icon">
        <svg v-if="hasApiKey" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8 0-.29.02-.58.05-.86 2.36-1.05 4.23-2.98 5.21-5.37C11.07 8.33 14.05 10 17.42 10c.78 0 1.53-.09 2.25-.26.21.41.33.88.33 1.37 0 4.41-3.59 8-8 8z"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
          <path d="M12 17c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6-9h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zM8.9 6c0-1.71 1.39-3.1 3.1-3.1s3.1 1.39 3.1 3.1v2H8.9V6zM18 20H6V10h12v10z"/>
        </svg>
      </span>
      <span class="model-name">
        <template v-if="loadingModels">{{ $t('chat.loading_models') }}</template>
        <template v-else>{{ hasApiKey ? selectedModel : $t('chat.locked') }}</template>
      </span>
      <span class="chevron" :class="{ open: isOpen }" v-if="hasApiKey">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M7 10l5 5 5-5H7z"/></svg>
      </span>
    </div>
    
    <div v-if="isOpen && hasApiKey" class="dropdown-menu glass-panel shadow-premium">
      <div v-for="group in modelGroups" :key="group.provider" class="model-group">
        <label>{{ group.provider }}</label>
        <div v-for="model in group.models" :key="model" 
             class="model-option" 
             @click="selectModel(model)">
          {{ model }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUIStore } from '../stores/ui'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  label: String
})

const uiStore = useUIStore()
const { t } = useI18n()
const selectedModel = ref('(none)')
const isOpen = ref(false)

const hasApiKey = computed(() => {
  return !!localStorage.getItem('xoai_key') 
})

const modelGroups = ref([
  { provider: 'None', models: ['(none)'] }
])

const loadingModels = ref(false)
const fetchModels = async () => {
  if (!hasApiKey.value) return
  loadingModels.value = true
  try {
    // Simulated fetch
    setTimeout(() => {
      modelGroups.value = [
        { provider: 'None', models: ['(none)'] },
        { provider: 'Google', models: ['gemini-1.5-pro', 'gemini-1.5-flash'] },
        { provider: 'OpenAI', models: ['gpt-4o', 'gpt-4-turbo'] },
        { provider: 'Anthropic', models: ['claude-3-opus', 'claude-3-sonnet'] }
      ]
      loadingModels.value = false
    }, 800)
  } catch (err) {
    loadingModels.value = false
  }
}

onMounted(fetchModels)

const toggleDropdown = () => {
  if (!hasApiKey.value) {
    uiStore.notify(t('chat.identity_required'), 'warning')
    return
  }
  isOpen.value = !isOpen.value
}

const selectModel = (model) => {
  selectedModel.value = model
  isOpen.value = false
}
</script>

<style scoped>
.model-selector-container {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector-label {
  font-size: 11px;
  font-weight: 900;
  color: var(--mango-primary);
  opacity: 0.8;
}

.selector-trigger {
  padding: 8px 12px;
  background: rgba(var(--bg-rgb), 0.05);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  transition: all 0.2s;
  min-width: 160px;
  color: var(--text-primary);
}

.model-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 110px;
  font-weight: 600;
}

.selector-trigger:hover:not(.locked) {
  background: rgba(var(--bg-rgb), 0.1);
  border-color: var(--mango-primary);
}

.selector-trigger.locked {
  opacity: 0.5;
  cursor: not-allowed;
  background: rgba(255, 0, 0, 0.02);
}

.dropdown-menu {
  position: absolute;
  bottom: 120%;
  right: 0;
  width: 220px;
  z-index: 5000;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
  border-radius: 16px;
  border: 1px solid var(--border-strong);
}

.model-group label {
  display: block;
  font-size: 10px;
  text-transform: uppercase;
  color: var(--mango-primary);
  margin: 12px 8px 4px;
  font-weight: 900;
  opacity: 0.6;
}

.model-option {
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  color: var(--text-primary);
}

.model-option:hover {
  background: var(--mango-primary);
  color: white;
}

.chevron {
  margin-left: auto;
  font-size: 10px;
  opacity: 0.4;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.chevron.open {
  transform: rotate(180deg);
}
</style>
