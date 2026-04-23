<template>
  <div v-if="isOpen" class="crop-overlay" @click.self="close">
    <div class="crop-modal glass-panel shadow-premium">
      <div class="crop-header">
        <h3>Crop Avatar</h3>
        <p>Adjust the selection to fit the circle.</p>
      </div>

      <div class="crop-area" ref="cropBox" @mousedown="startDrag" @touchstart="startDrag">
        <img :src="imageSrc" class="source-img" :style="imgStyle" ref="sourceImg" />
        <div class="crop-mask"></div>
        <div class="crop-circle"></div>
      </div>

      <div class="crop-controls">
        <div class="zoom-slider">
          <button class="btn-micro" @click="zoom = Math.max(1, zoom - 0.1)">-</button>
          <input type="range" v-model="zoom" min="1" max="3" step="0.01" />
          <button class="btn-micro" @click="zoom = Math.min(3, zoom + 0.1)">+</button>
        </div>
        <div class="actions-row">
          <button class="cancel-btn" @click="close">Cancel</button>
          <button class="mango-button" @click="confirm">Apply Crop</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps(['isOpen', 'imageSrc'])
const emit = defineEmits(['close', 'confirm'])

const zoom = ref(1)
const offset = ref({ x: 0, y: 0 })
let isDragging = false
let startCoords = { x: 0, y: 0 }

const imgStyle = computed(() => ({
  transform: `translate(${offset.value.x}px, ${offset.value.y}px) scale(${zoom.value})`,
}))

const startDrag = (e) => {
  isDragging = true
  const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX
  const clientY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY
  startCoords = { x: clientX - offset.value.x, y: clientY - offset.value.y }
  
  const moveEvent = e.type.includes('touch') ? 'touchmove' : 'mousemove'
  const endEvent = e.type.includes('touch') ? 'touchend' : 'mouseup'
  
  const onMove = (ev) => {
    if (!isDragging) return
    const cX = ev.type.includes('touch') ? ev.touches[0].clientX : ev.clientX
    const cY = ev.type.includes('touch') ? ev.touches[0].clientY : ev.clientY
    
    // Calculate new offset
    let nextX = cX - startCoords.x
    let nextY = cY - startCoords.y

    // Simple bounds check: keep center within the box
    const limit = 200 * zoom.value
    nextX = Math.max(-limit, Math.min(limit, nextX))
    nextY = Math.max(-limit, Math.min(limit, nextY))

    offset.value = { x: nextX, y: nextY }
  }
  
  const onEnd = () => {
    isDragging = false
    document.removeEventListener(moveEvent, onMove)
    document.removeEventListener(endEvent, onEnd)
  }
  
  document.addEventListener(moveEvent, onMove)
  document.addEventListener(endEvent, onEnd)
}

const close = () => emit('close')
const confirm = () => {
  // In a real app, generate base64 from current state
  emit('confirm', { zoom: zoom.value, offset: offset.value })
  close()
}
</script>

<style scoped>
.crop-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8); backdrop-filter: blur(10px);
  z-index: 10001; display: flex; align-items: center; justify-content: center;
}

.crop-modal {
  width: 100%; max-width: 440px; padding: 24px;
  display: flex; flex-direction: column; gap: 20px;
}

.crop-header h3 { margin: 0; font-size: 1.25rem; }
.crop-header p { margin: 4px 0 0; font-size: 0.9rem; opacity: 0.6; }

.crop-area {
  position: relative; width: 100%; aspect-ratio: 1;
  background: #000; border-radius: 12px; overflow: hidden;
  cursor: grab;
  user-select: none;
  touch-action: none;
}
.crop-area:active { cursor: grabbing; }

.source-img {
  position: absolute; top: 50%; left: 50%;
  max-width: none; width: 100%; transition: none;
  transform-origin: center;
  pointer-events: none;
  user-select: none;
  -webkit-user-drag: none;
}

.crop-mask {
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.5);
  pointer-events: none;
}

.crop-circle {
  position: absolute; top: 50%; left: 50%;
  width: 70%; height: 70%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 2px solid var(--mango-primary);
  box-shadow: 0 0 0 1000px rgba(0,0,0,0.5); /* Reinforce mask */
}

.crop-controls { display: flex; flex-direction: column; gap: 20px; }

.zoom-slider {
  display: flex; align-items: center; gap: 12px;
}
.zoom-slider input { flex: 1; accent-color: var(--mango-primary); }

.actions-row { display: flex; justify-content: flex-end; gap: 12px; }
.cancel-btn { background: transparent; border: none; color: white; opacity: 0.6; cursor: pointer; }
</style>
