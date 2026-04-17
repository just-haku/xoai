<script setup>
import { ref, computed } from 'vue'
import { api } from '../services/api'

const props = defineProps({
  item: {
    type: Object,
    required: true
  },
  depth: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['select'])

const isExpanded = ref(false)
const children = ref([])
const loading = ref(false)

const toggle = async () => {
  if (props.item.type !== 'dir') {
    emit('select', props.item.path)
    return
  }

  isExpanded.value = !isExpanded.value
  
  // Always notify parent of selection when clicking the folder itself
  emit('select', props.item.path)

  if (isExpanded.value && children.value.length === 0) {
    loading.value = true
    try {
      const data = await api.request('/workspace/files?path=' + encodeURIComponent(props.item.path))
      children.value = data.map(f => ({
        name: f.name,
        type: f.is_dir ? 'dir' : 'file',
        path: props.item.path ? (props.item.path + '/' + f.name) : f.name
      }))
    } catch (err) {
      console.error('Failed to fetch children:', err)
    } finally {
      loading.value = false
    }
  }
}

const handleSelect = (path) => {
  emit('select', path)
}
</script>

<template>
  <div class="tree-item-wrapper">
    <div 
      class="tree-item" 
      :style="{ paddingLeft: (depth * 12 + 8) + 'px' }"
      @click="toggle"
    >
      <span v-if="item.type === 'dir'" class="toggle-icon">
        <!-- User Request: 'v' to expand, '>' if expanded -->
        <template v-if="!isExpanded">
          <svg viewBox="0 0 24 24"><path d="M7,10L12,15L17,10H7Z"/></svg>
        </template>
        <template v-else>
          <svg viewBox="0 0 24 24"><path d="M8.59,16.59L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.59Z"/></svg>
        </template>
      </span>
      <span v-else class="file-spacer"></span>
      
      <span class="item-icon">
        <svg v-if="item.type === 'dir'" viewBox="0 0 24 24" class="mango"><path d="M10,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8C22,6.89 21.1,6 20,6H12L10,4Z"/></svg>
        <svg v-else viewBox="0 0 24 24"><path d="M13,9V3.5L18.5,9M6,2C4.89,2 4,2.89 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2H6Z"/></svg>
      </span>
      
      <span class="item-name">{{ item.name }}</span>
    </div>

    <div v-if="isExpanded" class="tree-children">
      <div v-if="loading" class="loading-state" :style="{ paddingLeft: (depth * 12 + 24) + 'px' }">
        Loading...
      </div>
      <FileTreeItem 
        v-for="child in children" 
        :key="child.path" 
        :item="child" 
        :depth="depth + 1"
        @select="handleSelect"
      />
    </div>
  </div>
</template>

<style scoped>
.tree-item {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
  gap: 6px;
  transition: background 0.2s;
  white-space: nowrap;
}
.tree-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.toggle-icon {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.6;
}
.toggle-icon svg { width: 14px; fill: currentColor; }

.file-spacer {
  width: 16px;
}

.item-icon {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.item-icon svg { width: 14px; fill: currentColor; opacity: 0.7; }
.item-icon svg.mango { color: var(--mango-primary); opacity: 1; }

.item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}

.loading-state {
  font-size: 11px;
  opacity: 0.4;
  padding: 4px 0;
}
</style>
