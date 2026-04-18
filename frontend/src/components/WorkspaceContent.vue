<script setup>
import { ref, watch, onMounted } from 'vue'
import { api } from '../services/api'
import { useUIStore } from '../stores/ui'
import ContextMenu from './ContextMenu.vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  currentPath: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['open'])
const uiStore = useUIStore()
const { t } = useI18n()

const files = ref([])
const loading = ref(false)
const menu = ref(null)
const selectedFile = ref(null)
const isDragActive = ref(false)

const fetchFiles = async () => {
  loading.value = true
  try {
    const data = await api.request('/workspace/files?path=' + encodeURIComponent(props.currentPath))
    files.value = data.map(f => ({
      name: f.name,
      type: f.is_dir ? 'dir' : 'file',
      path: props.currentPath ? (props.currentPath + '/' + f.name) : f.name
    }))
  } catch (err) {
    uiStore.notify(t('workspace.notifications.load_failed', { error: err.message }), 'danger')
  } finally {
    loading.value = false
  }
}

watch(() => props.currentPath, fetchFiles)

const handleFileClick = (file) => {
  selectedFile.value = file
  // Open directories on single click for faster navigation
  if (file.type === 'dir') {
    emit('open', file)
  }
}

const handleFileDblClick = (file) => {
  if (file.type === 'file') {
    emit('open', file)
  }
}

const handleContextMenu = (e, file) => {
  const items = [
    { label: t('workspace.actions.open'), icon: '👁️', action: () => handleFileClick(file) },
    { label: t('workspace.actions.open_new_tab'), icon: '🔗', action: () => openInNewTab(file) },
    { label: t('workspace.actions.download'), icon: '⬇️', action: () => downloadFile(file) }
  ]
  menu.value.open(e, items)
}

const openInNewTab = (file) => {
  window.open(`/view-file?path=${encodeURIComponent(file.path)}`, '_blank')
}

const downloadFile = (file) => {
  const link = document.createElement('a')
  link.href = `/api/workspace/files/read?path=${encodeURIComponent(file.path)}&download=true`
  link.download = file.name
  link.click()
}

const handleDrop = async (e) => {
  isDragActive.value = false
  const droppedFiles = e.dataTransfer.files
  if (droppedFiles.length === 0) return
  
  for (let file of droppedFiles) {
    try {
      await api.workspace.uploadFile(file, props.currentPath)
    } catch (err) {
      uiStore.notify(t('workspace.notifications.upload_failed', { error: err.message }), 'danger')
    }
  }
  uiStore.notify(t('workspace.notifications.upload_complete', { count: droppedFiles.length }), 'success')
  fetchFiles()
}

const handleDragEnter = () => {
  isDragActive.value = true
}

const handleDragLeave = (e) => {
  if (e.currentTarget.contains(e.relatedTarget)) return
  isDragActive.value = false
}

const goBack = () => {
  if (!props.currentPath) return
  const parts = props.currentPath.split('/')
  parts.pop()
  const parentPath = parts.join('/')
  emit('open', { type: 'dir', path: parentPath })
}

onMounted(fetchFiles)
</script>

<template>
  <div class="workspace-content" @dragover.prevent @dragenter.prevent="handleDragEnter" @dragleave.prevent="handleDragLeave" @drop.prevent="handleDrop">
    <div class="ws-header-title">
      <button 
        v-if="currentPath" 
        class="back-btn" 
        @click="goBack"
        title="Go Back"
      >
        <svg viewBox="0 0 24 24"><path d="M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z"/></svg>
      </button>
      <span class="path-label">{{ currentPath || t('workspace.root') }}</span>
    </div>

    <div class="grid-container">
      <div v-if="loading" class="center-state">
        {{ t('workspace.states.scanning') }}
      </div>
      <div v-else-if="files.length === 0" class="center-state">
        <div class="drop-hint">
          <svg viewBox="0 0 24 24"><path d="M14,13V17H10V13H7L12,8L17,13H14M19.35,10.03C18.67,6.59 15.64,4 12,4C9.11,4 6.6,5.64 5.35,8.03C2.34,8.36 0,10.9 0,14A6,6 0 0,0 6,20H19A5,5 0 0,0 24,15C24,12.36 21.95,10.22 19.35,10.03Z"/></svg>
          <p>{{ t('workspace.states.empty') }}</p>
          <span>{{ t('workspace.states.drop_here') }}</span>
        </div>
      </div>
      <div v-else class="file-grid">
        <div 
          v-for="file in files" 
          :key="file.path" 
          class="grid-item"
          :class="{ active: selectedFile?.path === file.path, 'is-dir': file.type === 'dir' }"
          @click.stop="handleFileClick(file)"
          @dblclick.stop="handleFileDblClick(file)"
          @contextmenu.stop="handleContextMenu($event, file)"
        >
          <div class="item-visual" :class="{ is_dir: file.type === 'dir' }">
            <svg v-if="file.type === 'dir'" viewBox="0 0 24 24" class="folder-svg"><path d="M10,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8C22,6.89 21.1,6 20,6H12L10,4Z"/></svg>
            <svg v-else viewBox="0 0 24 24" class="file-svg"><path d="M13,9V3.5L18.5,9M6,2C4.89,2 4,2.89 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2H6Z"/></svg>
          </div>
          <div class="item-label">{{ file.name }}</div>
        </div>
      </div>
    </div>

    <!-- Persistent Drop Zone Hint -->
    <div class="drop-zone-overlay" :class="{ active: isDragActive }">
       <div class="overlay-inner">
         <svg viewBox="0 0 24 24"><path d="M14,13V17H10V13H7L12,8L17,13H14M19.35,10.03C18.67,6.59 15.64,4 12,4C9.11,4 6.6,5.64 5.35,8.03C2.34,8.36 0,10.9 0,14A6,6 0 0,0 6,20H19A5,5 0 0,0 24,15C24,12.36 21.95,10.22 19.35,10.03Z"/></svg>
         <span>{{ t('workspace.states.drop_to_upload', { path: currentPath || t('workspace.root') }) }}</span>
       </div>
    </div>
    <ContextMenu ref="menu" />
  </div>
</template>

<style scoped>
.workspace-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  background: var(--bg-primary);
}

.ws-header-title {
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
}

.path-label {
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  opacity: 0.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.back-btn {
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  transition: 0.2s;
}
.back-btn:hover {
  background: rgba(255,255,255,0.05);
  color: var(--mango-primary);
  border-color: var(--mango-primary);
}
.back-btn svg { width: 16px; fill: currentColor; }

.grid-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 20px;
}

.grid-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 12px;
  border-radius: 12px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 10;
  pointer-events: auto;
  user-select: none;
}
.grid-item:hover {
  background: rgba(255, 255, 255, 0.04);
}
.grid-item.active {
  background: rgba(255, 170, 0, 0.1);
  border: 1px solid rgba(255, 170, 0, 0.3);
}

.item-visual {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.item-visual svg { width: 44px; fill: currentColor; }
.item-visual.is_dir svg { color: var(--mango-primary); }
.item-visual:not(.is_dir) svg { opacity: 0.6; }

.item-label {
  font-size: 12px;
  text-align: center;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.center-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.4;
  font-weight: 700;
  text-transform: uppercase;
  font-size: 11px;
}

.drop-hint { text-align: center; }
.drop-hint svg { width: 48px; fill: currentColor; margin-bottom: 12px; }
.drop-hint p { margin: 0; font-size: 14px; }
.drop-hint span { font-size: 11px; opacity: 0.6; }

.drop-zone-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  z-index: 100;
  display: none;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.drop-zone-overlay.active { display: flex; }

.overlay-inner {
  padding: 40px;
  border: 2px dashed var(--mango-primary);
  border-radius: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: var(--mango-primary);
}
.overlay-inner svg { width: 64px; fill: currentColor; }
</style>
