<template>
  <div class="settings-cog-container">
    <!-- SVG Cog Trigger -->
    <button class="cog-trigger" @click.stop="isOpen = !isOpen" :class="{active: isOpen}">
      <svg viewBox="0 0 24 24" class="icon"><path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.35 19.43,11.03L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.47,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.53,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11.03C4.53,11.35 4.5,11.67 4.5,12C4.5,11.32 4.53,11.35 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.04 4.95,18.95L7.44,17.95C7.96,18.34 8.53,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.47,18.68 16.04,18.34 16.56,17.95L19.05,18.95C19.27,19.04 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z"/></svg>
    </button>
    
    <div v-if="isOpen" class="settings-hub-dropdown glass-panel">
      <div class="grid-2x2">
        <!-- Theme Toggle -->
        <button class="grid-item" @click="uiStore.setTheme(uiStore.theme === 'dark' ? 'light' : 'dark')" :title="uiStore.theme === 'dark' ? $t('settings.interface.theme') + ': Light' : $t('settings.interface.theme') + ': Dark'">
          <svg v-if="uiStore.theme === 'dark'" viewBox="0 0 24 24" class="inner-icon"><path d="M12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,2L14.39,4.39L12,6.78L9.61,4.39L12,2M3.36,4.91L5.75,7.3L3.36,9.69L0.97,7.3L3.36,4.91M2,12L4.39,9.61L6.78,12L4.39,14.39L2,12M4.91,20.64L7.3,18.25L9.69,20.64L7.3,23.03L4.91,20.64M12,22L9.61,19.61L12,17.22L14.39,19.61L12,22M20.64,19.09L18.25,16.7L20.64,14.31L23.03,16.7L20.64,19.09M22,12L19.61,14.39L17.22,12L19.61,9.61L22,12M19.09,3.36L16.7,5.75L14.31,3.36L16.7,0.97L19.09,3.36Z"/></svg>
          <svg v-else viewBox="0 0 24 24" class="inner-icon"><path d="M17.75,4.09L15.22,6.03L16.13,9.09L13.5,7.28L10.87,9.09L11.78,6.03L9.25,4.09L12.44,4L13.5,1L14.56,4L17.75,4.09M21.25,11L19.61,12.25L20.2,14.23L18.5,13.06L16.8,14.23L17.39,12.25L15.75,11L17.81,10.95L18.5,9L19.19,10.95L21.25,11M18.97,15.95C18.39,15.92 17.77,15.96 17.15,16.07C11.11,17.08 6.82,12.43 7.47,6.38C7.76,3.73 8.91,1.54 10.41,0.2C4.62,1.17 0.5,6.1 0.5,12C0.5,18.35 5.65,23.5 12,23.5C15.84,23.5 19.25,21.61 21.32,18.65C20.55,18.85 19.76,18.96 18.97,15.95Z"/></svg>
        </button>

        <!-- Language Toggle -->
        <button class="grid-item" @click="uiStore.setLang(uiStore.lang === 'en' ? 'vi' : 'en')" :title="$t('settings.interface.language') + ': ' + uiStore.lang">
          <svg viewBox="0 0 24 24" class="inner-icon"><path d="M16.36,14C16.44,13.34 16.5,12.68 16.5,12C16.5,11.32 16.44,10.66 16.36,10H19.74C19.9,10.64 20,11.31 20,12C20,12.69 19.9,13.36 19.74,14M14.59,19C15.11,17.59 15.5,16.31 15.79,14H18.26C17.28,15.81 15.54,17.39 13.5,18.26C13.85,18.5 14.23,18.75 14.59,19M14.34,10H9.66C9.57,10.66 9.5,11.32 9.5,12C9.5,12.68 9.57,13.34 9.66,14H14.34C14.43,13.34 14.5,12.68 14.5,12C14.5,11.32 14.43,10.66 14.34,10M12,2C12.44,2 12.87,2.13 13.29,2.38C12.91,2.59 12.56,2.85 12.26,3.14M6.74,10H10.26C10.16,10.66 10.1,11.32 10.1,12C10.1,12.68 10.16,13.34 10.26,14H6.74C6.58,13.36 6.5,12.69 6.5,12C6.5,11.31 6.58,10.64 6.74,10M12,22C11.56,22 11.13,21.87 10.71,21.62C11.09,21.41 11.44,21.15 11.74,20.86M12,2C13.28,2 14.94,5 15.64,8H8.36C9.06,5 10.72,2 12,2M12,22C10.72,22 9.06,19 8.36,16H15.64C14.94,19 13.28,22 12,22M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/></svg>
        </button>

        <!-- UI Scale Minus -->
        <button class="grid-item" @click="uiStore.setScale(uiStore.scale - 0.1)" :title="$t('settings.interface.scale') + ' -'">
          <svg viewBox="0 0 24 24" class="inner-icon"><path d="M19,13H5V11H19V13Z"/></svg>
        </button>

        <!-- UI Scale Plus -->
        <button class="grid-item" @click="uiStore.setScale(uiStore.scale + 0.1)" :title="$t('settings.interface.scale') + ' +'">
          <svg viewBox="0 0 24 24" class="inner-icon"><path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useUIStore } from '../stores/ui'

const uiStore = useUIStore()
const isOpen = ref(false)

const close = () => (isOpen.value = false)

onMounted(() => {
  window.addEventListener('click', close)
})

onUnmounted(() => {
  window.removeEventListener('click', close)
})
</script>

<style scoped>
.settings-cog-container {
  position: relative;
}

.cog-trigger {
  background: transparent;
  border: none;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 50%;
}

.cog-trigger:hover, .cog-trigger.active {
  background: rgba(255, 255, 255, 0.05);
  color: var(--mango-primary);
  transform: rotate(90deg);
}

.cog-trigger .icon {
  width: 22px;
  fill: currentColor;
}

.settings-hub-dropdown {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 140px;
  padding: 12px;
  z-index: 10000;
  box-shadow: 0 10px 40px rgba(0,0,0,0.6);
}

.grid-2x2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.grid-item {
  aspect-ratio: 1;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.grid-item:hover {
  background: rgba(255, 122, 0, 0.1);
  border-color: var(--mango-primary);
  color: var(--mango-primary);
  transform: translateY(-2px);
}

.inner-icon {
  width: 22px;
  fill: currentColor;
}
</style>
