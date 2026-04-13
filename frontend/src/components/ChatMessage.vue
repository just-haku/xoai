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
      <div class="text glass-panel">
        <div class="markdown-body" v-html="renderMarkdown(message.content)"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  message: Object
})

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const renderMarkdown = (text) => {
  // Simple fallback for now, real implementation would use a lib
  return text.replace(/\n/g, '<br/>')
}
</script>

<style scoped>
.message-bubble {
  display: flex;
  gap: 12px;
  max-width: 85%;
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
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
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
}

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
</style>
