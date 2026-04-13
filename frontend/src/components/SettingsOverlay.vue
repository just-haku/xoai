<script setup>
import { ref, watch } from 'vue'
import { useUIStore } from '../stores/ui'

const props = defineProps(['show'])
const emit = defineEmits(['close'])

const uiStore = useUIStore()
const activeTab = ref('profile')

// User Settings
const profile = ref({
  name: 'Admin User',
  bio: 'XOAI System Administrator',
  avatar: null
})

const apiKeys = ref({
  openai: '',
  google: '',
  selectedModel: 'gemini-1.5-pro'
})

// Server Settings (Admin)
const serverKeys = ref({
  agent0: '',
  agent1: '',
  agent2: ''
})

const themes = [
  { name: 'settings.interface.theme.dark', id: 'dark' },
  { name: 'settings.interface.theme.light', id: 'light' }
]

const colors = [
  { name: 'settings.interface.color.xoai', id: 'xoai' },
  { name: 'settings.interface.color.blue', id: 'blue' },
  { name: 'settings.interface.color.green', id: 'green' },
  { name: 'settings.interface.color.yellow', id: 'yellow' },
  { name: 'settings.interface.color.contrast', id: 'contrast' }
]

const close = () => emit('close')
</script>

<template>
  <div v-if="show" class="overlay-backdrop" @click.self="close">
    <div class="settings-panel glass-panel">
      <div class="panel-sidebar">
        <button v-for="tab in ['profile', 'interface', 'intelligence', 'server']" 
                :key="tab"
                class="tab-btn" :class="{active: activeTab === tab}"
                @click="activeTab = tab">
          {{ $t(`settings.${tab}.title`) }}
        </button>
        <div class="spacer"></div>
        <button class="close-panel-btn" @click="close">{{ $t('actions.cancel') }}</button>
      </div>

      <div class="panel-content">
        <!-- Profile Tab -->
        <div v-if="activeTab === 'profile'" class="tab-view">
          <h2>{{ $t('settings.profile.title') }}</h2>
          <div class="field">
            <label>{{ $t('settings.profile.avatar') }}</label>
            <div class="avatar-upload">
              <div class="preview">
                <svg viewBox="0 0 24 24" class="svg-icon-large"><path d="M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"/></svg>
              </div>
              <button class="secondary-btn">{{ $t('settings.profile.change_image') }}</button>
            </div>
          </div>
          <div class="field">
            <label>{{ $t('settings.profile.name') }}</label>
            <input v-model="profile.name" type="text" />
          </div>
          <div class="field">
            <label>{{ $t('settings.profile.bio') }}</label>
            <textarea v-model="profile.bio"></textarea>
          </div>
          <div class="field">
            <label>{{ $t('settings.profile.password') }}</label>
            <input type="password" placeholder="••••••••" />
          </div>
        </div>

        <!-- Interface Tab -->
        <div v-if="activeTab === 'interface'" class="tab-view">
          <h2>{{ $t('settings.interface.title') }}</h2>
          <div class="field">
            <label>{{ $t('settings.interface.theme.title') }}</label>
            <div class="option-grid">
              <button v-for="t in themes" :key="t.id" 
                      class="option-btn" :class="{active: uiStore.theme === t.id}"
                      @click="uiStore.setTheme(t.id)">{{ $t(t.name) }}</button>
            </div>
          </div>
          <div class="field">
            <label>{{ $t('settings.interface.color.title') }}</label>
            <div class="option-grid">
              <button v-for="c in colors" :key="c.id" 
                      class="option-btn" :class="{active: uiStore.color === c.id}"
                      @click="uiStore.setColor(c.id)">{{ $t(c.name) }}</button>
            </div>
          </div>
          <div class="field">
            <label>{{ $t('settings.interface.scale') }} ({{ uiStore.scale.toFixed(1) }}x)</label>
            <input type="range" min="0.8" max="1.5" step="0.1" 
                   :value="uiStore.scale" @input="uiStore.setScale(parseFloat($event.target.value))" />
          </div>
        </div>

        <!-- Intelligence Tab -->
        <div v-if="activeTab === 'intelligence'" class="tab-view">
          <h2>Intelligence Configuration</h2>
          <div class="field">
            <label>OpenAI API Key</label>
            <input v-model="apiKeys.openai" type="password" placeholder="sk-..." />
          </div>
          <div class="field">
            <label>Google API Key</label>
            <input v-model="apiKeys.google" type="password" placeholder="AIza..." />
          </div>
          <button class="mango-button" @click="console.log('Fetch Models')">Fetch Available Models</button>
        </div>

        <!-- Server Tab (Admin Only) -->
        <div v-if="activeTab === 'server'" class="tab-view">
          <h2>Server & Triad Settings</h2>
          <div class="field">
            <label>Agent 0 (Supervisor) Key</label>
            <input v-model="serverKeys.agent0" type="password" />
          </div>
          <div class="field">
            <label>Orchestration Mode</label>
            <select>
              <option>Parallel Processing</option>
              <option>Sequential Cascade</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  backdrop-filter: blur(8px);
  z-index: 5000;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s ease-out;
}

.settings-panel {
  width: 900px;
  height: 600px;
  display: flex;
  overflow: hidden;
  box-shadow: 0 40px 100px rgba(0,0,0,0.8);
  border: 1px solid var(--border-strong);
}

.panel-sidebar {
  width: 220px;
  background: rgba(255, 255, 255, 0.02);
  border-right: 1px solid var(--border-subtle);
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tab-btn {
  padding: 12px 20px;
  border-radius: 10px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
}

.tab-btn:hover, .tab-btn.active {
  background: rgba(255, 255, 255, 0.05);
  color: var(--mango-primary);
}

.panel-content {
  flex: 1;
  padding: 40px;
  overflow-y: auto;
}

.tab-view h2 { margin-bottom: 32px; font-size: 24px; color: var(--mango-primary); }

.field { margin-bottom: 24px; display: flex; flex-direction: column; gap: 8px; }
.field label { font-size: 13px; font-weight: 700; opacity: 0.7; }
.field input, .field textarea, .field select {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-strong);
  padding: 12px;
  border-radius: 8px;
  color: var(--text-primary);
  outline: none;
}
.field input:focus { border-color: var(--mango-primary); }

.option-grid { display: flex; gap: 12px; }
.option-btn {
  padding: 8px 16px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  cursor: pointer;
}
.option-btn.active {
  border-color: var(--mango-primary);
  color: var(--mango-primary);
  background: rgba(255, 122, 0, 0.1);
}

.avatar-upload { display: flex; align-items: center; gap: 20px; }
.preview { width: 64px; height: 64px; border-radius: 50%; background: var(--border-strong); display: flex; align-items: center; justify-content: center; font-size: 32px; }

.spacer { flex: 1; }
.close-panel-btn {
  padding: 12px;
  border-radius: 10px;
  background: rgba(255, 0, 0, 0.05);
  color: var(--danger);
  border: 1px solid rgba(239, 68, 68, 0.2);
  cursor: pointer;
}

@keyframes fadeIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
</style>
