const DB_NAME = 'xoai-chat-cache'
const DB_VERSION = 1
const STORE_NAME = 'conversations'

const hasIndexedDb = () => typeof window !== 'undefined' && 'indexedDB' in window

const openDb = () => new Promise((resolve, reject) => {
  if (!hasIndexedDb()) {
    reject(new Error('IndexedDB unavailable'))
    return
  }
  const request = window.indexedDB.open(DB_NAME, DB_VERSION)
  request.onupgradeneeded = () => {
    const db = request.result
    if (!db.objectStoreNames.contains(STORE_NAME)) {
      db.createObjectStore(STORE_NAME, { keyPath: 'conversationId' })
    }
  }
  request.onsuccess = () => resolve(request.result)
  request.onerror = () => reject(request.error)
})

export const loadCachedConversation = async (conversationId) => {
  if (!hasIndexedDb()) return null
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const request = store.get(conversationId)
    request.onsuccess = () => resolve(request.result || null)
    request.onerror = () => reject(request.error)
  }).finally(() => db.close())
}

export const saveCachedConversation = async (conversationId, payload) => {
  if (!hasIndexedDb()) return
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
    tx.objectStore(STORE_NAME).put({
      conversationId,
      ...payload,
      updatedAt: Date.now(),
    })
  }).finally(() => db.close())
}
