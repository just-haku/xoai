<template>
  <div class="model-selector-container">
    <div class="selector-trigger" @click="isOpen = !isOpen">
      <span class="provider-icon">{{ getIcon(selectedModel) }}</span>
      <span class="model-name">{{ selectedModel }}</span>
      <span class="chevron" :class="{ open: isOpen }">▼</span>
    </div>
    
    <div v-if="isOpen" class="dropdown-menu glass-panel">
      <div v-for="group in modelGroups" :key="group.provider" class="model-group">
        <label>{{ group.provider }}</label>
        <div v-for="model in group.models" :key="model" 
             class="model-option" 
             @click="selectModel(model)">
          {{ model }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const selectedModel = ref('gemini-1.5-pro')
const isOpen = ref(false)

const modelGroups = ref([
  { provider: 'Google', models: ['gemini-1.5-pro', 'gemini-1.5-flash'] },
  { provider: 'OpenAI', models: ['gpt-4o', 'gpt-4-turbo'] }
])

const selectModel = (model) => {
  selectedModel.value = model
  isOpen.value = false
}

const getIcon = (model) => {
  if (model.includes('gemini')) return '✨'
  if (model.includes('gpt')) return '🤖'
  return '🧠'
}
</script>

<style scoped>
.model-selector-container {
  position: relative;
  min-width: 180px;
}

.selector-trigger {
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  transition: var(--transition-fast);
}

.selector-trigger:hover {
  background: rgba(255, 255, 255, 0.1);
}

.dropdown-menu {
  position: fixed;
  top: 80px; /* Aligned with header height */
  right: 20px;
  width: 200px;
  z-index: 9999;
  padding: 8px;
  max-height: 400px;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
}

.model-group label {
  display: block;
  font-size: 10px;
  text-transform: uppercase;
  color: var(--mango-primary);
  margin: 12px 8px 4px;
  font-weight: 800;
}

.model-option {
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}

.model-option:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--mango-primary);
}

.chevron {
  margin-left: auto;
  font-size: 10px;
  transition: transform 0.3s;
}

.chevron.open {
  transform: rotate(180deg);
}
</style>
