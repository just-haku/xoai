<script setup>
import { ref, onMounted, nextTick, watch, reactive } from 'vue'
import { useChatStore } from '../stores/chat'
import ToolCog from '../components/ToolCog.vue'
import FileExplorer from '../components/FileExplorer.vue'
import ModelSelector from '../components/ModelSelector.vue'
import ChatMessage from '../components/ChatMessage.vue'
import GlobalSettingsHub from '../components/GlobalSettingsHub.vue'

const chatStore = useChatStore()
const newMessage = ref('')
const messagesContainer = ref(null)

// Workspace Draggable/Resizable State
const showWorkspace = ref(true)
const wsPos = reactive({ x: 100, y: 100 })
const wsSize = reactive({ w: 320, h: 450 })

onMounted(() => {
  chatStore.connect('default_conversation')
})

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

watch(() => chatStore.messages.length, scrollToBottom)

const handleSend = () => {
  if (!newMessage.value.trim()) return
  chatStore.sendMessage(newMessage.value)
  newMessage.value = ''
  scrollToBottom()
}

// Draggable Logic
let isDragging = false
let startX, startY, startPosX, startPosY

const startDrag = (e) => {
  if (e.target.tagName === 'BUTTON') return
  isDragging = true
  startX = e.clientX
  startY = e.clientY
  startPosX = wsPos.x
  startPosY = wsPos.y
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

const onDrag = (e) => {
  if (!isDragging) return
  wsPos.x = startPosX + (e.clientX - startX)
  wsPos.y = startPosY + (e.clientY - startY)
}

const stopDrag = () => {
  isDragging = false
  document.body.style.userSelect = 'auto'
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  saveWsState()
}

const stopResize = () => {
  isResizing = false
  document.body.style.userSelect = 'auto'
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  saveWsState()
}

const saveWsState = () => {
  localStorage.setItem('xoai_ws_state', JSON.stringify({ pos: wsPos, size: wsSize }))
}

onMounted(() => {
  chatStore.connect('default_conversation')
  const saved = localStorage.getItem('xoai_ws_state')
  if (saved) {
    const { pos, size } = JSON.parse(saved)
    Object.assign(wsPos, pos)
    Object.assign(wsSize, size)
  }
})
</script>

<template>
  <div class="chat-page">
    <!-- Sidebar -->
    <aside class="sidebar glass-panel">
      <div class="sidebar-header">
        <h3>{{ $t('chat.chat_list') || 'Chats' }}</h3>
        <button class="new-chat-btn" @click="chatStore.newChat" :title="$t('chat.new_chat')">+</button>
      </div>
      <div class="conversation-list">
        <div v-for="chat in chatStore.conversations" :key="chat.id" 
             class="chat-item" :class="{active: chatStore.currentChatId === chat.id}"
             @click="chatStore.switchChat(chat.id)">
          <div class="chat-info">
            <svg viewBox="0 0 24 24" class="item-icon"><path d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4A2,2 0 0,0 20,2M20,16H5.17L4,17.17V4H20V16M11,10H13V12H11V10M11,6H13V8H11V6M11,14H13V16H11V14Z"/></svg>
            <span class="chat-title">{{ chat.title || $t('chat.default_title') || 'Discovery Session' }}</span>
          </div>
          <div class="chat-actions">
            <button class="mini-action" @click.stop="chatStore.forkChat(chat.id)" :title="$t('chat.fork')">
              <svg viewBox="0 0 24 24" class="mini-svg"><path d="M11,9V13H7V11H13V17H11V15H7V19H13V21H15V3H13V5H7V9H11M7,7V5H11V7H7M7,13V15H11V13H7M7,21H11V19H7V21Z"/></svg>
            </button>
            <button class="mini-action" @click.stop="chatStore.renameChat(chat.id)" :title="$t('chat.rename')">
              <svg viewBox="0 0 24 24" class="mini-svg"><path d="M20.71,7.04C21.1,6.65 21.1,6.02 20.71,5.63L18.37,3.29C17.98,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z"/></svg>
            </button>
            <button class="mini-action danger" @click.stop="chatStore.deleteChat(chat.id)" :title="$t('chat.trash')">
              <svg viewBox="0 0 24 24" class="mini-svg"><path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19V4M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"/></svg>
            </button>
          </div>
        </div>
      </div>
    </aside>
    
    <main class="chat-main">
      <!-- Top Bar -->
      <header class="chat-header glass-panel">
        <div class="left">
          <ToolCog />
          <h2 class="chat-title-main">{{ chatStore.currentChatTitle || 'Session' }}</h2>
        </div>
        <div class="right">
          <ModelSelector />
          <div class="divider-v"></div>
          <GlobalSettingsHub />
        </div>
      </header>
      
      <!-- Chat Body -->
      <div class="chat-body">
        <div class="messages-container" ref="messagesContainer">
          <div v-if="chatStore.messages.length === 0" class="welcome-hero">
            <h1 class="mango-text">{{ $t('chat.welcome_title') || 'How can I help you today?' }}</h1>
            <p>{{ $t('chat.welcome_subtitle') || 'I am your multi-agent AI Operating System.' }}</p>
          </div>
          <ChatMessage v-for="(msg, idx) in chatStore.messages" 
                       :key="idx" :message="msg" />
        </div>
        
        <!-- Draggable/Resizable Workspace Window -->
        <div v-if="showWorkspace" 
             class="workspace-modal glass-panel"
             :style="{ 
               top: wsPos.y + 'px', 
               left: wsPos.x + 'px',
               width: wsSize.w + 'px',
               height: wsSize.h + 'px'
             }">
          <div class="ws-header" @mousedown="startDrag" @touchstart="startDrag">
            <svg viewBox="0 0 24 24" class="header-icon"><path d="M19,3H5V19H19V3M19,1H5A2,2 0 0,0 3,3V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V3A2,2 0 0,0 19,1M6,17H18V15H6V17M6,13H18V11H6V13M6,9H18V7H6V9Z"/></svg>
            <span class="title">{{ $t('workspace.files') }}</span>
            <button class="close-btn" @click="showWorkspace = false">
              <svg viewBox="0 0 24 24" class="svg-icon-small"><path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/></svg>
            </button>
          </div>
          <div class="ws-content">
             <FileExplorer />
          </div>
          <div class="resizer" @mousedown="startResize"></div>
        </div>
      </div>
      
      <!-- Input Area -->
      <footer class="input-area">
        <form @submit.prevent="handleSend" class="glass-panel input-wrapper">
          <div class="input-actions">
            <button type="button" class="action-btn" :title="$t('chat.toggle_workspace')" @click="showWorkspace = !showWorkspace">
              <svg viewBox="0 0 24 24" class="icon-svg"><path d="M19,3H5C3.89,3 3,3.89 3,5V19C3,20.11 3.89,21 5,21H19C20.11,21 21,20.11 21,19V5C21,3.89 20.11,3 19,3M19,19H5V5H19V19M17,17H7V15H17V17M17,13H7V11H17V13M17,9H7V7H17V9Z"/></svg>
            </button>
            <button type="button" class="action-btn" :title="$t('workspace.upload')">
              <svg viewBox="0 0 24 24" class="icon-svg"><path d="M16.5,6V17.5A4,4 0 0,1 12.5,21.5A4,4 0 0,1 8.5,17.5V5A2.5,2.5 0 0,1 11,2.5A2.5,2.5 0 0,1 13.5,5V15.5A1,1 0 0,1 12.5,16.5A1,1 0 0,1 11.5,15.5V6H10V15.5A2.5,2.5 0 0,0 12.5,18A2.5,2.5 0 0,0 12.5,18.5V5A4,4 0 0,0 11,1A4,4 0 0,0 7,5V17.5A5.5,5.5 0 0,0 12.5,23A5.5,5.5 0 0,0 18,17.5V6H16.5Z"/></svg>
            </button>
          </div>
          <input v-model="newMessage" type="text" :placeholder="$t('chat.input_placeholder')" />
          <button type="submit" class="send-btn" :disabled="!newMessage.trim()">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
            </svg>
          </button>
        </form>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.chat-page {
  flex: 1;
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-primary);
}

.sidebar {
  width: 280px;
  border-radius: 0;
  border-right: 1px solid var(--border-strong);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: var(--spacing-6);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.new-chat-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.new-chat-btn:hover {
  background: var(--mango-primary);
  border-color: var(--mango-primary);
  transform: scale(1.05);
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
}

.chat-item {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border-left: 3px solid transparent;
  position: relative;
  overflow: hidden;
}

.chat-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.chat-item.active {
  background: rgba(255, 122, 0, 0.08);
  border-left-color: var(--mango-primary);
  color: var(--mango-primary);
}

.chat-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.chat-title {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0.8;
}

.chat-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transform: translateX(10px);
  transition: all 0.2s ease;
}

.chat-item:hover .chat-actions {
  opacity: 1;
  transform: translateX(0);
}

.mini-action {
  background: transparent;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.mini-action:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  transform: scale(1.1);
}

.mini-action.danger:hover {
  background: rgba(239, 68, 68, 0.2);
  color: var(--danger);
}

.mini-svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
}

.item-icon {
  width: 18px;
  height: 18px;
  fill: currentColor;
  opacity: 0.6;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

.chat-header {
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-radius: 0;
  border-bottom: 1px solid var(--border-subtle);
}

.chat-header .left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chat-title-main {
  font-size: 16px;
  font-weight: 600;
  opacity: 0.9;
}

.chat-header .right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.divider-v {
  width: 1px;
  height: 24px;
  background: var(--border-subtle);
}

.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 40px;
  display: flex;
  flex-direction: column;
  gap: 32px;
  max-width: 1000px;
  width: 100%;
  margin: 0 auto;
}

.welcome-hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.workspace-modal {
  position: absolute;
  z-index: 100;
  display: flex;
  flex-direction: column;
  box-shadow: 0 30px 90px rgba(0,0,0,0.7);
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-strong);
  overflow: hidden;
}

.ws-header {
  height: 44px;
  padding: 0 16px;
  background: rgba(255, 122, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: move;
  border-bottom: 1px solid var(--border-subtle);
}

.ws-header .title { font-size: 13px; font-weight: 700; flex: 1; }

.ws-content {
  flex: 1;
  overflow: hidden;
}

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

.resizer:hover { opacity: 0.6; }

.close-btn {
  background: transparent;
  border: none;
  font-size: 20px;
  cursor: pointer;
  opacity: 0.5;
}

.close-btn:hover { opacity: 1; color: var(--danger); }

.input-area {
  padding: 24px;
}

.input-wrapper {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  border-radius: 20px;
}

.input-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  background: transparent;
  border: none;
  font-size: 20px;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.action-btn:hover { opacity: 1; }

input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 16px;
}

.send-btn {
  background: var(--mango-primary);
  border: none;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px var(--mango-glow);
}

.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>
