<template>
  <div class="c-select-container" v-click-outside="close" ref="containerRef">
    <div 
      class="c-select-trigger" 
      :class="{ open: isOpen, disabled: disabled }"
      @click="toggle"
      ref="triggerRef"
    >
      <span class="c-select-value">{{ selectedLabel || placeholder }}</span>
      <svg class="c-select-chevron" viewBox="0 0 24 24">
        <path d="M7 10l5 5 5-5H7z" fill="currentColor"/>
      </svg>
    </div>

    <teleport to="body">
      <transition name="fade-slide">
        <div 
          v-if="isOpen" 
          class="c-select-dropdown glass-panel shadow-premium"
          :style="dropdownStyle"
          ref="dropdownRef"
        >
          <!-- Search Input -->
          <div class="c-select-search-wrap">
            <input 
              v-model="searchQuery" 
              class="c-select-search" 
              :placeholder="t('actions.search') + '...'" 
              @click.stop
              ref="searchInputRef"
              @keydown.enter="handleEnter"
            />
          </div>

          <div class="c-select-options-list">
            <div 
              v-for="option in filteredOptions" 
              :key="option.value" 
              class="c-select-option"
              :class="{ selected: modelValue === option.value }"
              @click="select(option)"
            >
              {{ option.label }}
            </div>

            <!-- Create New Option -->
            <div 
              v-if="allowCreate && searchQuery && !exactMatch" 
              class="c-select-option create-option"
              @click="createNew"
            >
              <span class="plus">+</span> {{ t('actions.create') }}: "{{ searchQuery }}"
            </div>

            <div v-if="filteredOptions.length === 0 && (!allowCreate || !searchQuery)" class="c-select-no-options">
              {{ t('admin.dashboard.common.no_data') }}
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  modelValue: [String, Number, Boolean],
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: 'Select option...'
  },
  disabled: Boolean,
  allowCreate: Boolean
})

const emit = defineEmits(['update:modelValue', 'change'])

const isOpen = ref(false)
const searchQuery = ref('')
const triggerRef = ref(null)
const dropdownRef = ref(null)
const containerRef = ref(null)
const searchInputRef = ref(null)
const dropdownPos = ref({ top: 0, left: 0, width: 0, placement: 'bottom' })

const filteredOptions = computed(() => {
  if (!searchQuery.value) return props.options
  const q = searchQuery.value.toLowerCase()
  return props.options.filter(o => 
    o.label.toLowerCase().includes(q) || 
    String(o.value).toLowerCase().includes(q)
  )
})

const exactMatch = computed(() => {
  const q = searchQuery.value.toLowerCase()
  return props.options.some(o => o.label.toLowerCase() === q || String(o.value).toLowerCase() === q)
})

const selectedLabel = computed(() => {
  const op = props.options.find(o => o.value === props.modelValue)
  return op ? op.label : props.modelValue || null
})

const dropdownStyle = computed(() => ({
  position: 'fixed',
  top: `${dropdownPos.value.top}px`,
  left: `${dropdownPos.value.left}px`,
  width: `${dropdownPos.value.width}px`,
  zIndex: 10001,
  transformOrigin: dropdownPos.value.placement === 'bottom' ? 'top center' : 'bottom center'
}))

const updatePosition = () => {
  if (!triggerRef.value || !isOpen.value) return
  
  const rect = triggerRef.value.getBoundingClientRect()
  const spaceBottom = window.innerHeight - rect.bottom
  const dropdownHeight = 300 // Max height with search
  
  let top, placement
  if (spaceBottom < dropdownHeight && rect.top > dropdownHeight) {
    top = rect.top - 8 
    placement = 'top'
  } else {
    top = rect.bottom + 8
    placement = 'bottom'
  }
  
  dropdownPos.value = {
    top,
    left: rect.left,
    width: Math.max(200, rect.width),
    placement
  }
}

const toggle = async () => {
  if (props.disabled) return
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    searchQuery.value = ''
    await nextTick()
    updatePosition()
    if (searchInputRef.value) searchInputRef.value.focus()
  }
}

const close = () => {
  isOpen.value = false
}

const select = (option) => {
  emit('update:modelValue', option.value)
  emit('change', option.value)
  isOpen.value = false
}

const createNew = () => {
  if (!props.allowCreate || !searchQuery.value) return
  emit('update:modelValue', searchQuery.value)
  emit('change', searchQuery.value)
  isOpen.value = false
}

const handleEnter = () => {
  if (filteredOptions.value.length > 0) {
    select(filteredOptions.value[0])
  } else if (props.allowCreate && searchQuery.value) {
    createNew()
  }
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
      if (
        !(el === event.target || el.contains(event.target)) &&
        !(event.target.closest('.c-select-dropdown'))
      ) {
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
.c-select-container {
  position: relative;
  width: 100%;
}

.c-select-trigger {
  width: 100%;
  padding: 10px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.c-select-trigger:hover:not(.disabled) {
  border-color: var(--mango-primary);
  background: var(--glass-hover);
}

.c-select-trigger.open {
  border-color: var(--mango-primary);
  box-shadow: 0 0 0 2px var(--mango-glow);
}

.c-select-trigger.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.c-select-value {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.c-select-chevron {
  width: 20px;
  height: 20px;
  opacity: 0.5;
  transition: transform 0.2s;
}

.c-select-trigger.open .c-select-chevron {
  transform: rotate(180deg);
}

.c-select-dropdown {
  max-height: 400px;
  display: flex;
  flex-direction: column;
  padding: 8px;
  border-color: var(--border-subtle);
  background: var(--bg-glass);
  backdrop-filter: blur(40px);
}

.c-select-search-wrap {
  padding: 8px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 8px;
}

.c-select-search {
  width: 100%;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 8px 12px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}

.c-select-search:focus {
  border-color: var(--mango-primary);
}

.c-select-options-list {
  overflow-y: auto;
  flex: 1;
}

.c-select-option {
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.c-select-option:hover {
  background: var(--glass-hover);
  color: var(--text-primary);
}

.c-select-option.selected {
  background: var(--mango-primary);
  color: white;
  font-weight: 700;
}

.create-option {
  color: var(--mango-primary);
  font-weight: 700;
  border-top: 1px dashed var(--border-subtle);
  margin-top: 4px;
  border-radius: 0 0 8px 8px;
}

.create-option .plus {
  font-size: 16px;
}

.c-select-no-options {
  padding: 20px;
  text-align: center;
  font-size: 12px;
  color: var(--text-disabled);
  opacity: 0.5;
}

/* Transitions */
.fade-slide-enter-active, .fade-slide-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.fade-slide-enter-from, .fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.c-select-dropdown[style*="transform-origin: bottom center"] {
  transform: translateY(-100%) translateY(-12px) !important;
}

.fade-slide-enter-from[style*="transform-origin: bottom center"],
.fade-slide-leave-to[style*="transform-origin: bottom center"] {
  opacity: 0;
  transform: translateY(-100%) translateY(8px) !important;
}
</style>
