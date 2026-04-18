import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { bootstrapGodModeSession, clearProxySession, getProxySession, hasPendingGodModeBridge, hasPendingGodModeHandoff } from '../services/session'

export const useSessionStore = defineStore('session', () => {
  const ready = ref(false)
  const hydrating = ref(false)
  const godMode = ref(false)
  const proxiedUser = ref(null)
  const proxyBy = ref(null)

  const syncFromStorage = () => {
    const proxySession = getProxySession()
    godMode.value = Boolean(proxySession?.access_token)
    proxiedUser.value = proxySession?.user || null
    proxyBy.value = proxySession?.proxy_by || null
    ready.value = true
  }

  const bootstrapFromRoute = async (route, router) => {
    if (!hasPendingGodModeHandoff(route) && !hasPendingGodModeBridge(route)) {
      syncFromStorage()
      return
    }
    hydrating.value = true
    try {
      await bootstrapGodModeSession(route, router)
      syncFromStorage()
    } catch (error) {
      clearProxySession()
      syncFromStorage()
      throw error
    } finally {
      hydrating.value = false
    }
  }

  const proxiedUserLabel = computed(() => {
    const user = proxiedUser.value
    return user?.name || user?.username || user?.email || ''
  })

  return {
    ready,
    hydrating,
    godMode,
    proxiedUser,
    proxyBy,
    proxiedUserLabel,
    syncFromStorage,
    bootstrapFromRoute,
  }
})
