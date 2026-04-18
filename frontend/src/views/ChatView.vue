<script setup>
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { useChatStore } from '../stores/chat'
import { useUIStore } from '../stores/ui'
import { useRouter, useRoute } from 'vue-router'
import ToolCog from '../components/ToolCog.vue'
import WorkspaceDesktop from '../components/WorkspaceDesktop.vue'
import ModelSelector from '../components/ModelSelector.vue'
import ChatMessage from '../components/ChatMessage.vue'
import FilePreviewOverlay from '../components/FilePreviewOverlay.vue'
import { api } from '../services/api'
import { useI18n } from 'vue-i18n'
import { clearActiveSession } from '../services/session'
import { useSessionStore } from '../stores/session'

const chatStore = useChatStore()
const uiStore = useUIStore()
const sessionStore = useSessionStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const newMessage = ref('')
const attachments = ref([])
const fileInput = ref(null)
const messagesContainer = ref(null)
const previewState = ref({ show: false, file: null })
const searchQuery = ref('')
const user = ref({ role: 'user' })
const virtualRowHeight = 132
const virtualOverscan = 10
const scrollTop = ref(0)
const viewportHeight = ref(800)

const currentChatTitle = computed(() => {
  if (chatStore.activeConversationId === chatStore.omniChannelId) return t('chat.view.work_chat_title')
  const chat = chatStore.conversations.find(c => c.id === chatStore.activeConversationId)
  if (!chat || !chat.title) return t('chat.view.new_chat_title')
  return t('chat.view.chat_title', { title: chat.title })
})
const isGodMode = computed(() => sessionStore.godMode)
const godModeUserLabel = computed(() => sessionStore.proxiedUserLabel || user.value?.name || user.value?.username || '')

// Mode detection based on route
const currentMode = computed(() => route.name === 'workspace' ? 'workspace' : 'chat')
const sidebarLabel = computed(() => currentMode.value === 'workspace' ? 'nav.workspace' : 'chat.chat_list')

const fetchUserData = async () => {
  try {
    const data = await api.auth.me()
    user.value = data
  } catch (err) {}
}

let resizeObserver = null
onMounted(() => {
  chatStore.connect('default_conversation')
  uiStore.apply()
  fetchUserData()

  // Track viewport height with ResizeObserver for accurate virtual scroll
  if (messagesContainer.value) {
    viewportHeight.value = messagesContainer.value.clientHeight || 800
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        viewportHeight.value = entry.contentRect.height || 800
      }
    })
    resizeObserver.observe(messagesContainer.value)
  }
})

import { onBeforeUnmount } from 'vue'
onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    scrollTop.value = messagesContainer.value.scrollTop
  }
}

watch(() => chatStore.messages.length, scrollToBottom)
const totalVirtualHeight = computed(() => chatStore.messages.length * virtualRowHeight)
const visibleRange = computed(() => {
  const vh = viewportHeight.value
  const start = Math.max(0, Math.floor(scrollTop.value / virtualRowHeight) - virtualOverscan)
  const count = Math.ceil(vh / virtualRowHeight) + virtualOverscan * 2
  const end = Math.min(chatStore.messages.length, start + count)
  return { start, end }
})
const visibleMessages = computed(() =>
  chatStore.messages.slice(visibleRange.value.start, visibleRange.value.end).map((message, offset) => ({
    message,
    index: visibleRange.value.start + offset,
  }))
)
const topSpacerHeight = computed(() => visibleRange.value.start * virtualRowHeight)
const bottomSpacerHeight = computed(() => Math.max(0, totalVirtualHeight.value - topSpacerHeight.value - (visibleMessages.value.length * virtualRowHeight)))

const sendMessage = async () => {
  if (isGodMode.value) {
    uiStore.notify(t('god_mode.chat_read_only_notice'), 'warning')
    return
  }
  if (!newMessage.value.trim() && attachments.value.length === 0) return
  const text = newMessage.value
  const files = [...attachments.value]
  newMessage.value = ''
  attachments.value = []
  await chatStore.sendMessage(text, files)
}

const handleEnterKey = (e) => {
  if (e.shiftKey) return
  sendMessage()
}

const handleAttachmentSelection = (event) => {
  attachments.value = Array.from(event.target.files || [])
}

const handleMessageScroll = () => {
  if (!messagesContainer.value) return
  scrollTop.value = messagesContainer.value.scrollTop
}

const logout = () => {
  clearActiveSession()
  router.push('/')
}

const startDrag = (id, event) => {
  let win = uiStore.windows[id]
  
  let startX = 0
  let startY = 0

  if (!win.floating) {
    const prevW = win.w
    uiStore.setLayout('chat-only')
    
    // Calculate new position so cursor stays at the same relative position in the header
    // if possible, otherwise center it.
    const newW = id === 'chat' ? 900 : 320
    const cursorOffsetPercent = event.clientX / window.innerWidth
    let newX = event.clientX - (newW * cursorOffsetPercent)
    
    // Clamp to screen
    newX = Math.max(10, Math.min(newX, window.innerWidth - newW - 10))

    uiStore.updateWindow(id, { 
      floating: true, 
      x: newX, 
      y: event.clientY - 20 
    })
    win = uiStore.windows[id]
    
    startX = event.clientX - newX
    startY = 20
  } else {
    startX = event.clientX - win.x
    startY = event.clientY - win.y
  }

  document.body.classList.add('dragging')

    const move = (e) => {
    const desktopArea = document.querySelector('.chat-main')
    const rect = desktopArea.getBoundingClientRect()
    
    let newX = e.clientX - startX
    let newY = e.clientY - startY

    newX = Math.max(0, Math.min(newX, rect.width - win.w))
    newY = Math.max(0, Math.min(newY, rect.height - win.h))

    uiStore.updateWindow(id, uiStore.clampWindowToViewport({ ...win, x: newX, y: newY }))
    
    if (e.clientY < 60) {
      document.body.classList.add('dock-target')
    } else {
      document.body.classList.remove('dock-target')
    }
  }

  const up = (e) => {
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', up)
    document.body.classList.remove('dragging')
    document.body.classList.remove('dock-target')
    
    if (e.clientY < 60) {
      const splitPoint = window.innerWidth / 2
      if (e.clientX < splitPoint - 100) {
        // Snap to LEFT
        uiStore.setLayout('split')
        uiStore.snapWindow(id, 'left')
        uiStore.snapWindow(id === 'chat' ? 'workspace' : 'chat', 'right')
        restore(id === 'chat' ? 'workspace' : 'chat')
      } else if (e.clientX > splitPoint + 100) {
        // Snap to RIGHT
        uiStore.setLayout('split')
        uiStore.snapWindow(id, 'right')
        uiStore.snapWindow(id === 'chat' ? 'workspace' : 'chat', 'left')
        restore(id === 'chat' ? 'workspace' : 'chat')
      } else {
        // Snap to FULL (Center)
        uiStore.setLayout('chat-only')
        uiStore.snapWindow(id, 'full')
        minimize(id === 'chat' ? 'workspace' : 'chat')
      }
    }
  }

  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
}

const startResize = (id, event) => {
  event.preventDefault()
  const win = uiStore.windows[id]
  const startW = win.w
  const startH = win.h
  const startX = event.clientX
  const startY = event.clientY

  const move = (e) => {
    uiStore.updateWindow(id, uiStore.clampWindowToViewport({
      ...win,
      w: Math.max(300, startW + (e.clientX - startX)),
      h: Math.max(200, startH + (e.clientY - startY))
    }))
  }

  const up = () => {
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', up)
  }

  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
}

const minimize = (id) => uiStore.updateWindow(id, { minimized: true })
const restore = (id) => uiStore.updateWindow(id, { minimized: false })
const undock = (id) => {
  uiStore.setLayout('chat-only')
  uiStore.updateWindow(id, { floating: true, x: 100, y: 100 })
}

const toggleWindow = (id) => {
  const win = uiStore.windows[id]
  if (win.minimized) {
    uiStore.updateWindow(id, { minimized: false, order: Object.keys(uiStore.windows).length + 1 })
  } else {
    // If it's already top order and visible, maybe minimize? 
    // Or just ensure it's selected. 
    // For now, toggle minimized for side buttons.
    uiStore.updateWindow(id, { minimized: true })
  }
}

const openFile = (file) => {
  previewState.value = { show: true, file }
}

const suggestions = computed(() => [
  { icon: 'code', text: t('chat.view.suggestions.architect.text'), sub: t('chat.view.suggestions.architect.sub') },
  { icon: 'search', text: t('chat.view.suggestions.ui.text'), sub: t('chat.view.suggestions.ui.sub') },
  { icon: 'folder', text: t('chat.view.suggestions.patterns.text'), sub: t('chat.view.suggestions.patterns.sub') },
  { icon: 'code', text: t('chat.view.suggestions.refactor.text'), sub: t('chat.view.suggestions.refactor.sub') }
])

const useSuggestion = (text) => {
  newMessage.value = text
  sendMessage()
}

const showQuickSettings = ref(false)
const activeWorkChatId = ref(null)

const activeWorkChat = computed(() => {
  if (!activeWorkChatId.value || !chatStore.conversations) return null
  return chatStore.conversations.find(c => c.id === activeWorkChatId.value)
})

const handleWorkChatDrop = async (e) => {
  const data = e.dataTransfer.getData('text/plain')
  if (data) {
    activeWorkChatId.value = data
    try {
      await api.users.setWorkChat(data)
      uiStore.notify(t('chat.view.notifications.work_chat_assigned'), 'success', 3000)
    } catch (err) {
      uiStore.notify(t('chat.view.notifications.work_chat_assign_failed'), 'error', 3000)
    }
  }
}

const clearWorkChat = async () => {
  activeWorkChatId.value = null
  try {
    await api.users.setWorkChat(null)
    uiStore.notify(t('chat.view.notifications.work_chat_unlinked'), 'info', 3000)
  } catch (err) {}
}

const handleChatDragStart = (e, id) => {
  e.dataTransfer.setData('text/plain', id)
}

const openTicketing = () => {
  uiStore.showSupport = true
}

const desktopMenu = ref({ show: false, x: 0, y: 0 })

const showDesktopMenu = (e) => {
  // Only show if clicking directly on the background (chat-body)
  if (e.target.classList.contains('chat-body')) {
    desktopMenu.value = {
      show: true,
      x: e.clientX,
      y: e.clientY
    }
  }
}

const formatSize = (bytes) => {
  if (bytes === undefined || bytes === null) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

onMounted(() => {
  window.addEventListener('click', () => {
    showQuickSettings.value = false
    desktopMenu.value.show = false
  })
})
</script>

<template>
  <div class="chat-page">
    <!-- Sidebar -->
    <aside class="sidebar glass-panel">
      <div class="sidebar-header">
        <div class="brand">XO<span class="mango-text">AI</span></div>
        <button class="new-chat-btn" :disabled="isGodMode" @click="!isGodMode && chatStore.newChat?.()" :title="$t('chat.new_chat')">
          <svg viewBox="0 0 24 24"><path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"/></svg>
        </button>
      </div>

      <div class="sidebar-search">
        <div class="search-input-wrapper">
          <svg class="search-icon" viewBox="0 0 24 24"><path d="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"/></svg>
          <input v-model="searchQuery" :placeholder="$t('chat.search')" />
        </div>
      </div>

      <div class="sidebar-nav-label">{{ $t(sidebarLabel) }}</div>

      <div class="conversation-list scrollable">
        <!-- Pinned Omni-Channel -->
        <div v-if="activeWorkChat" 
             class="chat-item omni-pinned"
             :class="{ active: chatStore.activeConversationId === activeWorkChatId }"
             @click="chatStore.loadChat(activeWorkChatId)">
          <div class="omni-status"></div>
          <span class="chat-title">{{ activeWorkChat.title || t('chat.view.omni_channel') }}</span>
        </div>

        <div v-for="chat in (chatStore.conversations || []).filter(c => c.id !== activeWorkChatId)" 
             :key="chat.id" 
             class="chat-item"
             :class="{ active: chatStore.activeConversationId === chat.id }"
             @click="chatStore.loadChat(chat.id)">
          <span class="chat-title">{{ chat.title || $t('chat.default_title') }}</span>
        </div>
      </div>

      <div class="sidebar-footer-grid">
        <button class="f-btn" @click="openTicketing">
          <div class="hover-label">{{ $t('nav.support') }}</div>
          <svg viewBox="0 0 24 24" class="parallelogram-i">
            <path d="M5 20H19L22 4H8L5 20Z" fill="none" stroke="currentColor" stroke-width="2" />
            <text x="12" y="14" font-family="serif" font-weight="900" font-style="italic" fill="currentColor" text-anchor="middle">i</text>
          </svg>
        </button>
        <router-link v-if="user?.role === 'admin'" to="/server-settings" class="f-btn admin-btn">
          <div class="hover-label">{{ $t('admin.title') }}</div>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.77 3.77z"/>
          </svg>
        </router-link>
        <router-link to="/user-settings" class="f-btn">
          <div class="hover-label">{{ $t('nav.settings') }}</div>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.35 19.43,11.03L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.47,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.53,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11.03C4.53,11.35 4.5,11.67 4.5,12C4.5,11.67 4.47,11.35 4.43,11.03L2.46,9.37C2.27,9.22 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.04 4.95,18.95L7.44,17.95C7.96,18.34 8.53,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.47,18.68 16.04,18.34 16.56,17.95L19.05,18.95C19.27,19.04 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" />
          </svg>
        </router-link>
        <button class="f-btn logout" @click="logout">
          <div class="hover-label">{{ $t('nav.logout') }}</div>
          <svg viewBox="0 0 24 24"><path d="M16,17V14H9V10H16V7L21,12L16,17M14,2A2,2 0 0,1 16,4V6H14V4H5V20H14V18H16V20A2,2 0 0,1 14,22H5A2,2 0 0,1 3,20V4A2,2 0 0,1 5,2H14Z"/></svg>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="chat-main">
      <div v-if="isGodMode" class="god-mode-readout glass-panel">
        {{ t('god_mode.banner', { user: godModeUserLabel }) }}
      </div>
      <header class="top-bar glass-panel">
        <div class="left">
          <h2 class="session-title">{{ chatStore.currentChatTitle || $t('chat.default_title') }}</h2>
        </div>
        <div class="right">
          <ToolCog v-if="user.id" />
          <button v-else class="mango-button small signin-btn" @click="router.push('/login')">
            {{ $t('landing.nav.signin') }}
          </button>
          <div class="right-divider-v"></div>
          <div class="quick-settings-wrapper" @click.stop>
            <button class="icon-btn-top cogs-trigger" @click="showQuickSettings = !showQuickSettings">
              <svg viewBox="0 0 24 24"><path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.35 19.43,11.03L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.47,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.53,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11.03C4.53,11.35 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.04 4.95,18.95L7.44,17.95C7.96,18.34 8.53,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.47,18.68 16.04,18.34 16.56,17.95L19.05,18.95C19.27,19.04 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z"/></svg>
            </button>
            <transition name="menu-pop">
              <div v-if="showQuickSettings" class="quick-settings-menu glass-panel shadow-premium">
                 <button @click="uiStore.setTheme(uiStore.theme === 'dark' ? 'light' : 'dark')" :title="$t('settings.interface.theme.title')">
                   <svg viewBox="0 0 24 24"><path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20V4Z"/></svg>
                 </button>
                 <button @click="uiStore.setLang(uiStore.lang === 'en' ? 'vi' : 'en')" :title="$t('settings.interface.language')">
                   <b>{{ uiStore.lang.toUpperCase() }}</b>
                 </button>
                 <button @click="uiStore.setScale(uiStore.scale + 0.1)" title="+">
                   <b>A+</b>
                 </button>
                 <button @click="uiStore.setScale(uiStore.scale - 0.1)" title="-">
                   <b>A-</b>
                 </button>
              </div>
            </transition>
          </div>
        </div>
      </header>
      
      <div class="chat-body" :class="uiStore.layout" @contextmenu.prevent="showDesktopMenu">
        
        <!-- Desktop Context Menu -->
        <transition name="menu-pop">
          <div v-if="desktopMenu.show" 
               class="desktop-menu glass-panel shadow-premium" 
               :style="{ top: desktopMenu.y + 'px', left: desktopMenu.x + 'px' }">
            <button class="context-item" @click="uiStore.resetWindows(); desktopMenu.show = false">
               {{ $t('settings.interface.reset_layout') || t('chat.view.reset_layout') }}
            </button>
            <button class="context-item" @click="uiStore.maximizeAll(); desktopMenu.show = false">
               {{ t('chat.view.maximize_all') }}
            </button>
            <button class="context-item" @click="uiStore.minimizeAll(); desktopMenu.show = false">
               {{ t('chat.view.minimize_all') }}
            </button>
          </div>
        </transition>

        <!-- Chat Window -->
        <div v-if="!uiStore.windows.chat.minimized" 
             class="window-frame chat-win"
             :class="{ floating: uiStore.windows.chat.floating }"
             @click.stop
             @contextmenu.stop
             :style="uiStore.windows.chat.floating ? { 
               top: uiStore.windows.chat.y + 'px', 
               left: uiStore.windows.chat.x + 'px',
               width: uiStore.windows.chat.w + 'px',
               height: uiStore.windows.chat.h + 'px',
               zIndex: uiStore.windows.chat.order
             } : { order: uiStore.windows.chat.order || 1 }">
          <div class="win-header" @mousedown="startDrag('chat', $event)">
            <span class="win-title">{{ currentChatTitle }}</span>
            <div class="win-controls">
              <button v-if="!uiStore.windows.chat.floating" @click="undock('chat')">
                <svg viewBox="0 0 24 24"><path d="M19,19H5V5H19V19M19,3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3Z"/></svg>
              </button>
              <button @click="minimize('chat')">
                <svg viewBox="0 0 24 24"><path d="M20,14H4V10H20V14Z"/></svg>
              </button>
            </div>
          </div>
          
          <div class="messages-container" ref="messagesContainer" @scroll="handleMessageScroll">
            <div v-if="chatStore.messages.length === 0" class="welcome-container">
               <h1 class="hero-text"><span class="mango-text">{{ $t('chat.welcome_title') }}</span></h1>
               <div class="suggestions-grid">
                 <div v-for="s in suggestions" :key="s.text" class="suggestion-card glass-panel" @click="useSuggestion(s.text)">
                    <div class="s-icon">
                      <svg v-if="s.icon === 'code'" viewBox="0 0 24 24"><path d="M8,3L9,4L4,9L9,14L8,15L2,9L8,3M16,3L15,4L20,9L15,14L16,15L22,9L16,3Z"/></svg>
                      <svg v-if="s.icon === 'search'" viewBox="0 0 24 24"><path d="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"/></svg>
                      <svg v-if="s.icon === 'shield'" viewBox="0 0 24 24"><path d="M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1M12,7C13.4,7 14.8,11.24 14.8,11.24L16,11V11C16,11 16,11 16,11L14.8,11.24C14.8,11.24 13.4,15.48 12,15.48C10.6,15.48 9.2,11.24 9.2,11.24L8,11V11C8,11 8,11 8,11L9.2,11.24C9.2,11.24 10.6,7 12,7Z"/></svg>
                      <svg v-if="s.icon === 'folder'" viewBox="0 0 24 24"><path d="M10,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8C22,6.89 21.1,6 20,4H12L10,4Z"/></svg>
                    </div>
                    <div class="s-content">
                       <span class="s-text">{{ s.text }}</span>
                       <span class="s-sub">{{ s.sub }}</span>
                    </div>
                 </div>
               </div>
            </div>
            <div v-else class="virtual-message-list" :style="{ height: `${totalVirtualHeight}px` }">
              <div class="virtual-spacer" :style="{ height: `${topSpacerHeight}px` }"></div>
              <ChatMessage 
                v-for="entry in visibleMessages"
                :key="entry.index"
                :message="entry.message" 
                :index="entry.index" 
                @hitl-response="chatStore.sendInputResponse"
                @triage-action="chatStore.handleTriageAction"
              />
              <div class="virtual-spacer" :style="{ height: `${bottomSpacerHeight}px` }"></div>
            </div>
          </div>

          <footer class="input-area-gemini">
             <div v-if="isGodMode" class="god-mode-chat-lock glass-panel">
                {{ t('god_mode.chat_read_only_notice') }}
             </div>
             <div v-else class="pill-input-wrapper glass-panel">
                <button class="pill-btn" @click="fileInput.click()">
                  <svg viewBox="0 0 24 24"><path d="M16.5,6V17.5A4,4 0 0,1 12.5,21.5A4,4 0 0,1 8.5,17.5V5A2.5,2.5 0 0,1 11,2.5A2.5,2.5 0 0,1 13.5,5V15.5A1,1 0 0,1 12.5,16.5A1,1 0 0,1 11.5,15.5V6H10V15.5A2.5,2.5 0 0,0 12.5,18A2.5,2.5 0 0,0 12.5,18.5V5A4,4 0 0,0 11,1A4,4 0 0,0 7,5V17.5A5.5,5.5 0 0,0 12.5,23A5.5,5.5 0 0,0 18,17.5V6H16.5Z"/></svg>
                </button>
                <input type="file" ref="fileInput" hidden multiple @change="handleAttachmentSelection" />
                <textarea v-model="newMessage" rows="1" :placeholder="$t('chat.input_placeholder')" @keydown.enter.prevent="handleEnterKey" class="gemini-textarea"></textarea>
                <div class="right-actions">
                   <ModelSelector />
                   <button class="send-btn-pill" :disabled="!newMessage.trim()" @click="sendMessage">
                      <svg viewBox="0 0 24 24"><path d="M2,21L23,12L2,3V10L17,12L2,14V21Z"/></svg>
                   </button>
                </div>
             </div>
          </footer>
          <div v-if="uiStore.windows.chat.floating" class="resizer" @mousedown="startResize('chat', $event)"></div>
        </div>

        <!-- Workspace Window -->
        <div v-if="!uiStore.windows.workspace.minimized" 
             class="window-frame ws-win"
             :class="{ floating: uiStore.windows.workspace.floating }"
             @click.stop
             @contextmenu.stop
             :style="uiStore.windows.workspace.floating ? { 
               top: uiStore.windows.workspace.y + 'px', 
               left: uiStore.windows.workspace.x + 'px',
               width: uiStore.windows.workspace.w + 'px',
               height: uiStore.windows.workspace.h + 'px',
               zIndex: uiStore.windows.workspace.order
             } : { order: uiStore.windows.workspace.order || 2 }">
          <div class="win-header" @mousedown="startDrag('workspace', $event)">
            <span class="win-title">
              {{ t('chat.view.workspace_quota', { quota: user.role === 'admin' ? t('chat.view.unlimited') : `${formatSize(user.quota_used_bytes || 0)} / 5 GB` }) }}
            </span>
            <div class="win-controls">
              <button v-if="!uiStore.windows.workspace.floating" @click="undock('workspace')">
                <svg viewBox="0 0 24 24"><path d="M19,19H5V5H19V19M19,3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3Z"/></svg>
              </button>
              <button @click="minimize('workspace')">
                <svg viewBox="0 0 24 24"><path d="M20,14H4V10H20V14Z"/></svg>
              </button>
            </div>
          </div>
          <div class="ws-content" style="padding: 0; background: var(--bg-primary); height: 100%;">
            <WorkspaceDesktop @open-file="openFile" />
          </div>
          <div v-if="uiStore.windows.workspace.floating" class="resizer" @mousedown="startResize('workspace', $event)"></div>
        </div>

      </div>

      <div class="min-tray">
         <div v-if="uiStore.windows.chat.minimized" class="tray-item glass-panel" @click="restore('chat')">
           <svg viewBox="0 0 24 24"><path d="M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22A10,10 0 0,1 2,12A10,10 0 0,1 12,2M12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4M12,6A6,6 0 0,1 18,12A6,6 0 0,1 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6M12,8A4,4 0 0,0 8,12A4,4 0 0,0 12,16A4,4 0 0,0 16,12A4,4 0 0,0 12,8Z"/></svg>
           <span>{{ $t('nav.chat') }}</span>
         </div>
         <div v-if="uiStore.windows.workspace.minimized" class="tray-item glass-panel" @click="restore('workspace')">
           <svg viewBox="0 0 24 24"><path d="M10,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8C22,6.89 21.1,6 20,4H12L10,4Z"/></svg>
           <span>{{ $t('nav.workspace') }}</span>
         </div>
         <div v-if="uiStore.windows.admin.minimized && user?.role === 'admin'" class="tray-item glass-panel" @click="restore('admin')">
           <svg viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.77 3.77z"/></svg>
           <span>{{ $t('admin.title') }}</span>
         </div>
         <div v-if="uiStore.windows.userSettings.minimized" class="tray-item glass-panel" @click="restore('userSettings')">
           <svg viewBox="0 0 24 24"><path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.35 19.43,11.03L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.47,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.53,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11.03C4.53,11.35 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.04 4.95,18.95L7.44,17.95C7.96,18.34 8.53,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.47,18.68 16.04,18.34 16.56,17.95L19.05,18.95C19.27,19.04 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" /></svg>
           <span>{{ $t('nav.settings') }}</span>
         </div>
      </div>

      <NotificationStation />
    </main>

    <!-- File Preview Moved outside of main to solve z-index stacking issues with sidebar -->
    <FilePreviewOverlay 
      v-if="previewState.show" 
      :show="previewState.show" 
      :file="previewState.file"
      @close="previewState.show = false"
    />
  </div>
</template>

<style scoped>
.chat-page { display: flex; height: 100vh; background: var(--bg-primary); overflow: hidden; }

/* Sidebar Evolution */
.sidebar {
  width: 280px;
  border: 1px solid var(--border-strong);
  border-radius: 16px;
  margin: 12px 0 12px 12px;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 100;
  background: var(--bg-glass);
  user-select: none;
}

.sidebar-header { padding: 24px; display: flex; justify-content: space-between; align-items: center; }
.new-chat-btn {
  width: 32px; height: 32px; border-radius: 8px; border: 1px solid var(--border-strong);
  background: var(--bg-tertiary); color: var(--text-primary); cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.new-chat-btn svg { width: 20px; fill: currentColor; }
.new-chat-btn:hover { border-color: var(--mango-primary); color: var(--mango-primary); }
.new-chat-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.sidebar-search { padding: 0 16px 16px; }
.search-input-wrapper {
  background: var(--bg-tertiary); border: 1px solid var(--border-subtle); border-radius: 12px;
  display: flex; align-items: center; padding: 6px 12px; gap: 8px;
}
.search-icon { width: 14px; opacity: 0.4; fill: currentColor; }
.search-input-wrapper input { border: none; background: transparent; color: var(--text-primary); font-size: 13px; outline: none; flex: 1; }

.sidebar-navigation { padding: 0 12px 16px; border-bottom: 1px solid var(--border-subtle); display: flex; flex-direction: column; gap: 4px; }
.sidebar-nav-item {
  width: 100%; padding: 10px 14px; border-radius: 10px; border: none; background: transparent;
  color: var(--text-secondary); display: flex; align-items: center; gap: 12px; cursor: pointer;
  transition: all 0.2s; font-size: 14px; font-weight: 600;
}
.sidebar-nav-item svg { width: 18px; fill: currentColor; opacity: 0.7; }
.sidebar-nav-item:hover, .sidebar-nav-item.active { background: rgba(255,255,255,0.05); color: var(--text-primary); }
.sidebar-nav-item.active { border: 1px solid var(--border-subtle); color: var(--mango-primary); }
.sidebar-nav-item.active svg { color: var(--mango-primary); opacity: 1; }

.sidebar-nav-label { padding: 16px 24px 8px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; opacity: 0.4; }

.conversation-list { flex: 1; overflow-y: auto; padding: 0 12px; }
.chat-item { 
  padding: 10px 14px; border-radius: 10px; cursor: pointer; transition: all 0.2s;
  font-size: 13px; margin-bottom: 2px;
}
.chat-item:hover { background: rgba(255,255,255,0.03); }
.chat-item.active { background: rgba(255, 122, 0, 0.05); color: var(--mango-primary); font-weight: 700; }
.chat-item.omni-pinned { border-left: 3px solid var(--mango-primary); background: rgba(255, 170, 0, 0.03); margin-bottom: 8px; }
.omni-status { width: 6px; height: 6px; border-radius: 50%; background: var(--mango-primary); box-shadow: 0 0 8px var(--mango-primary); position: absolute; right: 12px; top: 50%; transform: translateY(-50%); }

.sidebar-footer-grid { 
  padding: 16px; border-top: 1px solid var(--border-subtle); 
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
}
.f-btn {
  height: 40px; border-radius: 10px; border: 1px solid transparent; background: rgba(255,255,255,0.03);
  color: var(--text-secondary); display: flex; align-items: center; justify-content: center; cursor: pointer;
  transition: all 0.2s;
}
.f-btn svg { width: 18px; fill: currentColor; }
.f-btn:hover { background: rgba(255,255,255,0.08); color: var(--text-primary); border-color: var(--border-subtle); }
.f-btn.logout:hover { color: var(--danger); background: rgba(255, 0, 0, 0.05); border-color: rgba(255,0,0,0.1); }


/* Main Area */
.chat-main { 
  flex: 1; 
  display: flex; 
  flex-direction: column; 
  position: relative; 
  z-index: 10; 
  overflow: hidden; 
}
.god-mode-readout {
  margin: 12px 12px 0;
  padding: 12px 16px;
  border-radius: 16px;
  border: 1px solid rgba(255, 170, 0, 0.25);
  background: rgba(255, 170, 0, 0.08);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}
.top-bar { 
  height: 60px; 
  border: 1px solid var(--border-strong);
  border-radius: 16px;
  margin: 12px 12px 0 12px;
  display: flex; 
  align-items: center; 
  justify-content: space-between; 
  padding: 0 24px; 
  position: relative; 
  z-index: 2000; 
  background: var(--bg-glass);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
body.dock-target .top-bar {
  border-color: var(--mango-primary);
  box-shadow: 0 0 20px var(--mango-glow);
  transform: scale(1.01);
}
.session-title { font-size: 15px; font-weight: 700; }
.right { display: flex; align-items: center; gap: 12px; }
.divider-v { width: 1px; height: 20px; background: var(--border-subtle); }
.icon-btn-top { background: transparent; border: none; color: var(--text-secondary); cursor: pointer; padding: 6px; border-radius: 6px; transition: all 0.2s; }
.icon-btn-top:hover { background: rgba(255,255,255,0.05); color: var(--text-primary); }
.icon-btn-top svg { width: 18px; fill: currentColor; }

.chat-body { flex: 1; position: relative; overflow: hidden; padding: 12px; gap: 12px; }
.chat-body.split { 
  display: grid; 
  grid-template-columns: 1fr 1fr; 
  padding: 0; /* Zero-gap request */
  gap: 0; 
}

.chat-body.split .window-frame {
  border: none;
  border-right: 1px solid var(--border-subtle);
}
.chat-body.split .window-frame:last-child {
  border-right: none;
}
.window-frame { 
  background: var(--bg-secondary); border-radius: 16px; border: 1px solid var(--border-subtle); 
  display: flex; flex-direction: column; overflow: hidden; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.window-frame.floating { position: absolute; z-index: 1000; box-shadow: 0 40px 100px rgba(0,0,0,0.5); background: var(--bg-glass); }

.win-header { height: 44px; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; cursor: grab; }
.win-title { font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; opacity: 0.5; }
.win-controls { display: flex; gap: 4px; }
.win-controls button { width: 32px; height: 32px; border-radius: 6px; background: transparent; border: none; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.win-controls button:hover { background: rgba(255,255,255,0.05); color: var(--text-primary); }
.win-controls svg { width: 16px; fill: currentColor; }

.messages-container { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 24px; }

/* Welcome Screen */
.welcome-container { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 60px; }
.hero-text { font-size: 3rem; font-weight: 900; letter-spacing: -1.5px; }

.suggestions-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; width: 100%; max-width: 900px; }
.suggestion-card { padding: 24px; border-radius: 20px; text-align: left; cursor: pointer; transition: all 0.3s; border: 1px solid var(--border-subtle); background: var(--bg-glass); }
.suggestion-card:hover { border-color: var(--mango-primary); background: rgba(255, 170, 0, 0.05); transform: translateY(-6px); }
.s-icon { width: 32px; height: 32px; margin-bottom: 16px; color: var(--mango-primary); }
.s-icon svg { width: 100%; fill: currentColor; }
.s-text { font-weight: 800; font-size: 15px; display: block; margin-bottom: 6px; }
.s-sub { font-size: 12px; opacity: 0.5; line-height: 1.4; }

/* Input Gemini Style */
.input-area-gemini { padding: 0 60px 48px; flex-shrink: 0; }
.god-mode-chat-lock {
  padding: 16px 20px;
  border-radius: 24px;
  border: 1px solid rgba(255, 170, 0, 0.25);
  background: rgba(255, 170, 0, 0.08);
  color: var(--text-primary);
  text-align: center;
  font-weight: 700;
}
.pill-input-wrapper { background: var(--bg-tertiary); border-radius: 36px; border: 1px solid var(--border-strong); display: flex; align-items: flex-end; padding: 12px 20px; gap: 16px; transition: all 0.3s; }
.pill-input-wrapper:focus-within { border-color: var(--mango-primary); box-shadow: 0 0 40px rgba(0, 255, 136, 0.1); }

.gemini-textarea { flex: 1; background: transparent; border: none; color: var(--text-primary); padding: 12px 0; font-size: 16px; outline: none; resize: none; max-height: 200px; line-height: 1.5; }
.pill-btn { background: transparent; border: none; color: var(--text-secondary); cursor: pointer; padding: 10px; border-radius: 50%; transition: all 0.2s; }
.pill-btn:hover { background: rgba(255,255,255,0.05); color: var(--mango-primary); }
.pill-btn svg { width: 22px; fill: currentColor; }

.right-actions { display: flex; align-items: center; gap: 16px; padding-bottom: 6px; }
.send-btn-pill { width: 44px; height: 44px; border-radius: 50%; background: var(--mango-primary); color: white; border: none; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; box-shadow: 0 10px 20px var(--mango-glow); }
.send-btn-pill:disabled { opacity: 0.3; cursor: not-allowed; box-shadow: none; }
.send-btn-pill svg { width: 20px; fill: currentColor; }

.min-tray { position: absolute; bottom: 32px; right: 32px; display: flex; gap: 16px; z-index: 2000; }
.tray-item { padding: 10px 20px; border-radius: 14px; font-size: 13px; font-weight: 800; cursor: pointer; display: flex; align-items: center; gap: 10px; border: 1px solid var(--border-strong); box-shadow: 0 10px 40px rgba(0,0,0,0.5); }
.tray-item svg { width: 16px; fill: currentColor; }
.tray-item:hover { background: var(--mango-primary); color: white; border-color: var(--mango-primary); }

.ws-content { flex: 1; overflow: hidden; }
.resizer { position: absolute; right: 0; bottom: 0; width: 12px; height: 12px; cursor: nwse-resize; z-index: 10; }
.right-divider-v { width: 1px; height: 24px; background: var(--border-subtle); margin: 0 4px; }
.signin-btn { height: 32px; padding: 0 16px; font-size: 12px; border-radius: 8px; font-weight: 800; display: flex; align-items: center; }

/* Quick Settings */
.quick-settings-wrapper { position: relative; display: flex; align-items: center; }
.cogs-trigger svg { transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1); margin: 0; }
.cogs-trigger:hover svg { transform: rotate(180deg); color: var(--mango-primary); }

.quick-settings-menu {
  position: absolute; top: 100%; right: 0; width: 150px;
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; padding: 14px;
  border-radius: 20px; margin-top: 10px; z-index: 5000;
  background: var(--bg-glass); backdrop-filter: var(--glass-blur); 
  border: 1px solid var(--border-strong);
}
.reset-btn-wide { grid-column: span 2; width: 100% !important; border-radius: 12px !important; }
.quick-settings-menu button {
  background: rgba(255,255,255,0.08); border: 1px solid var(--border-subtle); border-radius: 10px;
  display: flex; align-items: center; justify-content: center; width: 50px; height: 50px; 
  color: var(--text-primary); cursor: pointer; transition: 0.2s; justify-self: center;
}
.quick-settings-menu button:hover { background: var(--mango-primary); color: white; border-color: transparent; }
.quick-settings-menu svg { width: 20px; fill: currentColor; }

/* Work Chat Box */
.work-chat-box {
  margin: 0 16px 16px; padding: 12px; border-radius: 12px;
  border: 1.5px dashed var(--border-strong); min-height: 60px;
  display: flex; align-items: center; justify-content: center; text-align: center;
}
.wc-empty { font-size: 11px; color: var(--text-disabled); font-weight: 500; padding: 8px; }
.wc-active { display: flex; align-items: center; justify-content: space-between; width: 100%; }
.wc-title { font-size: 12px; font-weight: 600; color: var(--mango-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.wc-clear { background: transparent; border: none; color: var(--text-secondary); cursor: pointer; padding: 4px; font-size: 14px; transition: color 0.2s; }
.wc-clear:hover { color: var(--danger); }

[data-theme='light'] .settings-panel:hover {
  background: var(--bg-glass) !important;
}

/* Footer Buttons Labels */
.sidebar-footer-grid { position: relative; }
.sidebar-footer-grid .f-btn { position: relative; }

.hover-label {
  position: absolute; left: calc(100% + 20px); top: 50%; transform: translateY(-50%);
  background: var(--bg-tertiary); color: var(--text-primary); padding: 6px 12px;
  border-radius: 8px; font-size: 11px; font-weight: 800; white-space: nowrap;
  opacity: 0; pointer-events: none; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid var(--border-strong); box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  z-index: 100;
}

.f-btn:hover .hover-label { 
  opacity: 1; 
  pointer-events: auto;
  transform: translateY(-50%) translateX(4px); 
}

.hover-label::before {
  content: ''; position: absolute; right: 100%; top: 50%; transform: translateY(-50%);
  border: 6px solid transparent; border-right-color: var(--border-strong);
}

.parallelogram-i { width: 22px; height: 22px; }
.admin-btn svg { color: var(--mango-primary); }

/* Desktop Context Menu */
.desktop-menu {
  position: fixed; z-index: 9999;
  min-width: 180px; padding: 6px;
  background: var(--bg-glass); border: 1px solid var(--border-strong);
  border-radius: 12px; backdrop-filter: blur(20px);
}
.context-item {
  width: 100%; display: block; text-align: left;
  padding: 8px 12px; border-radius: 8px; font-size: 13px; font-weight: 600;
  color: var(--text-primary); cursor: pointer; transition: all 0.2s; background: transparent; border: none;
}
.context-item:hover {
  background: var(--bg-tertiary);
  color: var(--mango-primary);
}

.virtual-message-list {
  position: relative;
  width: 100%;
}

.virtual-spacer {
  width: 100%;
  flex: 0 0 auto;
}

</style>
