<template>
  <div v-if="show" class="context-menu glass-panel" :style="{ top: y + 'px', left: x + 'px' }">
    <div v-for="item in items" :key="item.label" 
         class="menu-item" :class="item.class"
         @click="handleClick(item)">
      <span class="icon">{{ item.icon }}</span>
      <span class="label">{{ item.label }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const show = ref(false)
const x = ref(0)
const y = ref(0)
const items = ref([])

const open = (e, menuItems) => {
  e.preventDefault()
  items.value = menuItems
  x.value = e.clientX
  y.value = e.clientY
  show.value = true
}

const close = () => {
  show.value = false
}

const handleClick = (item) => {
  if (item.action) item.action()
  close()
}

onMounted(() => {
  window.addEventListener('click', close)
})

onUnmounted(() => {
  window.removeEventListener('click', close)
})

defineExpose({ open, close })
</script>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 10000;
  min-width: 160px;
  padding: 4px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--mango-primary);
}

.menu-item.danger:hover {
  background: rgba(255, 0, 0, 0.1);
  color: #ff4d4d;
}

.icon { font-size: 16px; opacity: 0.8; }
</style>
