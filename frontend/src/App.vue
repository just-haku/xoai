<script setup>
import GlobalSettingsHub from './components/GlobalSettingsHub.vue'
import SupportTicketModal from './components/SupportTicketModal.vue'
import PortalNotice from './components/PortalNotice.vue'
import QuickSettingsUnauth from './components/QuickSettingsUnauth.vue'
import { onMounted, computed, watch } from 'vue'
import { useUIStore } from './stores/ui'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from './stores/session'
import { useI18n } from 'vue-i18n'
import { attachGodModeBridgeListener } from './services/session'

const uiStore = useUIStore()
const sessionStore = useSessionStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const isUnauthRoute = computed(() => {
  return ['landing', 'login', 'register'].includes(route.name)
})

onMounted(() => {
  uiStore.apply()
  attachGodModeBridgeListener()
  sessionStore.bootstrapFromRoute(route, router).catch((error) => {
    uiStore.notify(error.message || t('god_mode.bootstrap_failed'), 'danger')
    router.replace({ name: 'landing' })
  })
})

watch(() => route.fullPath, async () => {
  try {
    await sessionStore.bootstrapFromRoute(route, router)
  } catch (error) {
    uiStore.notify(error.message || t('god_mode.bootstrap_failed'), 'danger')
    router.replace({ name: 'landing' })
  }
})
</script>

<template>
  <div class="app-container" :class="{ 'god-mode-active': sessionStore.godMode && !isUnauthRoute }">
    <div v-if="sessionStore.godMode && !isUnauthRoute" class="god-mode-banner">
      {{ t('god_mode.banner', { user: sessionStore.proxiedUserLabel }) }}
    </div>
    <div v-if="!sessionStore.ready || sessionStore.hydrating" class="app-loader">
      <div class="app-loader__ring"></div>
      <span>{{ t('god_mode.bootstrapping') }}</span>
    </div>
    <router-view v-else />
    <QuickSettingsUnauth v-if="isUnauthRoute" />
    <GlobalSettingsHub :show="uiStore.showSettings" @close="uiStore.showSettings = false" />
    <SupportTicketModal :show="uiStore.showSupport" @close="uiStore.showSupport = false" />
    <PortalNotice 
      :visible="uiStore.notice.visible"
      :type="uiStore.notice.type"
      :title="uiStore.notice.title"
      :message="uiStore.notice.message"
      :requires-input="uiStore.notice.requiresInput"
      :input-placeholder="uiStore.notice.inputPlaceholder"
      :show-cancel="uiStore.notice.showCancel"
      @close="uiStore.closeNotice"
      @submit="uiStore.handleSubmit"
    />
  </div>
</template>

<style>
@import './assets/main.css';

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-container.god-mode-active {
  padding-top: 44px;
}

.god-mode-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 5000;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  background: #2d1400;
  color: #ffd58c;
  border-bottom: 1px solid rgba(255, 170, 0, 0.35);
  font-size: 13px;
  font-weight: 700;
}

.app-loader {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.app-loader__ring {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--mango-primary);
  border-radius: 999px;
  animation: app-spin 1s linear infinite;
}

@keyframes app-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
