<template>
  <div class="file-viewer glass-panel">
    <div class="viewer-header">
      <div class="file-info">
        <span class="icon">{{ getFileIcon(file.type) }}</span>
        <span class="name">{{ file.name }}</span>
      </div>
      <div class="actions">
        <button @click="$emit('download')" title="Download">⬇️</button>
        <button @click="$emit('close')" title="Close">✖️</button>
      </div>
    </div>

    <div class="viewer-body scrollable">
      <!-- Image Viewer -->
      <img v-if="isImage" :src="fileUrl" class="media-preview" />

      <!-- Video Viewer with Custom Controls -->
      <div v-else-if="isVideo" class="video-container">
        <video ref="videoPlayer" :src="fileUrl" @timeupdate="updateProgress"></video>
        <div class="video-controls">
          <div class="progress-track" @click="seek">
            <div class="fill" :style="{width: videoProgress + '%'}"></div>
          </div>
          <div class="btns">
            <button @click="skip(-5)" title="Rewind 5s">⏪</button>
            <button @click="togglePlay">{{ isPlaying ? '⏸️' : '▶️' }}</button>
            <button @click="skip(5)" title="Forward 5s">⏩</button>
            <span class="time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
          </div>
        </div>
      </div>

      <!-- Text/Code Viewer -->
      <pre v-else-if="isText" class="code-preview"><code>{{ fileContent }}</code></pre>

      <!-- Fallback -->
      <div v-else class="fallback-preview">
        <p>Preview not available for this file type.</p>
        <button class="mango-button" @click="$emit('download')">Download to View</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps(['file', 'fileUrl', 'fileContent'])
const emit = defineEmits(['close', 'download'])

const videoPlayer = ref(null)
const isPlaying = ref(false)
const videoProgress = ref(0)
const currentTime = ref(0)
const duration = ref(0)

const isImage = computed(() => props.file.type.startsWith('image/'))
const isVideo = computed(() => props.file.type.startsWith('video/'))
const isText = computed(() => props.file.type.startsWith('text/') || props.file.name.endsWith('.md') || props.file.name.endsWith('.js'))

const getFileIcon = (type) => {
  if (type.startsWith('image/')) return '🖼️'
  if (type.startsWith('video/')) return '🎥'
  if (type.startsWith('audio/')) return '🎵'
  return '📄'
}

const togglePlay = () => {
  if (videoPlayer.value.paused) {
    videoPlayer.value.play()
    isPlaying.value = true
  } else {
    videoPlayer.value.pause()
    isPlaying.value = false
  }
}

const skip = (seconds) => {
  videoPlayer.value.currentTime += seconds
}

const updateProgress = () => {
  currentTime.value = videoPlayer.value.currentTime
  duration.value = videoPlayer.value.duration
  videoProgress.value = (currentTime.value / duration.value) * 100
}

const seek = (e) => {
  const rect = e.target.getBoundingClientRect()
  const pos = (e.clientX - rect.left) / rect.width
  videoPlayer.value.currentTime = pos * duration.value
}

const formatTime = (s) => {
  const min = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${min}:${sec < 10 ? '0' : ''}${sec}`
}
</script>

<style scoped>
.file-viewer {
  display: flex; flex-direction: column; height: 100%; width: 100%;
  overflow: hidden; border-radius: 12px;
}

.viewer-header {
  padding: 12px 16px; display: flex; justify-content: space-between;
  align-items: center; background: rgba(255,255,255,0.05);
  border-bottom: 1px solid var(--border-subtle);
}

.file-info { display: flex; gap: 12px; align-items: center; font-size: 14px; }
.actions button { background: none; border: none; cursor: pointer; padding: 4px; }

.viewer-body { flex: 1; display: flex; align-items: center; justify-content: center; background: #000; }

.media-preview { max-width: 100%; max-height: 100%; object-fit: contain; }

.video-container { position: relative; width: 100%; height: 100%; display: flex; flex-direction: column; }
video { flex: 1; max-height: calc(100% - 60px); }

.video-controls {
  padding: 12px; background: rgba(0,0,0,0.8); display: flex; flex-direction: column; gap: 8px;
}

.progress-track { height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; cursor: pointer; }
.progress-track .fill { height: 100%; background: var(--mango-primary); border-radius: 2px; }

.btns { display: flex; align-items: center; gap: 16px; }
.btns button { background: none; border: none; color: white; cursor: pointer; font-size: 18px; }
.time { font-size: 12px; opacity: 0.6; margin-left: auto; }

.code-preview {
  width: 100%; padding: 20px; color: #dcdcdc; font-family: monospace;
  font-size: 13px; line-height: 1.5; text-align: left;
}

.fallback-preview { display: flex; flex-direction: column; gap: 16px; align-items: center; }
</style>
