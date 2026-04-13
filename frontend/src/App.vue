<script setup>
import NavigationCluster from './components/NavigationCluster.vue'
import SettingsOverlay from './components/SettingsOverlay.vue'
import { useRoute } from 'vue-router'
import { onMounted } from 'vue'
import { useUIStore } from './stores/ui'

const route = useRoute()
const uiStore = useUIStore()

onMounted(() => {
  uiStore.apply()
})
</script>

<template>
  <div class="app-container">
    <router-view />
    <NavigationCluster v-if="route.meta.requiresAuth" />
    <SettingsOverlay :show="uiStore.showSettings" @close="uiStore.showSettings = false" />
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
