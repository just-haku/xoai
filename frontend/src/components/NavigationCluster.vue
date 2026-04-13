<template>
  <div class="nav-cluster glass-panel">
    <div class="cluster-items">
      <!-- Profile -->
      <button class="cluster-btn" @click="handleProfile">
        <svg viewBox="0 0 24 24" class="icon"><path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,8.39C13.57,8.39 14.85,9.67 14.85,11.24C14.85,12.81 13.57,14.09 12,14.09C10.43,14.09 9.15,12.81 9.15,11.24C9.15,9.67 10.43,8.39 12,8.39M12,18.78C9.84,18.78 7.96,17.69 6.86,16.03C6.88,14.31 10.3,13.37 12,13.37C13.7,13.37 17.12,14.31 17.14,16.03C16.04,17.69 14.16,18.78 12,18.78Z"/></svg>
        <span class="label">{{ $t('nav.profile') }}</span>
      </button>

      <!-- Settings -->
      <button class="cluster-btn" @click="openSettings">
        <svg viewBox="0 0 24 24" class="icon"><path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.35 19.43,11.03L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.47,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.53,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11.03C4.53,11.35 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.04 4.95,18.95L7.44,17.95C7.96,18.34 8.53,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.47,18.68 16.04,18.34 16.56,17.95L19.05,18.95C19.27,19.04 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z"/></svg>
        <span class="label">{{ $t('nav.settings') }}</span>
      </button>

      <!-- Admin -->
      <button v-if="isAdmin" class="cluster-btn admin" @click="openServerSettings">
        <svg viewBox="0 0 24 24" class="icon"><path d="M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1M12,7C13.4,7 14.8,8.1 14.8,9.5C14.8,11 13.4,12 12,12C10.6,12 9.2,11 9.2,9.5C9.2,8.1 10.6,7 12,7M16,17H8V15.5C8,14.2 10.7,13.2 12,13.2C13.3,13.2 16,14.2 16,15.5V17Z"/></svg>
        <span class="label">{{ $t('nav.server') }}</span>
      </button>

      <div class="divider"></div>

      <!-- Mode Toggle -->
      <button class="cluster-btn toggle" @click="toggleMode">
        <svg v-if="mode === 'chat'" viewBox="0 0 24 24" class="icon"><path d="M19,3H5C3.89,3 3,3.89 3,5V19C3,20.11 3.89,21 5,21H19C20.11,21 21,20.11 21,19V5C21,3.89 20.11,3 19,3M19,19H5V5H19V19M17,17H7V15H17V17M17,13H7V11H17V13M17,9H7V7H17V9Z"/></svg>
        <svg v-else viewBox="0 0 24 24" class="icon"><path d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4A2,2 0 0,0 20,2M20,16H5.17L4,17.17V4H20V16M11,10H13V12H11V10M11,6H13V8H11V6M11,14H13V16H11V14Z"/></svg>
        <span class="label">{{ mode === 'chat' ? $t('nav.workspace') : $t('nav.chat') }}</span>
      </button>

      <button class="cluster-btn" @click="handleSupport">
        <svg viewBox="0 0 24 24" class="icon"><path d="M11,18H13V16H11V18M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,6A4,4 0 0,0 8,10H10A2,2 0 0,1 12,8A2,2 0 0,1 14,10C14,12 11,11.75 11,15H13C13,12.75 16,12.5 16,10A4,4 0 0,0 12,6Z"/></svg>
        <span class="label">{{ $t('nav.support') }}</span>
      </button>

      <button class="cluster-btn logout" @click="logout">
        <svg viewBox="0 0 24 24" class="icon"><path d="M16,17V14H9V10H16V7L21,12L16,17M14,2A2,2 0 0,1 16,4V9H14V4H5V20H14V15H16V20A2,2 0 0,1 14,22H5A2,2 0 0,1 3,20V4A2,2 0 0,1 5,2H14Z"/></svg>
        <span class="label">{{ $t('nav.logout') }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUIStore } from '../stores/ui'

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()
const isAdmin = ref(true)
const mode = ref(route.path.includes('workspace') ? 'workspace' : 'chat')

const toggleMode = () => {
  mode.value = mode.value === 'chat' ? 'workspace' : 'chat'
  if (mode.value === 'workspace') router.push('/workspace')
  else router.push('/')
}

const openSettings = () => {
  uiStore.showSettings = true
}

const handleProfile = () => {
  uiStore.showSettings = true
  // Tab change logic could be added here if needed
}
const handleSupport = () => console.log('Support Click')

const logout = () => {
  localStorage.removeItem('xoai_token')
  router.push('/login')
}
</script>

<style scoped>
.nav-cluster {
  position: fixed;
  bottom: var(--spacing-6);
  left: var(--spacing-6);
  padding: var(--spacing-2);
  border-radius: 20px;
  z-index: 1000;
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-strong);
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}

.cluster-items {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.cluster-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 12px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 160px;
}

.cluster-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.cluster-btn .icon {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.cluster-btn .label {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02rem;
}

.cluster-btn.admin:hover {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

.cluster-btn.logout:hover {
  color: var(--danger);
  background: rgba(239, 68, 68, 0.1);
}

.divider {
  height: 1px;
  background: var(--border-strong);
  margin: var(--spacing-1) var(--spacing-4);
  opacity: 0.5;
}
</style>
