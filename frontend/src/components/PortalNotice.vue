<template>
  <transition name="portal-fade">
    <div v-if="visible" class="portal-notice-overlay" @click.self="close">
      <div class="portal-card glass-panel" :class="[type, themeMode]">
        <div class="portal-icon">
          <svg v-if="type === 'success'" viewBox="0 0 24 24"><path d="M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z"/></svg>
          <svg v-if="type === 'error'" viewBox="0 0 24 24"><path d="M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M13 17H11V15H13V17M13 13H11V7H13V13Z"/></svg>
          <svg v-if="type === 'info'" viewBox="0 0 24 24"><path d="M11 9H13V7H11V9M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M12 20C7.59 20 4 16.41 4 12S7.59 4 12 4 20 7.59 20 12 16.41 20 12 20M11 17H13V11H11V17Z"/></svg>
        </div>
        <div class="portal-body">
          <h4 class="portal-title">{{ title || defaultTitle }}</h4>
          <p class="portal-message">{{ message }}</p>
          
          <div v-if="requiresInput" class="portal-input-group">
            <input v-model="inputValue" type="text" :placeholder="inputPlaceholder" class="portal-input" @keyup.enter="submit" />
          </div>

          <div class="portal-actions">
            <button v-if="showCancel" class="portal-btn secondary" @click="close">Cancel</button>
            <button class="portal-btn primary" @click="submit">Confirm</button>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUIStore } from '../stores/ui'

const props = defineProps({
  visible: Boolean,
  type: { type: String, default: 'info' }, // success, error, info, warning
  title: String,
  message: String,
  requiresInput: Boolean,
  inputPlaceholder: { type: String, default: 'Enter value...' },
  showCancel: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'submit'])
const uiStore = useUIStore()
const inputValue = ref('')

const themeMode = computed(() => uiStore.theme || 'dark')
const defaultTitle = computed(() => {
  if (props.type === 'success') return 'Success'
  if (props.type === 'error') return 'System Alert'
  return 'Information'
})

const close = () => {
  emit('close')
}

const submit = () => {
  emit('submit', inputValue.value)
  inputValue.value = ''
  close()
}
</script>

<style scoped>
.portal-notice-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  z-index: 99999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.portal-card {
  width: 100%;
  max-width: 440px;
  padding: 32px;
  border-radius: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 24px;
  border: 1px solid var(--border-strong);
  box-shadow: 0 40px 100px rgba(0,0,0,0.4);
}

.portal-icon { width: 64px; height: 64px; }
.portal-icon svg { fill: var(--mango-primary); }

.portal-card.success .portal-icon svg { fill: var(--success); }
.portal-card.error .portal-icon svg { fill: var(--danger); }

.portal-title { font-size: 20px; font-weight: 800; margin-bottom: 8px; }
.portal-message { opacity: 0.6; line-height: 1.6; }

.portal-input-group { width: 100%; margin-top: 12px; }
.portal-input {
  width: 100%;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 12px 16px;
  color: var(--text-primary);
  outline: none;
}
.portal-input:focus { border-color: var(--mango-primary); }

.portal-actions {
  display: flex;
  gap: 12px;
  width: 100%;
  margin-top: 8px;
}

.portal-btn {
  flex: 1;
  padding: 12px;
  border-radius: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.portal-btn.primary {
  background: var(--mango-primary);
  color: white;
  border: none;
  box-shadow: 0 4px 15px var(--mango-glow);
}

.portal-btn.secondary {
  background: transparent;
  border: 1px solid var(--border-strong);
  color: var(--text-primary);
}

.portal-btn:hover { transform: translateY(-2px); }

/* Transitions */
.portal-fade-enter-active, .portal-fade-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.portal-fade-enter-from, .portal-fade-leave-to { opacity: 0; transform: scale(0.95); }
</style>
