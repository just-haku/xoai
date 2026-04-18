<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import FileExplorer from './FileExplorer.vue'
import WorkspaceContent from './WorkspaceContent.vue'

const sidebarWidth = ref(250)
const isDragging = ref(false)
const selectedPath = ref('')

const emit = defineEmits(['open-file'])

const startDrag = () => {
  isDragging.value = true
}

const onDrag = (e) => {
  if (!isDragging.value) return
  const newWidth = e.clientX - 100 // Approximate offset
  if (newWidth > 150 && newWidth < 600) {
    sidebarWidth.value = newWidth
  }
}

const stopDrag = () => {
  isDragging.value = false
}

const handleSelect = (path) => {
  selectedPath.value = path
}

const handleOpenFile = (file) => {
  if (file.type === 'dir') {
    selectedPath.value = file.path
  } else {
    emit('open-file', file)
  }
}

onMounted(() => {
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', stopDrag)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', stopDrag)
})
</script>

<template>
  <div class="workspace-desktop">
    <div class="ws-main">
      <div class="ws-sidebar" :style="{ width: sidebarWidth + 'px' }">
        <FileExplorer @select="handleSelect" />
      </div>

      <div class="ws-resizer" @mousedown="startDrag"></div>

      <div class="ws-content-area">
        <WorkspaceContent 
          :current-path="selectedPath" 
          @open="handleOpenFile" 
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.workspace-desktop {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.ws-header {
  height: 36px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  padding: 0 16px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  opacity: 0.6;
}

.ws-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.ws-sidebar {
  height: 100%;
  overflow-y: auto;
  background: var(--bg-tertiary);
}

.ws-resizer {
  width: 4px;
  background: transparent;
  cursor: col-resize;
  transition: background 0.2s;
  z-index: 10;
}
.ws-resizer:hover, .ws-resizer:active {
  background: var(--mango-primary);
}

.ws-content-area {
  flex: 1;
  height: 100%;
  overflow: hidden;
  position: relative;
}
</style>
