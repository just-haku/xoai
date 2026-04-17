<template>
  <div class="c-select-container" v-click-outside="close">
    <div 
      class="c-select-trigger" 
      :class="{ open: isOpen, disabled: disabled }"
      @click="toggle"
    >
      <span class="c-select-value">{{ selectedLabel || placeholder }}</span>
      <svg class="c-select-chevron" viewBox="0 0 24 24">
        <path d="M7 10l5 5 5-5H7z" fill="currentColor"/>
      </svg>
    </div>

    <transition name="fade-slide">
      <div v-if="isOpen" class="c-select-dropdown glass-panel shadow-premium">
        <div 
          v-for="option in options" 
          :key="option.value" 
          class="c-select-option"
          :class="{ selected: modelValue === option.value }"
          @click="select(option)"
        >
          {{ option.label }}
        </div>
        <div v-if="options.length === 0" class="c-select-no-options">
          No options available
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

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
  disabled: Boolean
})

const emit = defineEmits(['update:modelValue', 'change'])

const isOpen = ref(false)

const selectedLabel = computed(() => {
  const op = props.options.find(o => o.value === props.modelValue)
  return op ? op.label : null
})

const toggle = () => {
  if (props.disabled) return
  isOpen.value = !isOpen.value
}

const close = () => {
  isOpen.value = false
}

const select = (option) => {
  emit('update:modelValue', option.value)
  emit('change', option.value)
  isOpen.value = false
}

// Simple directive for clicking outside
const vClickOutside = {
  mounted(el, binding) {
    el.clickOutsideEvent = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
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
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  z-index: 9999;
  max-height: 250px;
  overflow-y: auto;
  padding: 8px;
  border-color: var(--border-subtle);
}

.c-select-option {
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all 0.2s;
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

.c-select-no-options {
  padding: 12px;
  text-align: center;
  font-size: 12px;
  color: var(--text-disabled);
}

/* Transitions */
.fade-slide-enter-active, .fade-slide-leave-active {
  transition: all 0.2s ease;
}
.fade-slide-enter-from, .fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
