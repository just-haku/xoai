<template>
  <div class="quick-settings-unauth">
    <div class="top-right-toolbar">
      <!-- Sign In Button (Hidden on login page) -->
      <router-link 
        v-if="route.name !== 'login'" 
        to="/login" 
        class="nav-link login-box"
      >
        {{ $t('landing.nav.signin') }}
      </router-link>

      <div class="settings-wrapper" v-click-outside="closeMenu">
        <button class="cogs-btn" @click="toggleMenu" :title="$t('nav.settings')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </button>

        <transition name="fade-slide">
          <div v-if="isOpen" class="unauth-menu glass-panel shadow-premium">
            <div class="settings-grid">
              <!-- Theme Toggle -->
              <button class="grid-btn" @click="toggleTheme" :title="$t('settings.interface.theme.title')">
                <svg viewBox="0 0 24 24" fill="currentColor" class="btn-svg">
                  <path d="M12 2A10 10 0 0 0 2 12A10 10 0 0 0 12 22A10 10 0 0 0 22 12A10 10 0 0 0 12 2M12 4A8 8 0 0 1 12 20V4Z"/>
                </svg>
              </button>

              <!-- Language Toggle -->
              <button class="grid-btn text-btn" @click="toggleLang" :title="$t('settings.interface.lang')">
                {{ uiStore.lang === 'en' ? 'EN' : 'VI' }}
              </button>

              <!-- UI Scale + -->
              <button class="grid-btn text-btn" @click.stop="uiStore.setScale(uiStore.scale + 0.1)" title="UI+">
                A+
              </button>

              <!-- UI Scale - -->
              <button class="grid-btn text-btn" @click.stop="uiStore.setScale(uiStore.scale - 0.1)" title="UI-">
                A-
              </button>
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUIStore } from '../stores/ui'
import { useRoute } from 'vue-router'

const uiStore = useUIStore()
const route = useRoute()
const isOpen = ref(false)

const toggleMenu = () => isOpen.value = !isOpen.value
const closeMenu = () => isOpen.value = false

const toggleTheme = () => {
  uiStore.setTheme(uiStore.theme === 'dark' ? 'light' : 'dark')
}

const toggleLang = () => {
  uiStore.setLang(uiStore.lang === 'en' ? 'vi' : 'en')
}

// Simple click-outside directive simulation
const vClickOutside = {
  mounted(el, binding) {
    el._clickOutside = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value(event)
      }
    }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el) {
    document.removeEventListener('click', el._clickOutside)
  }
}
</script>

<style scoped>
.top-right-toolbar {
  position: fixed;
  top: 40px;
  right: 80px;
  display: flex;
  align-items: center;
  gap: 20px;
  z-index: 9999;
}

.login-box { 
  display: block;
  padding: 10px 24px; 
  border: 1.5px solid var(--border-strong); 
  border-radius: 14px; 
  color: var(--text-primary); 
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
  background: var(--bg-glass);
  backdrop-filter: blur(10px);
  transition: all 0.3s;
}

.login-box:hover {
  border-color: var(--mango-primary);
  color: var(--mango-primary);
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(255, 170, 0, 0.1);
}

.settings-wrapper {
  position: relative;
}

.cogs-btn {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  border: 1px solid var(--border-strong);
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  color: var(--text-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}

.cogs-btn:hover {
  border-color: var(--mango-primary);
  color: var(--mango-primary);
  box-shadow: 0 4px 25px var(--mango-glow);
}

.cogs-btn:hover svg {
  transform: rotate(45deg);
}

.cogs-btn svg {
  width: 22px;
  height: 22px;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.unauth-menu {
  position: absolute;
  top: 56px;
  right: 0;
  width: 140px;
  padding: 12px;
  border-radius: 20px;
  border: 1px solid var(--border-strong);
  animation: menuIn 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  background: var(--bg-glass);
  backdrop-filter: blur(30px);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.grid-btn {
  aspect-ratio: 1;
  border-radius: 12px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.grid-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--mango-primary);
  color: var(--mango-primary);
}

.btn-svg {
  width: 20px;
  height: 20px;
}

.text-btn {
  font-size: 14px;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.fade-slide-enter-active, .fade-slide-leave-active {
  transition: all 0.2s ease;
}
.fade-slide-enter-from, .fade-slide-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.95);
}
</style>
