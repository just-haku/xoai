<script setup>
import GlobalSettingsHub from './components/GlobalSettingsHub.vue'
import SupportTicketModal from './components/SupportTicketModal.vue'
import PortalNotice from './components/PortalNotice.vue'
import QuickSettingsUnauth from './components/QuickSettingsUnauth.vue'
import { onMounted, computed } from 'vue'
import { useUIStore } from './stores/ui'
import { useRoute } from 'vue-router'

const uiStore = useUIStore()
const route = useRoute()

const isUnauthRoute = computed(() => {
  return ['landing', 'login', 'register'].includes(route.name)
})

onMounted(() => {
  uiStore.apply()
})
</script>

<template>
  <div class="app-container">
    <router-view />
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
</style>
