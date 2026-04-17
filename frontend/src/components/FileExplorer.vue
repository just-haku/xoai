<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../services/api'
import FileTreeItem from './FileTreeItem.vue'

const rootFiles = ref([])
const loading = ref(true)

const emit = defineEmits(['select'])

const fetchRoot = async () => {
  loading.value = true
  try {
    const data = await api.request('/workspace/files?path=')
    rootFiles.value = data.map(f => ({
      name: f.name,
      type: f.is_dir ? 'dir' : 'file',
      path: f.name
    }))
  } catch (err) {
    console.error('Failed to fetch root files:', err)
  } finally {
    loading.value = false
  }
}

const handleSelect = (path) => {
  emit('select', path)
}

onMounted(() => {
  fetchRoot()
})
</script>

<template>
  <div class="file-explorer-tree">
    <div class="explorer-inner">
      <div v-if="loading" class="loading-root">
        Initializing Workspace...
      </div>
      <FileTreeItem 
        v-for="file in rootFiles" 
        :key="file.path" 
        :item="file" 
        @select="handleSelect"
      />
      <div v-if="!loading && rootFiles.length === 0" class="empty-root">
        No files found
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-explorer-tree {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-tertiary);
  overflow-x: hidden;
  overflow-y: auto;
}

.explorer-inner {
  padding: 12px 8px;
}

.loading-root, .empty-root {
  padding: 20px;
  font-size: 11px;
  text-align: center;
  opacity: 0.5;
  font-weight: 700;
  text-transform: uppercase;
}
</style>
