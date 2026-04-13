<template>
  <div class="settings-page">
    <header class="settings-header">
      <h1>Settings</h1>
      <p>Configure your personal XOAI experience.</p>
    </header>

    <div class="settings-container">
      <section class="settings-card glass-panel">
        <form @submit.prevent="save">
          <div class="section-header">
            <span class="icon">🔑</span>
            <h3>Intelligence API Keys</h3>
          </div>
          
          <div class="setting-item">
            <label>Provider</label>
            <select v-model="provider">
              <option value="gemini">Google Gemini</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>

          <div class="setting-item">
            <label>API Key</label>
            <div class="input-with-reveal">
              <input :type="showKey ? 'text' : 'password'" v-model="apiKey" placeholder="sk-..." />
              <button type="button" @click="showKey = !showKey">{{ showKey ? '🙈' : '👁️' }}</button>
            </div>
          </div>

          <div class="setting-item">
            <label>Default Model</label>
            <input v-model="model" placeholder="gemini-1.5-pro" />
          </div>

          <button type="submit" class="mango-button save-btn">Save Identity</button>
        </form>
      </section>

      <section class="settings-card glass-panel">
        <div class="section-header">
          <span class="icon">🌍</span>
          <h3>Localization & UI</h3>
        </div>
        
        <div class="setting-item">
          <label>Preferred Language</label>
          <div class="radio-group">
            <button :class="{ active: lang === 'en' }" @click="lang = 'en'">English</button>
            <button :class="{ active: lang === 'vi' }" @click="lang = 'vi'">Tiếng Việt</button>
          </div>
        </div>

        <div class="setting-item">
          <label>Theme Accent</label>
          <div class="color-picker">
            <div class="color mango active"></div>
            <div class="color cyan"></div>
            <div class="color purple"></div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const provider = ref('gemini')
const apiKey = ref('')
const model = ref('gemini-1.5-pro')
const showKey = ref(false)
const lang = ref('en')

const save = () => {
  alert('Settings saved securely.')
}
</script>

<style scoped>
.settings-page {
  padding: var(--spacing-10);
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-8);
}

.settings-header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.settings-header p {
  opacity: 0.6;
}

.settings-container {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: var(--spacing-8);
}

.settings-card {
  padding: var(--spacing-8);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: var(--spacing-2);
}

.section-header .icon {
  font-size: 1.5rem;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-item label {
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 800;
  opacity: 0.5;
  letter-spacing: 0.05rem;
}

input, select {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  padding: 12px;
  border-radius: 10px;
  color: white;
  font-size: 14px;
}

.input-with-reveal {
  display: flex;
  gap: 8px;
}

.input-with-reveal input {
  flex: 1;
}

.input-with-reveal button {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
}

.radio-group {
  display: flex;
  gap: 8px;
}

.radio-group button {
  flex: 1;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: white;
  cursor: pointer;
}

.radio-group button.active {
  background: var(--mango-primary);
  border-color: var(--mango-primary);
}

.color-picker {
  display: flex;
  gap: 12px;
}

.color {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
}

.color.active {
  border-color: white;
}

.color.mango { background: var(--mango-primary); }
.color.cyan { background: #00d4ff; }
.color.purple { background: #b042ff; }

.save-btn {
  margin-top: var(--spacing-4);
}
</style>
