<template>
  <TransitionGroup name="notif" tag="div" class="notification-station">
    <div v-for="n in uiStore.notifications" :key="n.id" class="notification-box glass-panel" :class="n.type">
      <div class="n-icon">
        <svg v-if="n.type === 'success'" viewBox="0 0 24 24"><path d="M9,16.17L4.83,12L3.41,13.41L9,19L21,7L19.59,5.59L9,16.17Z"/></svg>
        <svg v-else-if="n.type === 'error'" viewBox="0 0 24 24"><path d="M12,2L1,21H23L12,2M12,6L19.53,19H4.47L12,6M11,10V14H13V10H11M11,16V18H13V16H11Z"/></svg>
        <svg v-else viewBox="0 0 24 24"><path d="M11,9H13V7H11M11,17H13V11H11M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/></svg>
      </div>
      <div class="n-message">{{ n.message }}</div>
      <button class="n-close" @click="uiStore.removeNotification(n.id)">
        <svg viewBox="0 0 24 24"><path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L17.59,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/></svg>
      </button>
    </div>
  </TransitionGroup>
</template>

<script setup>
import { useUIStore } from '../stores/ui'
const uiStore = useUIStore()
</script>

<style scoped>
.notification-station {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 12px;
  pointer-events: none;
}

.notification-box {
  pointer-events: auto;
  min-width: 300px;
  max-width: 400px;
  padding: 16px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.3);
  border: 1px solid var(--border-subtle);
}

.n-icon { width: 24px; height: 24px; flex-shrink: 0; }
.n-icon svg { width: 100%; fill: currentColor; }

.notification-box.success .n-icon { color: var(--accent-green); }
.notification-box.error .n-icon { color: var(--danger); }
.notification-box.info .n-icon { color: var(--mango-primary); }

.n-message { font-size: 14px; font-weight: 700; flex: 1; }

.n-close {
  background: transparent; border: none; color: var(--text-secondary); cursor: pointer;
  padding: 4px; border-radius: 6px; display: flex; align-items: center; justify-content: center;
  transition: all 0.2s; opacity: 0.5;
}
.n-close:hover { background: rgba(255,255,255,0.05); color: var(--text-primary); opacity: 1; }
.n-close svg { width: 14px; fill: currentColor; }

/* Animations */
.notif-enter-active, .notif-leave-active { transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
.notif-enter-from { transform: translateX(100%) scale(0.9); opacity: 0; }
.notif-leave-to { transform: translateX(100%) scale(0.9); opacity: 0; }
</style>
