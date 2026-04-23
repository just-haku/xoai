<template>
  <div class="model-selector-container" v-click-outside="close" ref="containerRef">
    <div v-if="label" class="selector-label">{{ label }}</div>
    <div class="selector-trigger" :class="{ locked: !hasApiKey, open: isOpen }" @click="toggleDropdown" ref="triggerRef">
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
    
    <teleport to="body">
      <transition name="menu-pop">
        <div 
          v-if="isOpen && hasApiKey" 
          class="dropdown-menu glass-panel shadow-premium"
          :style="dropdownStyle"
        >
          <div v-for="group in modelGroups" :key="group.provider" class="model-group">
            <label>{{ group.provider }}</label>
            <div v-for="model in group.models" :key="model" 
                 class="model-option" 
                 :class="{ active: selectedModel === model }"
                 @click="selectModel(model)">
              {{ model }}
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useUIStore } from '../stores/ui'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  label: String
})

const uiStore = useUIStore()
const { t } = useI18n()
const selectedModel = ref('(none)')
const isOpen = ref(false)
const loadingModels = ref(false)
const modelGroups = ref([{ provider: 'None', models: ['(none)'] }])

const triggerRef = ref(null)
const dropdownPos = ref({ top: 0, left: 0, width: 0, placement: 'top' })

const hasApiKey = computed(() => {
  return !!localStorage.getItem('xoai_key') 
})

const dropdownStyle = computed(() => ({
  position: 'fixed',
  top: `${dropdownPos.value.top}px`,
  left: `${dropdownPos.value.left}px`,
  width: `${dropdownPos.value.width}px`,
  zIndex: 10001,
  transform: dropdownPos.value.placement === 'top' ? 'translateY(-100%) translateY(-12px)' : 'none'
}))

const updatePosition = () => {
  if (!triggerRef.value) return
  const rect = triggerRef.value.getBoundingClientRect()
  
  // ModelSelector usually opens UPWARDS in the Chat View (bottom bar)
  // But let's make it smart.
  const spaceBottom = window.innerHeight - rect.bottom
  const dropdownHeight = 350
  
  let top, placement
  if (spaceBottom < dropdownHeight && rect.top > dropdownHeight) {
    top = rect.top
    placement = 'top'
  } else {
    top = rect.bottom + 8
    placement = 'bottom'
  }

  dropdownPos.value = {
    top,
    left: rect.left,
    width: Math.max(220, rect.width),
    placement
  }
}

const fetchModels = async () => {
  if (!hasApiKey.value) return
  loadingModels.value = true
  try {
    // Simulated fetch - in production this would call api.users.getModels()
    setTimeout(() => {
      modelGroups.value = [
        { provider: 'None', models: ['(none)'] },
        { provider: 'Google', models: ['gemini-1.5-pro', 'gemini-1.5-flash', 'text-embedding-004'] },
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

const toggleDropdown = async () => {
  if (!hasApiKey.value) {
    uiStore.notify(t('chat.identity_required'), 'warning')
    return
  }
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    await nextTick()
    updatePosition()
  }
}

const close = () => {
  isOpen.value = false
}

const selectModel = (model) => {
  selectedModel.value = model
  close()
}

const handleScrollResize = () => {
  if (isOpen.value) close()
}

watch(isOpen, (val) => {
  if (val) {
    window.addEventListener('scroll', handleScrollResize, true)
    window.addEventListener('resize', handleScrollResize)
  } else {
    window.removeEventListener('scroll', handleScrollResize, true)
    window.removeEventListener('resize', handleScrollResize)
  }
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScrollResize, true)
  window.removeEventListener('resize', handleScrollResize)
})

const vClickOutside = {
  mounted(el, binding) {
    el.clickOutsideEvent = (event) => {
      if (!(el === event.target || el.contains(event.target)) && !event.target.closest('.dropdown-menu')) {
        binding.value()
      }
    }
    document.addEventListener('click', el.clickOutsideEvent)
  },
  unmounted(el) {
    document.removeEventListener('click', el.clickOutsideEvent)
  }
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
  background: rgba(var(--bg-rgb, 10, 10, 12), 0.05);
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
  max-width: 130px;
  font-weight: 600;
}

.selector-trigger:hover:not(.locked) {
  background: rgba(var(--bg-rgb, 10, 10, 12), 0.1);
  border-color: var(--mango-primary);
}

.selector-trigger.open {
  border-color: var(--mango-primary);
  box-shadow: 0 0 0 2px var(--mango-glow);
}

.selector-trigger.locked {
  opacity: 0.5;
  cursor: not-allowed;
  background: rgba(255, 0, 0, 0.02);
}

.dropdown-menu {
  /* position: fixed is applied via :style */
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
  border-radius: 16px;
  border: 1px solid var(--border-strong);
  background: var(--bg-glass);
  backdrop-filter: blur(40px);
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
  background: var(--glass-hover);
  color: var(--mango-primary);
}

.model-option.active {
  background: var(--mango-primary);
  color: white;
  font-weight: 700;
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

/* Transitions */
.menu-pop-enter-active, .menu-pop-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.menu-pop-enter-from, .menu-pop-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(10px) !important;
}
</style>
