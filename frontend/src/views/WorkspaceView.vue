<script setup>
import { ref, reactive, onMounted } from 'vue'
import FileExplorer from '../components/FileExplorer.vue'
import ChatMessage from '../components/ChatMessage.vue'
import { useChatStore } from '../stores/chat'
import GlobalSettingsHub from '../components/GlobalSettingsHub.vue'

const chatStore = useChatStore()
const showChat = ref(true)
const chatPos = reactive({ x: window.innerWidth - 450, y: 100 })
const chatSize = reactive({ w: 380, h: 500 })
const newMessage = ref('')

const saveChatState = () => {
  localStorage.setItem('xoai_chat_mini_state', JSON.stringify({ pos: chatPos, size: chatSize }))
}

onMounted(() => {
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
    <header class="workspace-header glass-panel">
      <div class="left">
        <svg viewBox="0 0 24 24" class="header-icon"><path d="M19,3H5C3.89,3 3,3.89 3,5V19C3,20.11 3.89,21 5,21H19C20.11,21 21,20.11 21,19V5C21,3.89 20.11,3 19,3M19,19H5V5H19V19M17,17H7V15H17V17M17,13H7V11H17V13M17,9H7V7H17V9Z"/></svg>
        <h2 class="title">System Workspace</h2>
      </div>
      <div class="right">
        <button class="icon-btn" @click="showChat = !showChat" :title="showChat ? 'Hide Chat' : 'Show Chat'">
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
          <span class="title">Personal Assistant</span>
          <button class="close-btn" @click="showChat = false">
            <svg viewBox="0 0 24 24" class="svg-icon-small"><path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/></svg>
          </button>
        </div>
        <div class="chat-modal-body">
          <div class="messages-lite" ref="msgLite">
            <ChatMessage v-for="(msg, idx) in chatStore.messages" 
                         :key="idx" :message="msg" is-lite />
          </div>
          <div class="input-lite">
            <input v-model="newMessage" @keyup.enter="handleSend" placeholder="Type to chat..." />
          </div>
        </div>
        <div class="resizer" @mousedown="startResize"></div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.workspace-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
}

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
