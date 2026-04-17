<template>
  <div class="message-bubble" :class="message.role">
    <div class="avatar">
      <svg v-if="message.role === 'assistant'" viewBox="0 0 24 24" class="brand-icon"><path d="M12,2L14.39,4.39L12,6.78L9.61,4.39L12,2M3.36,4.91L5.75,7.3L3.36,9.69L0.97,7.3L3.36,4.91M2,12L4.39,9.61L6.78,12L4.39,14.39L2,12M4.91,20.64L7.3,18.25L9.69,20.64L7.3,23.03L4.91,20.64M12,22L9.61,19.61L12,17.22L14.39,19.61L12,22M20.64,19.09L18.25,16.7L20.64,14.31L23.03,16.7L20.64,19.09M22,12L19.61,14.39L17.22,12L19.61,9.61L22,12M19.09,3.36L16.7,5.75L14.31,3.36L16.7,0.97L19.09,3.36Z"/></svg>
      <svg v-else viewBox="0 0 24 24" class="user-icon"><path d="M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"/></svg>
    </div>
    <div class="content-wrapper">
      <div class="message-header">
        <span class="sender-name">{{ message.role === 'assistant' ? 'XOAI' : 'You' }}</span>
        <span class="time">{{ formatTime(message.timestamp) }}</span>
      </div>
      <div class="text glass-panel" :class="{ editing: isEditing }">
        <div v-if="!isEditing" class="markdown-body">
            <div v-if="message.type === 'input_required'" class="hitl-box">
                <div class="hitl-header">
                  <svg viewBox="0 0 24 24"><path d="M11,15H13V17H11V15M11,7H13V13H11V7M12,2C6.47,2 2,6.47 2,12C2,17.53 6.47,22 12,22C17.53,22 22,17.53 22,12C22,6.47 17.53,2 12,2M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20Z"/></svg>
                  <span>Action Approval Required</span>
                </div>
                <div class="hitl-content">
                    <p>Agent 02 (Executor) is requesting to run:</p>
                    <code>{{ message.tool }}: {{ formatArgs(message.args) }}</code>
                </div>
                <div v-if="!message.responded" class="hitl-actions">
                    <button class="deny-btn" @click="handleResponse('deny')">Deny</button>
                    <button class="allow-btn mango-button" @click="handleResponse('allow')">Allow Execution</button>
                </div>
                <div v-else class="hitl-status" :class="message.response">
                    {{ message.response === 'allow' ? '✓ Execution Approved' : '✕ Execution Denied' }}
                </div>
            </div>
            <div v-else-if="message.metadata?.type === 'triage_approval'" class="hitl-box triage-box">
                <div class="hitl-header" :class="message.metadata.classification">
                  <svg viewBox="0 0 24 24"><path d="M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22A10,10 0 0,1 2,12A10,10 0 0,1 12,2M12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4M12,6A6,6 0 0,1 18,12A6,6 0 0,1 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6M12,8A4,4 0 0,0 8,12A4,4 0 0,0 12,16A4,4 0 0,0 16,12A4,4 0 0,0 12,8Z"/></svg>
                  <span>Support Triage Approval: {{ message.metadata.classification.toUpperCase() }} CHANGE</span>
                </div>
                <div class="hitl-content">
                    <p>Agent 0 has triaged this ticket. Approve to activate A1 (Architect) and A2 (Executor) for resolution.</p>
                    <div class="triage-details" v-html="renderMarkdown(message.content)"></div>
                </div>
                <div v-if="!message.responded" class="hitl-actions">
                    <button class="deny-btn" @click="handleTriage('deny')">Close Ticket</button>
                    <button class="allow-btn mango-button" @click="handleTriage('approve')">Approve Resolution</button>
                </div>
                <div v-else class="hitl-status" :class="message.response">
                    {{ message.response === 'approve' ? '✓ Resolution Approved' : '✕ Ticket Closed' }}
                </div>
            </div>
            <div v-else v-html="renderMarkdown(message.content)"></div>
        </div>
        <div v-else class="editor-mode">
          <textarea v-model="editContent" rows="3" class="edit-textarea"></textarea>
          <div class="edit-actions">
            <button class="cancel-btn" @click="isEditing = false">Cancel</button>
            <button class="save-btn mango-button" @click="handleSave">Save & Fork</button>
          </div>
        </div>

        <!-- Action Bar -->
        <div v-if="!isEditing && message.role === 'user'" class="message-actions">
           <button class="msg-action-btn" @click="startEdit" title="Edit and Fork">
             <svg viewBox="0 0 24 24"><path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.07,6.19L3,17.25Z" /></svg>
           </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  message: Object,
  index: Number
})

const emit = defineEmits(['edit-fork', 'hitl-response', 'triage-action'])

const isEditing = ref(false)
const editContent = ref('')

const handleResponse = (response) => {
  if (props.message.responded) return
  emit('hitl-response', { index: props.index, response })
}

const handleTriage = (action) => {
  if (props.message.responded) return
  emit('triage-action', { index: props.index, action, ticketId: props.message.metadata.ticket_id })
}

const formatArgs = (args) => {
  if (typeof args === 'string') return args
  return JSON.stringify(args)
}

const startEdit = () => {
  editContent.value = props.message.content
  isEditing.value = true
}

const handleSave = () => {
  if (editContent.value !== props.message.content) {
    emit('edit-fork', { index: props.index, content: editContent.value })
  }
  isEditing.value = false
}

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const renderMarkdown = (text) => {
  if (!text) return ''
  return text.replace(/\n/g, '<br/>')
}
</script>

<style scoped>
.message-bubble {
  display: flex;
  gap: 12px;
  max-width: 85%;
  position: relative;
  margin-bottom: 24px;
}

.message-bubble.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  border: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.message-bubble.user .content-wrapper {
  align-items: flex-end;
}

.message-header {
  display: flex;
  gap: 12px;
  font-size: 11px;
  opacity: 0.6;
  padding: 0 4px;
}

.text {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  position: relative;
  transition: all 0.3s ease;
}

.text.editing {
  background: rgba(255, 255, 255, 0.05) !important;
  width: 100%;
}

.editor-mode {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.edit-textarea {
  width: 100%;
  background: rgba(0,0,0,0.2);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  color: white;
  padding: 12px;
  font-family: inherit;
  font-size: 14px;
  outline: none;
  resize: vertical;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.message-actions {
  position: absolute;
  top: 4px;
  right: -40px;
  opacity: 0;
  transition: opacity 0.2s;
  display: flex;
}

.message-bubble:hover .message-actions {
  opacity: 1;
}

.message-bubble.user:hover .message-actions {
  left: -40px;
  right: auto;
}

.msg-action-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
}

.msg-action-btn:hover {
  background: rgba(255,255,255,0.05);
  color: var(--mango-primary);
}

.msg-action-btn svg { width: 16px; fill: currentColor; }

.message-bubble.user .text {
  background: rgba(255, 122, 0, 0.15);
  border-bottom-right-radius: 2px;
  border-left: 2px solid var(--mango-primary);
}

.message-bubble.assistant .text {
  background: rgba(255, 255, 255, 0.03);
  border-bottom-left-radius: 2px;
  border-left: 2px solid var(--text-secondary);
}

/* HITL (Human In The Loop) Styling */
.hitl-box {
  margin-top: 8px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

.hitl-header {
  background: var(--bg-tertiary);
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--mango-primary);
  border-bottom: 1px solid var(--border-subtle);
}
.hitl-header svg { width: 14px; fill: currentColor; }

.hitl-content { padding: 16px; }
.hitl-content p { font-size: 13px; font-weight: 600; opacity: 0.7; margin-bottom: 8px; }
.hitl-content code {
  display: block;
  padding: 12px;
  background: rgba(255,122,0,0.05);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  word-break: break-all;
}

.hitl-actions {
  padding: 12px 16px;
  background: rgba(0,0,0,0.1);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.deny-btn {
  background: transparent; border: 1px solid var(--border-subtle);
  color: var(--text-secondary); padding: 8px 16px; border-radius: 8px;
  font-size: 12px; font-weight: 800; cursor: pointer; transition: all 0.2s;
}
.deny-btn:hover { background: rgba(255,0,0,0.05); color: var(--danger); }

.hitl-status {
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 900;
  text-align: center;
  text-transform: uppercase;
}
.hitl-status.allow, .hitl-status.approve { color: var(--accent-green); background: rgba(0, 255, 136, 0.05); }
.hitl-status.deny { color: var(--danger); background: rgba(255, 0, 0, 0.05); }

.triage-box .hitl-header.big { color: var(--danger); border-color: rgba(255,0,0,0.3); }
.triage-box .hitl-header.minor { color: var(--mango-primary); }
.triage-details { font-size: 13px; line-height: 1.5; opacity: 0.9; }

.cancel-btn {
  background: transparent;
  border: none;
  color: var(--text-primary);
  opacity: 0.6;
  cursor: pointer;
  font-size: 13px;
}
</style>
