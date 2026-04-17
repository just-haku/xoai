<script setup>
import { ref, watch, onMounted, computed, onUnmounted } from 'vue'
import { api } from '../services/api'
import { useUIStore } from '../stores/ui'

import MonacoEditor from './viewers/MonacoEditor.vue'
import DocxEditor from './viewers/DocxEditor.vue'
import XlsxViewer from './viewers/XlsxViewer.vue'
import ImageViewer from './viewers/ImageViewer.vue'

const props = defineProps({
  show: Boolean,
  file: Object
})

const emit = defineEmits(['close'])
const uiStore = useUIStore()

const loading = ref(true)
const content = ref('')
const excelData = ref({ rows: [], cols: [] })
const viewerType = ref('none')

const getViewerType = (name) => {
  const ext = name.split('.').pop().toLowerCase()
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return 'image'
  if (ext === 'docx') return 'docx'
  if (ext === 'xlsx') return 'xlsx'
  if (['js', 'ts', 'py', 'json', 'html', 'css', 'md', 'vue', 'sh', 'sql', 'c', 'cpp', 'txt'].includes(ext)) return 'code'
  return 'unknown'
}

const getLanguage = (name) => {
  const ext = name.split('.').pop().toLowerCase()
  const map = {
    js: 'javascript', ts: 'typescript', py: 'python', 
    html: 'html', css: 'css', json: 'json',
    md: 'markdown', sh: 'shell', sql: 'sql',
    vue: 'html', c: 'c', cpp: 'cpp', txt: 'text'
  }
  return map[ext] || 'text'
}

const viewerLanguage = ref('text')

const loadFile = async () => {
  if (!props.file) return
  loading.value = true
  viewerType.value = getViewerType(props.file.name)
  viewerLanguage.value = getLanguage(props.file.name)
  
  try {
    if (viewerType.value === 'code') {
      const data = await api.request(`/workspace/files/read?path=${encodeURIComponent(props.file.path)}`)
      content.value = data.content
    } else if (viewerType.value === 'docx') {
      const data = await api.request(`/workspace/files/convert/docx?path=${encodeURIComponent(props.file.path)}`)
      content.value = data.content
    } else if (viewerType.value === 'xlsx') {
      const data = await api.request(`/workspace/files/convert/xlsx?path=${encodeURIComponent(props.file.path)}`)
      excelData.value = {
        rows: data.content,
        cols: Object.keys(data.content[0] || {}).map(k => ({ field: k, headerName: k }))
      }
    } else if (viewerType.value === 'image') {
       // Images can use the read endpoint direct URL or base64
       // Assuming backend has a direct serving endpoint or we use read?as_base64=true
       const data = await api.request(`/workspace/files/read?path=${encodeURIComponent(props.file.path)}&base64=true`)
       content.value = `data:image/png;base64,${data.content}`
    }
  } catch (err) {
    uiStore.notify('Error loading preview: ' + err.message, 'danger')
  } finally {
    loading.value = false
  }
}

const saveFile = async () => {
  try {
    let endpoint = ''
    let payload = { content: content.value }
    
    if (viewerType.value === 'docx') endpoint = '/workspace/files/save/docx'
    else if (viewerType.value === 'code') endpoint = '/workspace/files/save' 
    else if (viewerType.value === 'xlsx') {
       endpoint = '/workspace/files/save/xlsx'
       payload = { content: excelData.value.rows }
    }

    if (endpoint) {
      await api.request(endpoint, {
        method: 'POST',
        body: JSON.stringify({ path: props.file.path, ...payload })
      })
      uiStore.notify('File saved successfully!', 'success')
    }
  } catch (err) {
    uiStore.notify('Failed to save file: ' + err.message, 'danger')
  }
}

const openInNewTab = () => {
  window.open(`/view-file?path=${encodeURIComponent(props.file.path)}`, '_blank')
}

watch(() => props.file, loadFile, { immediate: true })

const close = () => emit('close')
const handleEsc = (e) => { if (e.key === 'Escape') close() }

onMounted(() => window.addEventListener('keydown', handleEsc))
onUnmounted(() => window.removeEventListener('keydown', handleEsc))
</script>

<template>
  <Transition name="fade">
    <div v-if="show" class="preview-overlay" @click.self="close">
      <div class="preview-card glass-panel shadow-premium">
        <div class="preview-header">
          <div class="header-left">
            <span class="file-info">{{ file?.name }}</span>
            <div class="header-badge" v-if="viewerType !== 'none'">{{ viewerType }}</div>
          </div>
          <div class="header-actions">
            <button class="action-btn" @click="saveFile" v-if="['code', 'docx', 'xlsx'].includes(viewerType)">
              <svg viewBox="0 0 24 24"><path d="M15,9H5V5H15M12,19A3,3 0 0,1 9,16A3,3 0 0,1 12,13A3,3 0 0,1 15,16A3,3 0 0,1 12,19M17,3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V7L17,3Z"/></svg>
              <span>Save</span>
            </button>
            <button class="action-btn" @click="openInNewTab">
              <svg viewBox="0 0 24 24"><path d="M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z"/></svg>
              <span>Extern</span>
            </button>
            <button class="exit-btn" @click="close">
              <svg viewBox="0 0 24 24"><path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/></svg>
            </button>
          </div>
        </div>
        
        <div class="preview-body">
          <div v-if="loading" class="preview-loading">
             <div class="loader"></div>
             <span>Fetching context...</span>
          </div>
          
          <template v-else>
            <MonacoEditor 
              v-if="viewerType === 'code'" 
              v-model="content" 
              :language="viewerLanguage"
              @save="saveFile" 
            />
            <DocxEditor v-else-if="viewerType === 'docx'" v-model="content" @save="saveFile" />
            <XlsxViewer v-else-if="viewerType === 'xlsx'" :rowData="excelData.rows" :columnDefs="excelData.cols" @save="saveFile" />
            <ImageViewer v-else-if="viewerType === 'image'" :src="content" :fileName="file.name" />
            <div v-else class="unknown-preview">
              <svg viewBox="0 0 24 24"><path d="M13,9V3.5L18.5,9M6,2C4.89,2 4,2.89 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2H6Z"/></svg>
              <p>{{ $t('workspace.preview.not_available') }}</p>
              <button class="download-fallback" @click="openInNewTab">Download to Edit</button>
            </div>
          </template>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.preview-overlay {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 9999;
  background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(20px);
  display: flex; align-items: center; justify-content: center; padding: 40px;
}

.preview-card {
  width: 100%; max-width: 1400px; height: 90vh;
  display: flex; flex-direction: column; overflow: hidden;
  background: var(--bg-secondary); border: 1px solid var(--border-strong);
  border-radius: 24px; box-shadow: 0 50px 100px rgba(0,0,0,0.6);
}

.preview-header {
  padding: 16px 24px; display: flex; justify-content: space-between; align-items: center;
  background: var(--bg-tertiary); border-bottom: 1px solid var(--border-subtle);
}

.header-left { display: flex; align-items: center; gap: 12px; }
.file-info { font-weight: 800; font-size: 15px; letter-spacing: -0.2px; }
.header-badge {
  padding: 4px 10px; border-radius: 6px; background: var(--mango-primary);
  color: white; font-size: 10px; font-weight: 900; text-transform: uppercase;
}

.header-actions { display: flex; align-items: center; gap: 10px; }
.action-btn, .exit-btn {
  background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border-subtle);
  color: var(--text-primary); padding: 8px 16px; border-radius: 10px;
  display: flex; align-items: center; gap: 8px; cursor: pointer;
  transition: all 0.2s; font-size: 13px; font-weight: 700;
}
.exit-btn { padding: 8px; border-radius: 10px; }
.action-btn:hover { background: var(--bg-glass); border-color: var(--mango-primary); color: var(--mango-primary); }
.exit-btn:hover { color: var(--danger); background: rgba(255,0,0,0.05); }

.action-btn svg, .exit-btn svg { width: 18px; fill: currentColor; }

.preview-body { flex: 1; overflow: hidden; position: relative; }

.preview-loading {
  height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px;
  background: var(--bg-primary); opacity: 0.8;
}

.loader {
  width: 40px; height: 40px; border: 4px solid var(--border-subtle);
  border-top-color: var(--mango-primary); border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.unknown-preview {
  height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px;
  color: var(--text-secondary);
}
.unknown-preview svg { width: 64px; opacity: 0.2; fill: currentColor; }
.download-fallback {
  margin-top: 16px; padding: 10px 24px; border-radius: 12px;
  background: var(--mango-primary); color: white; border: none; font-weight: 800; cursor: pointer;
}

.fade-enter-active, .fade-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: scale(0.95); }
</style>
