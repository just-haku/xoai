<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../services/api'
import { useUIStore } from '../stores/ui'

import MonacoEditor from '../components/viewers/MonacoEditor.vue'
import DocxEditor from '../components/viewers/DocxEditor.vue'
import XlsxViewer from '../components/viewers/XlsxViewer.vue'
import ImageViewer from '../components/viewers/ImageViewer.vue'

const route = useRoute()
const router = useRouter()
const uiStore = useUIStore()

const path = computed(() => route.query.path)
const fileName = computed(() => path.value?.split('/').pop() || '')

const loading = ref(true)
const content = ref('')
const excelData = ref({ rows: [], cols: [] })
const viewerType = ref('none')
const imageUrl = ref('')

const getViewerType = (name) => {
  const ext = name.split('.').pop().toLowerCase()
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return 'image'
  if (ext === 'docx') return 'docx'
  if (ext === 'xlsx') return 'xlsx'
  if (['js', 'ts', 'py', 'json', 'html', 'css', 'md', 'vue', 'sh', 'sql', 'c', 'cpp', 'txt'].includes(ext)) return 'code'
  return 'unknown'
}

const loadFile = async () => {
  if (!path.value) return
  if (!localStorage.getItem('xoai_token')) {
    router.replace({ name: 'landing' })
    return
  }
  loading.value = true
  viewerType.value = getViewerType(fileName.value)
  
  try {
    if (viewerType.value === 'code') {
      const data = await api.request(`/workspace/files/read?path=${encodeURIComponent(path.value)}`)
      content.value = data.content
    } else if (viewerType.value === 'docx') {
      const data = await api.request(`/workspace/files/convert/docx?path=${encodeURIComponent(path.value)}`)
      content.value = data.content
    } else if (viewerType.value === 'xlsx') {
      const data = await api.request(`/workspace/files/convert/xlsx?path=${encodeURIComponent(path.value)}`)
      excelData.value = {
        rows: data.content,
        cols: Object.keys(data.content[0] || {}).map(k => ({ field: k, headerName: k }))
      }
    } else if (viewerType.value === 'image') {
       const blob = await api.requestBlob(`/workspace/files/read?path=${encodeURIComponent(path.value)}&download=true`)
       imageUrl.value = URL.createObjectURL(blob)
    }
  } catch (err) {
    uiStore.notify('Error loading file: ' + err.message, 'danger')
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
        body: JSON.stringify({ path: path.value, ...payload })
      })
      uiStore.notify('File saved successfully!', 'success')
    }
  } catch (err) {
    uiStore.notify('Failed to save: ' + err.message, 'danger')
  }
}

onMounted(() => {
  loadFile()
})
</script>

<template>
  <div class="file-viewer-page">
    <header class="viewer-nav glass-panel">
      <div class="nav-left">
        <button class="back-link" @click="router.back()">
          <svg viewBox="0 0 24 24"><path d="M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z"/></svg>
        </button>
        <span class="file-name">{{ fileName }}</span>
        <div class="type-tag" v-if="viewerType !== 'none'">{{ viewerType }}</div>
      </div>
      
      <div class="nav-right">
        <button class="save-btn" @click="saveFile" v-if="['code', 'docx', 'xlsx'].includes(viewerType)">
          <svg viewBox="0 0 24 24"><path d="M15,9H5V5H15M12,19A3,3 0 0,1 9,16A3,3 0 0,1 12,13A3,3 0 0,1 15,16A3,3 0 0,1 12,19M17,3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V7L17,3Z"/></svg>
          <span>Save Changes</span>
        </button>
      </div>
    </header>

    <main class="viewer-body">
      <div v-if="loading" class="page-loader">
        <div class="loader-ring"></div>
        <span>Initializing full-page context...</span>
      </div>

      <template v-else>
        <MonacoEditor v-if="viewerType === 'code'" v-model="content" @save="saveFile" />
        <DocxEditor v-else-if="viewerType === 'docx'" v-model="content" @save="saveFile" />
        <XlsxViewer v-else-if="viewerType === 'xlsx'" :rowData="excelData.rows" :columnDefs="excelData.cols" @save="saveFile" />
        <ImageViewer v-else-if="viewerType === 'image'" :src="imageUrl" :fileName="fileName" />
        <div v-else class="not-supported">
           <svg viewBox="0 0 24 24"><path d="M13,9V3.5L18.5,9M6,2C4.89,2 4,2.89 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2H6Z"/></svg>
           <h2>Unsupported File Format</h2>
           <p>This file type cannot be previewed directly. Please use another tool to view <b>{{ fileName }}</b>.</p>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.file-viewer-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.viewer-nav {
  height: 64px; border-bottom: 1px solid var(--border-subtle);
  display: flex; align-items: center; justify-content: space-between; padding: 0 32px;
  background: var(--bg-secondary); z-index: 1000;
}

.nav-left { display: flex; align-items: center; gap: 20px; }
.back-link { 
  background: transparent; border: none; color: var(--text-secondary); 
  cursor: pointer; padding: 8px; border-radius: 50%; transition: all 0.2s;
}
.back-link:hover { background: rgba(255,255,255,0.05); color: var(--mango-primary); }
.back-link svg { width: 22px; fill: currentColor; }

.file-name { font-size: 18px; font-weight: 800; letter-spacing: -0.5px; }
.type-tag {
  background: var(--mango-primary); color: white; padding: 4px 12px;
  border-radius: 6px; font-size: 10px; font-weight: 900; text-transform: uppercase;
}

.save-btn {
  background: var(--mango-primary); color: white; border: none;
  padding: 10px 24px; border-radius: 12px; font-weight: 800;
  display: flex; align-items: center; gap: 10px; cursor: pointer; transition: 0.2s;
  box-shadow: 0 10px 20px var(--mango-glow);
}
.save-btn:hover { transform: translateY(-2px); box-shadow: 0 15px 30px var(--mango-glow); }
.save-btn svg { width: 18px; fill: currentColor; }

.viewer-body { flex: 1; overflow: hidden; position: relative; }

.page-loader {
  height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px;
}
.loader-ring {
  width: 48px; height: 48px; border: 4px solid var(--border-subtle);
  border-top-color: var(--mango-primary); border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.not-supported {
  height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
}
.not-supported svg { width: 80px; opacity: 0.1; fill: currentColor; margin-bottom: 24px; }
.not-supported h2 { margin-bottom: 8px; font-weight: 800; }
.not-supported p { opacity: 0.5; max-width: 400px; }
</style>
