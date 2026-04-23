<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUIStore } from '../stores/ui'

const { t } = useI18n()
const uiStore = useUIStore()

// Requirement: Default models are none. Only fetch when keys are input.
const triad = ref([
  { id: 'a0', name: 'Supervisor', shortName: 'A0', provider: '', model: '', open: false },
  { id: 'a1', name: 'Architect', shortName: 'A1', provider: '', model: '', open: false },
  { id: 'a2', name: 'Executor', shortName: 'A2', provider: '', model: '', open: false }
])

const providers = ref({})
const loadingModels = ref(false)

const fetchModels = async () => {
  if (!hasApiKey.value) return
  loadingModels.value = true
  try {
    // Simulated API call - would call api.models.list()
    setTimeout(() => {
      providers.value = {
        gemini: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-1.0-ultra'],
        openai: ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
        anthropic: ['claude-3-opus', 'claude-3-sonnet'],
        local: ['mistral-7b', 'llama-3-8b']
      }
      loadingModels.value = false
    }, 800)
  } catch (err) {
    uiStore.notify('Failed to fetch models', 'error')
    loadingModels.value = false
  }
}

// Check for API keys in local storage (or uiStore)
const hasApiKey = computed(() => {
  return !!localStorage.getItem('xoai_key') 
})

const toggleMenu = (agent) => {
  if (!hasApiKey.value) {
    uiStore.notify(t('chat.missing_key'), 'warning')
    return
  }
  // Close others
  triad.value.forEach(a => { if(a.id !== agent.id) a.open = false })
  agent.open = !agent.open
}

const selectModel = (agent, provider, model) => {
  agent.provider = provider
  agent.model = model
  agent.open = false
  
  uiStore.notify(t('chat.agent_using', { agent: agent.shortName, model: model, provider: provider }), 'info')
}

onMounted(() => {
  fetchModels()
  window.addEventListener('click', () => {
    triad.value.forEach(a => a.open = false)
  })
})
</script>

<template>
  <div class="tool-cog-wrapper" @click.stop>
    <div class="triad-status">
      <div v-for="agent in triad" :key="agent.id" 
           class="agent-cog-container" 
           :class="[agent.provider, { active: agent.open, locked: !hasApiKey }]"
           @click.stop="toggleMenu(agent)">
        
        <div class="cog-icon">
          <svg viewBox="0 0 24 24" class="cog-svg">
            <path v-if="hasApiKey" d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.35 19.43,11.03L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.47,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.53,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11.03C4.53,11.35 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.04 4.95,18.95L7.44,17.95C7.96,18.34 8.53,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.47,18.68 16.04,18.34 16.56,17.95L19.05,18.95C19.27,19.04 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" />
            <path v-else d="M12,17A2,2 0 0,0 14,15C14,13.89 13.1,13 12,13A2,2 0 0,0 10,15A2,2 0 0,0 12,17M18,8H17V6A5,5 0 0,0 12,1A5,5 0 0,0 7,6V8H6A2,2 0 0,0 4,10V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V10A2,2 0 0,0 18,8M9,6A3,3 0 0,1 12,3A3,3 0 0,1 15,6V8H9V6Z" />
          </svg>
        </div>
        <div class="agent-info">
          <span class="agent-label">{{ agent.shortName }}</span>
          <span class="active-model">
            <template v-if="loadingModels">{{ t('chat.loading_models') }}</template>
            <template v-else>{{ hasApiKey ? (agent.model || t('chat.model_none')) : t('chat.locked') }}</template>
          </span>
        </div>

        <transition name="menu-pop">
           <div v-if="agent.open && hasApiKey" class="model-dropdown glass-panel">
              <div v-for="(models, prov) in providers" :key="prov" class="prov-section">
                 <div class="prov-header">{{ prov }}</div>
                 <div v-for="m in models" :key="m" class="model-option" @click="selectModel(agent, prov, m)">
                    {{ m }}
                 </div>
              </div>
           </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tool-cog-wrapper { padding: 4px 8px; background: rgba(0, 0, 0, 0.1); border-radius: 16px; border: 1px solid var(--border-subtle); }
.triad-status { display: flex; gap: 8px; }

.agent-cog-container {
  display: flex; align-items: center; gap: 8px; padding: 4px 12px; border-radius: 12px;
  cursor: pointer; position: relative; transition: all 0.2s; border: 1px solid transparent;
}

.agent-cog-container:hover:not(.locked) { background: rgba(255,255,255,0.05); }
.agent-cog-container.active { background: rgba(255, 170, 0, 0.1); border-color: var(--mango-primary); }
.agent-cog-container.locked { opacity: 0.5; cursor: not-allowed; }

.cog-icon { width: 16px; height: 16px; color: var(--text-secondary); }
.cog-svg { fill: currentColor; }

.agent-info { display: flex; flex-direction: column; }
.agent-label { font-size: 10px; font-weight: 900; opacity: 0.8; color: var(--text-primary); }
.active-model { font-size: 9px; opacity: 0.4; font-weight: 700; color: var(--text-primary); }

.active .cog-icon { color: var(--mango-primary); animation: spin 8s linear infinite; }

/* Dropdown */
.model-dropdown {
  position: absolute; top: calc(100% + 12px); left: 0; min-width: 180px;
  z-index: 5000; padding: 12px; border-radius: 16px; border: 1px solid var(--border-strong);
  box-shadow: 0 20px 50px rgba(0,0,0,0.5);
}

.prov-section { margin-bottom: 12px; }
.prov-header { font-size: 9px; opacity: 0.4; font-weight: 900; text-transform: uppercase; margin-bottom: 4px; padding-left: 8px; color: var(--text-primary); }

.model-option {
  padding: 8px 12px; border-radius: 8px; font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all 0.2s; color: var(--text-primary);
}
.model-option:hover { background: var(--mango-primary); color: white; }

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Menu Transition */
.menu-pop-enter-active, .menu-pop-leave-active { transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); }
.menu-pop-enter-from, .menu-pop-leave-to { opacity: 0; transform: translateY(-10px); }
</style>
