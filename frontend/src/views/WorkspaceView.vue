<script setup>
import { ref, reactive, onMounted } from 'vue'
import FileExplorer from '../components/FileExplorer.vue'
import ChatMessage from '../components/ChatMessage.vue'
import { useChatStore } from '../stores/chat'
import { useRouter, useRoute } from 'vue-router'
import { useUIStore } from '../stores/ui'
import GlobalSettingsHub from '../components/GlobalSettingsHub.vue'
import ToolCog from '../components/ToolCog.vue'
import { useI18n } from 'vue-i18n'

const chatStore = useChatStore()
const uiStore = useUIStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const showChat = ref(true)
const chatPos = reactive({ x: window.innerWidth - 450, y: 100 })
const chatSize = reactive({ w: 380, h: 500 })
const newMessage = ref('')
const isAdmin = ref(true)
const mode = ref('workspace') // Default for this view

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
}

const handleSupport = () => console.log('Support Click')

const logout = () => {
  localStorage.removeItem('xoai_token')
  router.push('/login')
}

const saveChatState = () => {
  localStorage.setItem('xoai_chat_mini_state', JSON.stringify({ pos: chatPos, size: chatSize }))
}

onMounted(() => {
  mode.value = route.path.includes('workspace') ? 'workspace' : 'chat'
  const saved = localStorage.getItem('xoai_chat_mini_state')
  if (saved) {
    const { pos, size } = JSON.parse(saved)
    Object.assign(chatPos, pos)
    Object.assign(chatSize, size)
  }
})

// Drag logic
let isDragging = false
let startX, startY, startPosX, startPosY

const startDrag = (e) => {
  if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return
  isDragging = true
  document.body.style.userSelect = 'none'
  startX = e.clientX
  startY = e.clientY
  startPosX = chatPos.x
  startPosY = chatPos.y
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

const onDrag = (e) => {
  if (!isDragging) return
  chatPos.x = startPosX + (e.clientX - startX)
  chatPos.y = startPosY + (e.clientY - startY)
}

const stopDrag = () => {
  isDragging = false
  document.body.style.userSelect = 'auto'
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  saveChatState()
}

// Resize logic
let isResizing = false
let startW, startH

const startResize = (e) => {
  isResizing = true
  document.body.style.userSelect = 'none'
  startX = e.clientX
  startY = e.clientY
  startW = chatSize.w
  startH = chatSize.h
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
}

const onResize = (e) => {
  if (!isResizing) return
  chatSize.w = Math.max(300, startW + (e.clientX - startX))
  chatSize.h = Math.max(300, startH + (e.clientY - startY))
}

const stopResize = () => {
  isResizing = false
  document.body.style.userSelect = 'auto'
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  saveChatState()
}

const handleSend = () => {
  if (!newMessage.value.trim()) return
  chatStore.sendMessage(newMessage.value)
  newMessage.value = ''
}
</script>

<template>
  <div class="workspace-page">
    <!-- Shared Sidebar -->
    <aside class="sidebar glass-panel">
      <div class="sidebar-header">
        <h3>{{ $t('chat.chat_list') || t('workspace.chat_list') }}</h3>
      </div>
      <div class="conversation-list">
        <div v-for="chat in chatStore.conversations" :key="chat.id" 
             class="chat-item" @click="router.push('/')">
          <div class="chat-info">
            <svg viewBox="0 0 24 24" class="item-icon"><path d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4A2,2 0 0,0 20,2M20,16H5.17L4,17.17V4H20V16M11,10H13V12H11V10M11,6H13V8H11V6M11,14H13V16H11V14Z"/></svg>
            <span class="chat-title">{{ chat.title || t('workspace.discovery_session') }}</span>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <button class="nav-btn" @click="handleProfile">
          <svg viewBox="0 0 24 24" class="icon"><path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,8.39C13.57,8.39 14.85,9.67 14.85,11.24C14.85,12.81 13.57,14.09 12,14.09C10.43,14.09 9.15,12.81 9.15,11.24C9.15,9.67 10.43,8.39 12,8.39M12,18.78C9.84,18.78 7.96,17.69 6.86,16.03C6.88,14.31 10.3,13.37 12,13.37C13.7,13.37 17.12,14.31 17.14,16.03C16.04,17.69 14.16,18.78 12,18.78Z"/></svg>
          <span>{{ $t('nav.profile') }}</span>
        </button>
        <button class="nav-btn" @click="openSettings">
          <svg viewBox="0 0 24 24" class="icon"><path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.35 19.43,11.03L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.47,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.53,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11.03C4.53,11.35 4.5,11.67 4.5,12C4.5,11.67 19.47,11.35 19.43,11.03Z"/></svg>
          <span>{{ $t('nav.settings') }}</span>
        </button>
        <div class="divider"></div>
        <button class="nav-btn toggle" @click="toggleMode">
          <svg viewBox="0 0 24 24" class="icon"><path d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4A2,2 0 0,0 20,2M20,16H5.17L4,17.17V4H20V16M11,10H13V12H11V10M11,6H13V8H11V6M11,14H13V16H11V14Z"/></svg>
          <span>{{ mode === 'chat' ? $t('nav.workspace') : $t('nav.chat') }}</span>
        </button>
      </div>
    </aside>

    <div class="main-content">
      <header class="workspace-header glass-panel">
        <div class="left">
          <svg viewBox="0 0 24 24" class="header-icon"><path d="M19,3H5C3.89,3 3,3.89 3,5V19C3,20.11 3.89,21 5,21H19C20.11,21 21,20.11 21,19V5C21,3.89 20.11,3 19,3M19,19H5V5H19V19M17,17H7V15H17V17M17,13H7V11H17V13M17,9H7V7H17V9Z"/></svg>
          <h2 class="title">{{ t('workspace.system_workspace') }}</h2>
        </div>
        <div class="right">
          <button class="icon-btn" @click="showChat = !showChat" :title="showChat ? t('workspace.hide_chat') : t('workspace.show_chat')">
            <svg viewBox="0 0 24 24" class="svg-icon"><path d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4A2,2 0 0,0 20,2M20,16H5.17L4,17.17V4H20V16M11,10H13V12H11V10M11,6H13V8H11V6M11,14H13V16H11V14Z"/></svg>
          </button>
          <div class="divider-v"></div>
          <GlobalSettingsHub />
        </div>
      </header>
  
      <main class="workspace-main">
        <FileExplorer class="full-explorer" />
  
        <!-- Floating Mini-Chat Window -->
        <div v-if="showChat" 
             class="chat-modal glass-panel"
             :style="{ 
               top: chatPos.y + 'px', 
               left: chatPos.x + 'px',
               width: chatSize.w + 'px',
               height: chatSize.h + 'px'
             }">
          <div class="chat-modal-header" @mousedown="startDrag">
            <svg viewBox="0 0 24 24" class="icon"><path d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4A2,2 0 0,0 20,2M20,16H5.17L4,17.17V4H20V16M11,10H13V12H11V10M11,6H13V8H11V6M11,14H13V16H11V14Z"/></svg>
            <span class="title">{{ t('workspace.personal_assistant') }}</span>
            <button class="close-btn" @click="showChat = false">
              <svg viewBox="0 0 24 24" class="svg-icon-small"><path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/></svg>
            </button>
          </div>
          <div class="chat-modal-body">
            <div class="messages-lite" ref="msgLite">
              <ChatMessage v-for="(msg, idx) in chatStore.messages" 
                           :key="idx" :message="msg" :index="idx" is-lite
                           @hitl-response="chatStore.sendInputResponse"
                           @triage-action="chatStore.handleTriageAction" />
            </div>
            <div class="input-lite">
              <input v-model="newMessage" @keyup.enter="handleSend" :placeholder="t('workspace.type_to_chat')" />
            </div>
          </div>
          <div class="resizer" @mousedown="startResize"></div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.workspace-page {
  flex: 1;
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-primary);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.sidebar {
  width: 280px;
  border-radius: 0;
  border-right: 1px solid var(--border-strong);
  display: flex;
  flex-direction: column;
  background: rgba(18, 18, 18, 0.4);
}

.sidebar-header {
  padding: var(--spacing-6);
  color: var(--text-primary);
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.nav-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.nav-btn .icon { width: 18px; fill: currentColor; }
.nav-btn span { font-size: 13px; font-weight: 500; }

.divider { height: 1px; background: var(--border-subtle); margin: 4px 0; }

.conversation-list { flex: 1; overflow-y: auto; }
.chat-item { padding: 12px 16px; cursor: pointer; transition: 0.2s; }
.chat-item:hover { background: rgba(255,255,255,0.05); }
.chat-info { display: flex; align-items: center; gap: 12px; }
.item-icon { width: 18px; fill: currentColor; opacity: 0.6; }
.chat-title { font-size: 13px; opacity: 0.8; }

.workspace-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-radius: 0;
  border-bottom: 1px solid var(--border-subtle);
}

.workspace-header .left { display: flex; align-items: center; gap: 16px; }
.header-icon { width: 20px; fill: var(--mango-primary); }
.title { font-size: 16px; font-weight: 700; opacity: 0.9; }

.workspace-header .right { display: flex; align-items: center; gap: 16px; }

.workspace-main {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.full-explorer {
  width: 100% !important;
  height: 100%;
  border-left: none !important;
}

.chat-modal {
  position: absolute;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  box-shadow: 0 40px 100px rgba(0,0,0,0.8);
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-strong);
  overflow: hidden;
}

.chat-modal-header {
  height: 48px;
  padding: 0 16px;
  background: rgba(255, 122, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: move;
  border-bottom: 1px solid var(--border-subtle);
}

.chat-modal-header .icon { width: 18px; fill: currentColor; }
.chat-modal-header .title { font-size: 13px; font-weight: 700; flex: 1; opacity: 0.8; }

.chat-modal-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-lite {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-lite {
  padding: 12px;
  border-top: 1px solid var(--border-subtle);
}

.input-lite input {
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 8px 12px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
}

.input-lite input:focus { border-color: var(--mango-primary); }

.resizer {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 16px;
  height: 16px;
  cursor: nwse-resize;
  background: linear-gradient(135deg, transparent 50%, var(--mango-primary) 50%);
  opacity: 0.2;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 20px;
  cursor: pointer;
  opacity: 0.4;
}
.close-btn:hover { opacity: 1; color: var(--danger); }

.divider-v { width: 1px; height: 20px; background: var(--border-subtle); }
.icon-btn { background: transparent; border: none; cursor: pointer; color: var(--text-secondary); }
.icon-btn:hover { color: var(--mango-primary); }
.svg-icon { width: 20px; fill: currentColor; }
</style>
