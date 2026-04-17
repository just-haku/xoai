<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  src: String,
  fileName: String
})

const zoom = ref(1)

const zoomIn = () => { zoom.value += 0.1 }
const zoomOut = () => { zoom.value = Math.max(0.1, zoom.value - 0.1) }
const resetZoom = () => { zoom.value = 1 }

const download = () => {
  const link = document.createElement('a')
  link.href = props.src
  link.download = props.fileName
  link.click()
}
</script>

<template>
  <div class="image-viewer">
    <div class="toolbar glass-panel">
      <button @click="zoomIn" title="Zoom In">+</button>
      <button @click="zoomOut" title="Zoom Out">-</button>
      <button @click="resetZoom" title="Reset Zoom">1:1</button>
      <span class="divider"></span>
      <button @click="download" title="Download">
        <svg viewBox="0 0 24 24"><path d="M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z"/></svg>
      </button>
    </div>
    <div class="viewport scrollable">
      <div class="image-container" :style="{ transform: `scale(${zoom})` }">
        <img :src="src" :alt="fileName" @dblclick="resetZoom" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.image-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #09090b;
  position: relative;
}

.toolbar {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  z-index: 10;
  border-radius: 12px;
  background: rgba(0,0,0,0.4);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
}

.toolbar button {
  background: transparent;
  border: none;
  color: white;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}
.toolbar button:hover { background: rgba(255, 255, 255, 0.1); }
.toolbar svg { width: 16px; fill: currentColor; }

.divider { width: 1px; height: 16px; background: rgba(255,255,255,0.1); margin: 0 4px; }

.viewport {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: 40px;
}

.image-container {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
}

img {
  max-width: none;
  display: block;
  box-shadow: 0 20px 50px rgba(0,0,0,0.5);
  background: #111;
  background-image: 
    linear-gradient(45deg, #18181b 25%, transparent 25%), 
    linear-gradient(-45deg, #18181b 25%, transparent 25%), 
    linear-gradient(45deg, transparent 75%, #18181b 75%), 
    linear-gradient(-45deg, transparent 75%, #18181b 75%);
  background-size: 20px 20px;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
}
</style>
