<template>
  <div class="settings-page user-settings">
    <header class="settings-header">
      <h1>User Settings</h1>
      <p>Configure your personal profile, identity, and interface preferences.</p>
    </header>

    <div class="settings-grid">
      <!-- Profile section -->
      <section class="settings-card glass-panel profile-hero">
        <div class="profile-main">
          <div class="avatar-wrap">
            <div class="avatar-circle">👤</div>
            <button class="edit-overlay">Edit</button>
          </div>
          <div class="profile-input-group">
            <input v-model="profile.name" class="h1-input" placeholder="Display Name" />
            <input v-model="profile.bio" class="p-input" placeholder="Add a bio..." />
          </div>
        </div>
      </section>

      <!-- Intelligence section -->
      <section class="settings-card glass-panel">
        <div class="section-header"><h3>🔑 Personal Intelligence</h3></div>
        <div class="setting-item">
          <label>API Provider</label>
          <select v-model="keys.provider">
            <option value="gemini">Google Gemini</option>
            <option value="openai">OpenAI</option>
          </select>
        </div>
        <div class="setting-item">
          <label>API Key</label>
          <div class="input-row">
            <input type="password" v-model="keys.apiKey" placeholder="sk-..." />
            <button class="mango-button tiny" @click="fetchModels">Fetch</button>
          </div>
        </div>
        <div v-if="models.length > 0" class="setting-item">
          <label>Default Model</label>
          <select v-model="keys.model">
            <option v-for="m in models" :key="m" :value="m">{{m}}</option>
          </select>
        </div>
      </section>

      <!-- UI Customization -->
      <section class="settings-card glass-panel">
        <div class="section-header"><h3>🎨 Interface & UX</h3></div>
        <div class="setting-item">
          <label>Theme Variant</label>
          <div class="color-grid">
            <div v-for="t in themes" :key="t.id" 
                 :class="['color-dot', t.id, {active: currentTheme === t.id}]"
                 :title="t.name" @click="setTheme(t.id)"></div>
          </div>
        </div>
        <div class="setting-item">
          <label>UI Scale ({{ Math.round(uiScale * 100) }}%)</label>
          <input type="range" min="0.7" max="1.5" step="0.1" v-model="uiScale" @change="setScale" />
        </div>
        <div class="setting-item">
          <label>Language</label>
          <select v-model="language">
            <option value="en">English (Global)</option>
            <option value="vi">Tiếng Việt (Vietnam)</option>
          </select>
        </div>
      </section>

      <!-- Security -->
      <section class="settings-card glass-panel">
        <div class="section-header"><h3>🛡️ Security</h3></div>
        <div class="setting-item">
          <label>Change Password</label>
          <input type="password" placeholder="New Password" />
        </div>
        <button class="mango-button">Update Security</button>
      </section>
    </div>
    
    <footer class="settings-footer">
       <button class="mango-button save-all">Save All Changes</button>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'

const profile = reactive({ name: 'Haku', bio: 'AI Systems Architect' })
const keys = reactive({ provider: 'gemini', apiKey: '', model: 'gemini-1.5-pro' })
const models = ref([])
const uiScale = ref(1.0)
const language = ref('en')
const currentTheme = ref('xoai')

const themes = [
  { id: 'dark', name: 'Original Dark' },
  { id: 'contrast', name: 'High Contrast' },
  { id: 'blue', name: 'Cobalt Blue' },
  { id: 'green', name: 'Forest Green' },
  { id: 'yellow', name: 'Cyber Yellow' },
  { id: 'xoai', name: 'XOAI Gradient' }
]

const setTheme = (id) => {
  currentTheme.value = id
  document.documentElement.setAttribute('data-theme', id)
}

const setScale = () => {
  document.documentElement.style.fontSize = `${16 * uiScale.value}px`
}

const fetchModels = () => {
  models.value = ['gemini-1.5-pro', 'gemini-1.5-flash', 'gpt-4o', 'gpt-4-turbo']
}
</script>

<style scoped>
.settings-page { max-width: 1000px; margin: 0 auto; padding: 60px 20px; }
.settings-header { margin-bottom: 40px; }
.settings-header h1 { font-size: 2.5rem; margin-bottom: 8px; }
.settings-header p { opacity: 0.6; }

.settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

.settings-card { padding: 32px; display: flex; flex-direction: column; gap: 24px; }

.profile-hero { grid-column: span 2; }
.profile-main { display: flex; align-items: center; gap: 32px; }

.avatar-wrap { position: relative; width: 100px; height: 100px; }
.avatar-circle { width: 100px; height: 100px; border-radius: 50%; background: var(--bg-tertiary); display: flex; align-items: center; justify-content: center; font-size: 48px; border: 2px solid var(--mango-primary); }
.edit-overlay { position: absolute; bottom: 0; right: 0; background: var(--mango-primary); border: none; border-radius: 40%; padding: 4px 8px; font-size: 10px; cursor: pointer; color: white; }

.profile-input-group { flex: 1; }
.h1-input { font-size: 2rem; font-weight: 800; border: none; background: transparent; width: 100%; border-bottom: 2px solid transparent; transition: border-color 0.3s; }
.h1-input:focus { border-bottom-color: var(--mango-primary); outline: none; }
.p-input { border: none; background: transparent; width: 100%; opacity: 0.7; font-size: 1.1rem; margin-top: 8px; }

.setting-item { display: flex; flex-direction: column; gap: 8px; }
.setting-item label { font-size: 11px; font-weight: 800; text-transform: uppercase; opacity: 0.5; letter-spacing: 0.05rem; }

input, select { background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-subtle); padding: 12px; border-radius: 10px; color: white; font-size: 14px; }
.input-row { display: flex; gap: 8px; }
.input-row input { flex: 1; }

.color-grid { display: flex; gap: 12px; }
.color-dot { width: 32px; height: 32px; border-radius: 8px; cursor: pointer; border: 2px solid transparent; transition: transform 0.2s; }
.color-dot:hover { transform: scale(1.1); }
.color-dot.active { border-color: white; transform: scale(1.15); }

.color-dot.dark { background: #1a1a1c; }
.color-dot.contrast { background: #ffffff; }
.color-dot.blue { background: #0088ff; }
.color-dot.green { background: #00cc66; }
.color-dot.yellow { background: #ffcc00; }
.color-dot.xoai { background: linear-gradient(135deg, #00ff88, #ffaa00); }

.mango-button.tiny { padding: 4px 12px; font-size: 11px; }

.settings-footer { margin-top: 40px; display: flex; justify-content: flex-end; }
</style>
