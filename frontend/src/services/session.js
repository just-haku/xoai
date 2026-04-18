const PRIMARY_TOKEN_KEY = 'xoai_token'
const PROXY_SESSION_KEY = 'xoai_proxy_session'
const GOD_MODE_BRIDGE_CHANNEL = 'xoai_god_mode_bridge'
let bridgeChannel = null
let bridgeListenerAttached = false

const canUseBrowserStorage = () => typeof window !== 'undefined'

const parseStoredJson = (storage, key) => {
  if (!storage) return null
  try {
    const raw = storage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const randomBridgeId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `bridge_${Math.random().toString(36).slice(2)}`
}

export const getPrimaryToken = () => {
  if (!canUseBrowserStorage()) return null
  return window.localStorage.getItem(PRIMARY_TOKEN_KEY)
}

export const setPrimaryToken = (token) => {
  if (!canUseBrowserStorage()) return
  window.localStorage.setItem(PRIMARY_TOKEN_KEY, token)
}

export const clearPrimaryToken = () => {
  if (!canUseBrowserStorage()) return
  window.localStorage.removeItem(PRIMARY_TOKEN_KEY)
}

export const getProxySession = () => {
  if (!canUseBrowserStorage()) return null
  const payload = parseStoredJson(window.sessionStorage, PROXY_SESSION_KEY)
  if (!payload?.access_token) return null
  return payload
}

export const setProxySession = (payload) => {
  if (!canUseBrowserStorage()) return
  window.sessionStorage.setItem(PROXY_SESSION_KEY, JSON.stringify({
    ...payload,
    god_mode: true,
  }))
}

export const clearProxySession = () => {
  if (!canUseBrowserStorage()) return
  window.sessionStorage.removeItem(PROXY_SESSION_KEY)
}

export const isGodModeActive = () => Boolean(getProxySession()?.access_token)

export const getActiveToken = () => getProxySession()?.access_token || getPrimaryToken()

export const hasActiveSession = () => Boolean(getActiveToken())

export const clearActiveSession = () => {
  if (isGodModeActive()) {
    clearProxySession()
    return
  }
  clearPrimaryToken()
}

export const hasPendingGodModeHandoff = (routeLike) => {
  const query = routeLike?.query || {}
  return query.god_mode === 'true' && typeof query.handoff === 'string' && query.handoff.length > 0
}

export const hasPendingGodModeBridge = (routeLike) => {
  const query = routeLike?.query || {}
  return query.god_mode === 'true' && typeof query.bridge === 'string' && query.bridge.length > 0
}

const getBridgeChannel = () => {
  if (!canUseBrowserStorage() || typeof BroadcastChannel === 'undefined') return null
  if (!bridgeChannel) {
    bridgeChannel = new BroadcastChannel(GOD_MODE_BRIDGE_CHANNEL)
  }
  return bridgeChannel
}

export const attachGodModeBridgeListener = () => {
  const channel = getBridgeChannel()
  if (!channel || bridgeListenerAttached) return
  bridgeListenerAttached = true
  channel.onmessage = (event) => {
    const data = event.data || {}
    if (data.type !== 'request_proxy_session') return
    const proxySession = getProxySession()
    if (!proxySession?.access_token) return
    channel.postMessage({
      type: 'response_proxy_session',
      bridge: data.bridge,
      payload: proxySession,
    })
  }
}

const receiveGodModeBridgeSession = (bridgeId, timeoutMs = 2500) => {
  const channel = getBridgeChannel()
  if (!channel) {
    throw new Error('God Mode bridge is unavailable in this browser')
  }

  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      channel.removeEventListener('message', handleMessage)
      reject(new Error('Timed out waiting for God Mode session handoff'))
    }, timeoutMs)

    const handleMessage = (event) => {
      const data = event.data || {}
      if (data.type !== 'response_proxy_session' || data.bridge !== bridgeId) return
      window.clearTimeout(timer)
      channel.removeEventListener('message', handleMessage)
      resolve(data.payload)
    }

    channel.addEventListener('message', handleMessage)
    channel.postMessage({ type: 'request_proxy_session', bridge: bridgeId })
  })
}

export const buildViewerUrl = (path) => {
  const params = new URLSearchParams({ path })
  if (isGodModeActive()) {
    params.set('god_mode', 'true')
    params.set('bridge', randomBridgeId())
  }
  return `/view-file?${params.toString()}`
}

export const exchangeGodModeHandoff = async (handoffToken) => {
  const response = await fetch('/api/auth/proxy/exchange', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ handoff_token: handoffToken }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Failed to exchange God Mode handoff')
  }

  return response.json()
}

export const bootstrapGodModeSession = async (route, router) => {
  if (hasPendingGodModeBridge(route)) {
    if (!getProxySession()) {
      const bridgedSession = await receiveGodModeBridgeSession(route.query.bridge)
      setProxySession(bridgedSession)
    }
  } else if (hasPendingGodModeHandoff(route)) {
    const payload = await exchangeGodModeHandoff(route.query.handoff)
    setProxySession({
      access_token: payload.access_token,
      session_id: payload.session_id,
      proxy_by: payload.proxy_by,
      user: payload.user,
    })
  } else {
    return getProxySession()
  }

  if (router) {
    const cleanedQuery = { ...route.query }
    delete cleanedQuery.handoff
    delete cleanedQuery.bridge
    await router.replace({
      name: route.name,
      params: route.params,
      query: cleanedQuery,
      hash: route.hash,
      replace: true,
    })
  }

  return getProxySession()
}
