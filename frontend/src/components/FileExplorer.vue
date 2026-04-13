<template>
  <div class="file-explorer glass-panel" @contextmenu="handleGlobalContextMenu">
    <div class="explorer-header">
      <h4>Workspace</h4>
      <div class="actions">
        <button class="icon-btn" title="Refresh">
          <svg viewBox="0 0 24 24" class="svg-icon-small"><path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"/></svg>
        </button>
      </div>
    </div>
    <div class="file-list">
      <div v-for="file in files" :key="file.name" 
           class="file-item" :class="file.type"
           @contextmenu.stop="handleContextMenu($event, file)">
        <svg v-if="file.type === 'dir'" viewBox="0 0 24 24" class="item-icon-svg mango"><path d="M10,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8C22,6.89 21.1,6 20,6H12L10,4Z"/></svg>
        <svg v-else viewBox="0 0 24 24" class="item-icon-svg"><path d="M13,9V3.5L18.5,9M6,2C4.89,2 4,2.89 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2H6Z"/></svg>
        <span class="name">{{ file.name }}</span>
      </div>
      <div v-if="files.length === 0" class="empty-state">
        No files in workspace
      </div>
    </div>
    <ContextMenu ref="menu" />
    <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop">
      Drop files to upload
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../services/api'
import ContextMenu from './ContextMenu.vue'

const files = ref([
  { name: 'src', type: 'dir' },
  { name: 'main.py', type: 'file' },
  { name: 'requirements.txt', type: 'file' }
])

const menu = ref(null)

const handleGlobalContextMenu = (e) => {
  menu.value.open(e, [
    { label: 'Upload File', icon: '📤', action: () => console.log('Upload File') },
    { label: 'Upload Folder', icon: '📁', action: () => console.log('Upload Folder') },
    { label: 'New Folder', icon: '➕', action: () => console.log('New Folder') }
  ])
}

const handleContextMenu = (e, file) => {
  menu.value.open(e, [
    { label: 'Open', icon: '👁️', action: () => console.log('Open', file.name) },
    { label: 'Download', icon: '⬇️', action: () => console.log('Download', file.name) },
    { label: 'Share', icon: '🔗', action: () => console.log('Share', file.name) },
    { label: 'Rename', icon: '✏️', action: () => console.log('Rename', file.name) },
    { label: 'Trash', icon: '🗑️', class: 'danger', action: () => console.log('Trash', file.name) }
  ])
}

const handleDrop = async (e) => {
  const droppedFiles = e.dataTransfer.files
  for (let file of droppedFiles) {
    try {
      await api.workspace.uploadFile(file)
    } catch (err) {
      console.error(err)
    }
  }
}

onMounted(() => {
  // refresh list
})
</script>

<style scoped>
.file-explorer {
  width: 240px;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--border-subtle);
  border-radius: 0;
  height: 100%;
}

.explorer-header {
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
}

.explorer-header h4 { font-size: 13px; font-weight: 700; opacity: 0.8; margin: 0; }

.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.file-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--mango-primary);
}

.item-icon-svg { width: 18px; fill: currentColor; opacity: 0.7; }
.item-icon-svg.mango { color: var(--mango-primary); opacity: 0.9; }

.drop-zone {
  padding: 16px;
  border-top: 1px dashed var(--border-subtle);
  text-align: center;
  font-size: 11px;
  color: var(--text-secondary);
  background: rgba(255, 122, 0, 0.03);
}

.empty-state {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 12px;
}

.svg-icon-small { width: 14px; fill: currentColor; }
.icon-btn { background: transparent; border: none; cursor: pointer; color: var(--text-secondary); }
.icon-btn:hover { color: var(--mango-primary); }
</style>
