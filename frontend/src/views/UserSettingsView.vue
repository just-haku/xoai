<template>
  <div class="settings-window">
    <!-- Sidebar Navigation -->
    <aside class="settings-sidebar">
      <router-link to="/chat" class="back-link">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="3">
          <path d="M19 12H5M12 19l-7-7 7-7" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ t('userSettings.back_to_workspace') }}
      </router-link>
      <div class="sidebar-brand">
        XO<span class="mango-text">AI</span> <span>{{ t('userSettings.identity') }}</span>
      </div>
      <nav class="settings-nav">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          class="nav-item"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <div class="nav-icon" v-html="getIcon(tab.id)"></div>
          {{ tab.label }}
        </button>
      </nav>
    </aside>

    <!-- Content Area -->
    <main class="settings-main scrollable">
      <header class="pane-header">
        <div class="breadcrumb">{{ t('userSettings.breadcrumb') }} / {{ currentTab.label }}</div>
        <h1>{{ currentTab.label }}</h1>
        <p>{{ currentTab.description }}</p>
      </header>

      <!-- PROFILE TAB -->
      <div v-if="activeTab === 'profile'" class="tab-pane">
        <div class="form-section">
          <div class="profile-hero">
            <div class="avatar-manager">
              <div class="avatar-large" :style="profile.avatar ? { backgroundImage: `url(${profile.avatar})`, backgroundSize: 'cover' } : {}">
                <span v-if="!profile.avatar">{{ profile.name ? profile.name[0] : 'U' }}</span>
              </div>
              <button class="avatar-upload-btn" @click="$refs.avatarInput.click()">
                <svg viewBox="0 0 24 24"><path d="M4,4H7L9,2H15L17,4H20A2,2 0 0,1 22,6V18A2,2 0 0,1 20,20H4A2,2 0 0,1 2,18V6A2,2 0 0,1 4,4M12,7A5,5 0 0,0 7,12A5,5 0 0,0 12,17A5,5 0 0,0 17,12A5,5 0 0,0 12,7M12,9A3,3 0 0,1 15,12A3,3 0 0,1 12,15A3,3 0 0,1 9,12A3,3 0 0,1 12,9Z"/></svg>
              </button>
              <input type="file" ref="avatarInput" hidden @change="uploadAvatar" accept="image/*" />
            </div>
            <div class="hero-info">
              <div class="input-group">
                <label>{{ t('settings.profile.name') }}</label>
                <div class="name-edit-wrap">
                  <input v-model="profile.name" class="h1-input" :placeholder="t('settings.profile.name')" />
                  <span class="username-tag">@{{ profile.username }}</span>
                </div>
              </div>
              <div class="input-group email-verify-group">
                <label>{{ t('settings.profile.email') }}</label>
                <div class="email-control">
                  <input v-model="profile.email" class="p-input" :disabled="!isChangingEmail" />
                  <button v-if="!isChangingEmail" :disabled="profile.role === 'admin'" class="btn-micro" :class="{ 'btn-locked': profile.role === 'admin' }" @click="isChangingEmail = true">
                    <span v-if="profile.role === 'admin'">{{ t('userSettings.system_managed') }}</span>
                    <span v-else>{{ t('userSettings.change') }}</span>
                  </button>
                  <button v-if="isChangingEmail && !emailCodeSent" class="btn-micro btn-success" @click="requestEmailCode">{{ t('userSettings.get_code') }}</button>
                </div>
                <div v-if="emailCodeSent" class="verification-box mt-2">
                  <input v-model="emailCode" class="p-input code-input" :placeholder="t('userSettings.enter_code')" maxlength="6" />
                  <button class="btn-micro btn-success" @click="verifyEmailChange">{{ t('userSettings.verify_update') }}</button>
                  <button class="btn-micro btn-danger" @click="cancelEmailChange">{{ t('actions.cancel') }}</button>
                </div>
              </div>
            </div>
          </div>
          
          <div class="input-group mt-4">
            <label>{{ t('settings.profile.bio') }}</label>
            <textarea v-model="profile.bio" :placeholder="t('settings.profile.bio_placeholder')" rows="3"></textarea>
          </div>
        </div>
        <div class="action-bar">
          <button class="mango-button" @click="saveProfile">{{ t('userSettings.save_profile') }}</button>
        </div>

        <ImageCrop 
          :is-open="isCropping" 
          :image-src="cropSrc" 
          @close="isCropping = false" 
          @confirm="handleCropConfirm" 
        />
      </div>

      <!-- INTERFACE TAB -->
      <div v-if="activeTab === 'interface'" class="tab-pane">
        <div class="form-section">
          <div class="setting-item">
            <div class="item-info">
              <h3>{{ t('userSettings.ui_scaling') }}</h3>
              <p>{{ t('userSettings.ui_scaling_desc') }}</p>
            </div>
            <div class="item-control">
              <div class="scale-display">{{ Math.round(uiSettings.scale * 100) }}%</div>
              <input type="range" min="0.8" max="1.2" step="0.05" v-model="uiSettings.scale" @input="applyScale" />
            </div>
          </div>

          <div class="setting-item">
            <div class="item-info">
              <h3>{{ t('userSettings.theme_palette') }}</h3>
              <p>{{ t('userSettings.theme_palette_desc') }}</p>
            </div>
            <div class="item-control">
              <div class="theme-grid">
                <div 
                  v-for="color in themeColors" 
                  :key="color.id"
                  :class="['color-dot', color.id, { active: uiSettings.color === color.id }]"
                  :title="color.name"
                  @click="uiSettings.color = color.id; applyTheme()"
                ></div>
              </div>
            </div>
          </div>

          <div class="setting-item">
            <div class="item-info">
              <h3>{{ t('userSettings.aesthetics') }}</h3>
              <p>{{ t('userSettings.aesthetics_desc') }}</p>
            </div>
            <div class="item-control">
              <div class="toggle-wrap">
                <span class="toggle-label">{{ t('settings.interface.pastel') }}</span>
                <button class="toggle-btn" :class="{ active: uiSettings.pastel }" @click="uiSettings.pastel = !uiSettings.pastel; applyTheme()">
                  {{ uiSettings.pastel ? t('userSettings.on') : t('userSettings.off') }}
                </button>
              </div>
            </div>
          </div>

          <div class="setting-item">
            <div class="item-info">
              <h3>{{ t('settings.interface.language') }}</h3>
              <p>{{ t('userSettings.language_desc') }}</p>
            </div>
            <div class="item-control">
              <CSelect 
                v-model="uiSettings.lang" 
                :options="langOptions"
                @change="applyTheme" 
              />
            </div>
          </div>
        </div>
      </div>

      <!-- SECURITY TAB -->
      <div v-if="activeTab === 'security'" class="tab-pane">
        <div class="form-section">
          <div class="input-group">
            <label>{{ t('settings.security.old_pass') }}</label>
            <input type="password" v-model="security.old_password" placeholder="••••••••" />
          </div>
          <div class="input-group">
            <label>{{ t('settings.security.new_pass') }}</label>
            <input type="password" v-model="security.new_password" placeholder="••••••••" />
          </div>
          <div class="input-group">
            <label>{{ t('settings.security.confirm_pass') }}</label>
            <input type="password" v-model="security.confirm_password" placeholder="••••••••" />
          </div>
        </div>
        <div class="action-bar">
          <button class="mango-button" @click="updatePassword">{{ t('userSettings.update_security') }}</button>
        </div>
      </div>

      <!-- AGENT TAB -->
      <div v-if="activeTab === 'agent'" class="tab-pane">
        <div class="form-section">
          <div class="infra-card glass-panel p-4">
            <div class="input-group">
              <label>{{ t('settings.agent.provider') }}</label>
              <CSelect v-model="agent.provider" :options="agentProviderOptions" />
            </div>
            <div class="input-group mt-4">
              <label>{{ t('settings.agent.apiKey') }}</label>
              <div class="key-field">
                <input :type="showKey ? 'text' : 'password'" v-model="agent.key" placeholder="sk-..." />
                <button class="icon-toggle" @click="showKey = !showKey">
                   {{ showKey ? t('userSettings.hide') : t('userSettings.show') }}
                </button>
              </div>
            </div>
            <div class="input-group mt-4">
              <div class="label-with-action">
                <label>{{ t('userSettings.model_override') }}</label>
                <button 
                  class="btn-text-action" 
                  @click="fetchPersonalModels"
                  :disabled="agent.fetching"
                >
                  {{ agent.fetching ? t('userSettings.fetching') : t('settings.intelligence.fetch_models') }}
                </button>
              </div>
              <CSelect 
                v-if="agent.availableModels.length > 0"
                v-model="agent.model" 
                :options="agent.availableModels"
                :placeholder="t('userSettings.select_model')"
              />
              <input v-else v-model="agent.model" :placeholder="t('userSettings.model_placeholder')" />
            </div>
          </div>
        </div>
        <div class="action-bar">
          <button class="mango-button" @click="saveAgent">{{ t('userSettings.update_agent') }}</button>
        </div>
      </div>

      <!-- CHANNEL TAB -->
      <div v-if="activeTab === 'channel'" class="tab-pane">
        <div class="form-section gap-4">
          <div v-for="c in channels" :key="c.id" class="channel-card glass-panel">
            <div class="c-header">
              <div class="c-info">
                <div class="c-icon" v-html="getChannelIcon(c.id)"></div>
                <div class="c-meta">
                  <strong>{{ c.name }}</strong>
                  <span>{{ c.status === 'active' ? t('userSettings.connected') : t('userSettings.ready_to_link') }}</span>
                </div>
              </div>
              <button 
                class="btn-status" 
                :class="{ active: c.status === 'active' }"
                @click="toggleChannel(c)"
              >
                {{ c.status === 'active' ? t('userSettings.revoke_access') : t('userSettings.configure') }}
              </button>
            </div>
            <div v-if="c.configuring" class="c-config mt-2">
              <input type="password" v-model="c.token" :placeholder="t('userSettings.integration_key')" />
              <button class="mango-button small" @click="saveChannel(c)">{{ t('userSettings.finish_linking') }}</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useUIStore } from '../stores/ui'
import { api } from '../services/api'
import CSelect from '../components/common/CSelect.vue'
import ImageCrop from '../components/ImageCrop.vue'
import { useI18n } from 'vue-i18n'

const uiStore = useUIStore()
const { t } = useI18n()

const activeTab = ref('profile')
const showKey = ref(false)

const isCropping = ref(false)
const cropSrc = ref('')

const getIcon = (id) => {
  switch(id) {
    case 'profile': return '<svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>'
    case 'interface': return '<svg viewBox="0 0 24 24"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9c.83 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-.99 0-.83.67-1.5 1.5-1.5H16c2.76 0 5-2.24 5-5 0-4.42-4.03-8-9-8zm-5.5 9c-.83 0-1.5-.67-1.5-1.5S5.67 9 6.5 9 8 9.67 8 10.5 7.33 12 6.5 12zm3-4C8.67 8 8 7.33 8 6.5S8.67 5 9.5 5 11 5.67 11 6.5 10.33 8 9.5 8zm5 0c-.83 0-1.5-.67-1.5-1.5S13.67 5 14.5 5s1.5.67 1.5 1.5S15.33 8 14.5 8zm3 4c-.83 0-1.5-.67-1.5-1.5S16.67 9 17.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>'
    case 'security': return '<svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 8.5 12 4.66-1.26 8.5-6.45 8.5-12V5l-9-4z"/></svg>'
    case 'agent': return '<svg viewBox="0 0 24 24"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1V5.73c-.6-.34-1-1-1-1.73a2 2 0 0 1 2-2M9 9v2h2V9H9m4 0v2h2V9h-2M9 13v2h6v-2H9z"/></svg>'
    case 'channel': return '<svg viewBox="0 0 24 24"><path d="M11 2v4.07C7.38 6.57 4.5 9.47 4.07 13H1v2h3.07C4.5 18.53 7.38 21.43 11 21.93V24h2v-2.07c3.62-.5 6.5-3.4 6.93-6.93H23v-2h-3.07C19.5 9.47 16.62 6.57 13 6.07V2h-2m1 6a6 6 0 0 1 6 6 6 6 0 0 1-6 6 6 6 0 0 1-6-6 6 6 0 0 1 6-6z"/></svg>'
    default: return ''
  }
}

const tabs = computed(() => [
  { id: 'profile', label: t('userSettings.tabs.profile.label'), description: t('userSettings.tabs.profile.desc') },
  { id: 'interface', label: t('userSettings.tabs.interface.label'), description: t('userSettings.tabs.interface.desc') },
  { id: 'security', label: t('userSettings.tabs.security.label'), description: t('userSettings.tabs.security.desc') },
  { id: 'agent', label: t('userSettings.tabs.agent.label'), description: t('userSettings.tabs.agent.desc') },
  { id: 'channel', label: t('userSettings.tabs.channel.label'), description: t('userSettings.tabs.channel.desc') }
])

const currentTab = computed(() => tabs.value.find((tab) => tab.id === activeTab.value))

// State
const profile = reactive({ name: '', username: '', email: '', bio: '', avatar: null, role: 'user' })
const security = reactive({ old_password: '', new_password: '', confirm_password: '' })
const agent = reactive({ provider: 'gemini', key: '', model: '', fetching: false, availableModels: [] })
const uiSettings = reactive({ 
  scale: uiStore.scale, 
  color: uiStore.color, 
  pastel: uiStore.pastel, 
  lang: uiStore.lang 
})

const langOptions = computed(() => [
  { label: t('userSettings.languages.en'), value: 'en' },
  { label: t('userSettings.languages.vi'), value: 'vi' }
])

const agentProviderOptions = computed(() => [
  { label: t('userSettings.providers.gemini'), value: 'gemini' },
  { label: t('userSettings.providers.openai'), value: 'openai' },
  { label: t('userSettings.providers.anthropic'), value: 'anthropic' }
])

const isChangingEmail = ref(false)
const emailCode = ref('')
const emailCodeSent = ref(false)

const getChannelIcon = (id) => {
  switch(id) {
    case 'discord': return '<svg viewBox="0 0 24 24"><path d="M19.27 4.73C17.78 3.35 15.83 2.54 13.67 2.54V4.04C15.39 4.04 16.94 4.67 18.13 5.7L19.27 4.73M16 12C16 11.17 15.33 10.5 14.5 10.5S13 11.17 13 12 13.67 13.5 14.5 13.5 16 12.83 16 12M11 12C11 11.17 10.33 10.5 9.5 10.5S8 11.17 8 12 8.67 13.5 9.5 13.5 11 12.83 11 12M12 2C6.48 2 2 6.48 2 12S6.48 22 12 22 22 17.52 22 12 17.52 2 12 2M18 16V16C18 16 18 16 18 16V16C18 16 16.33 17 14.5 17L14.28 16.78C15.33 16.44 16.22 15.81 16.94 15.11C16.03 15.67 15.05 16.03 14 16.21C13.37 16.32 12.7 16.4 12 16.4S10.63 16.32 10 16.21C8.95 16.03 7.97 15.67 7.06 15.11C7.78 15.81 8.67 16.44 9.72 16.78L9.5 17C7.67 17 6 16 6 16V16C6 16 6 16 6 16V16C6 13 7 10 9.5 8C10.5 7.5 11.5 7.2 12.5 7.2S14.5 7.5 15.5 8C18 10 19 13 19 16Z"/></svg>'
    case 'telegram': return '<svg viewBox="0 0 24 24"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.28-.89-.88.19-1.33L10.23 11l.28-4.23L21 3.5l-3.5 18-7.72-2.85z"/></svg>'
    case 'zalo': return '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8 0-.29.02-.58.05-.86 2.36-1.05 4.23-2.98 5.21-5.37C11.07 8.33 14.05 10 17.42 10c.78 0 1.53-.09 2.25-.26.21.41.33.88.33 1.37 0 4.41-3.59 8-8 8z"/></svg>' // Fallback icon
    default: return ''
  }
}

const themeColors = [
  { id: 'xoai', name: 'XOAI' },
  { id: 'red', name: t('userSettings.colors.red') },
  { id: 'pink', name: t('userSettings.colors.pink') },
  { id: 'blue', name: t('userSettings.colors.blue') },
  { id: 'yellow', name: t('userSettings.colors.yellow') },
  { id: 'green', name: t('userSettings.colors.green') },
  { id: 'contrast', name: t('userSettings.colors.contrast') }
]

const channels = ref([
  { id: 'discord', name: 'Discord', status: 'idle', token: '', configuring: false },
  { id: 'zalo', name: 'Zalo', status: 'idle', token: '', configuring: false },
  { id: 'telegram', name: 'Telegram', status: 'idle', token: '', configuring: false }
])

const fetchUser = async () => {
  try {
    const data = await api.auth.me()
    Object.assign(profile, {
      name: data.name,
      username: data.username,
      email: data.email,
      bio: data.bio || '',
      avatar: data.avatar || null,
      role: data.role || 'user'
    })
  } catch (err) {}
}

const uploadAvatar = (e) => {
  const file = e.target.files[0]
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = (re) => {
    cropSrc.value = reader.result
    isCropping.value = true
  }
  reader.readAsDataURL(file)
}

const handleCropConfirm = async (data) => {
  // data contains zoom and offset, but for now we upload the source 
  // until we implement client-side canvas cropping (planned v2)
  const formData = new FormData()
  
  // Convert base64 to blob if needed, but the current backend expects a file 
  // Let's stick to the current implementation's expectation of a real File object first
  // Actually, handleCropConfirm should probably just perform the upload with the original file 
  // if we aren't doing the actual canvas crop yet. 
  // But the user wants it to "open".
  
  const fileInput = document.querySelector('input[type="file"][ref="avatarInput"]') 
  // Wait, I can't easily get the file back from input here if I use ref. 
  // Let's just use the cropSrc blob.
  
  try {
    // Basic implementation: send original file for now, but UI shows the "Apply" step
    // fetch user avatar to blob 
    const response = await fetch(cropSrc.value)
    const blob = await response.blob()
    const file = new File([blob], "avatar.png", { type: "image/png" })
    
    const formData = new FormData()
    formData.append('file', file)
    
    const res = await api.request('/users/avatar', {
      method: 'POST',
      body: formData
    })
    profile.avatar = res.url
    uiStore.notify(t('userSettings.notifications.avatar_updated'), 'success')
    isCropping.value = false
  } catch (err) {
    uiStore.notify(t('userSettings.notifications.avatar_failed'), 'danger')
  }
}

const requestEmailCode = async () => {
  try {
    await api.request('/users/email-verification-code', {
      method: 'POST',
      body: JSON.stringify({ email: profile.email })
    })
    emailCodeSent.value = true
    uiStore.notify(t('userSettings.notifications.code_sent', { email: profile.email }), 'info')
  } catch (err) {
    uiStore.notify(t('userSettings.notifications.code_failed', { error: err.message }), 'danger')
  }
}

const verifyEmailChange = async () => {
  try {
    await api.request('/users/update-email', {
      method: 'PUT',
      body: JSON.stringify({ email: profile.email, code: emailCode.value })
    })
    uiStore.notify(t('userSettings.notifications.email_updated'), 'success')
    isChangingEmail.value = false
    emailCodeSent.value = false
    emailCode.value = ''
  } catch (err) {
    uiStore.notify(t('userSettings.notifications.verification_failed', { error: err.message }), 'danger')
  }
}

const cancelEmailChange = () => {
  isChangingEmail.value = false
  emailCodeSent.value = false
  emailCode.value = ''
  fetchUser() // Reset to current email
}

const saveProfile = async () => {
  try {
    await api.users.updateProfile({ name: profile.name, bio: profile.bio })
    uiStore.notify(t('userSettings.notifications.profile_updated'), 'success')
  } catch (err) {
    uiStore.notify(t('userSettings.notifications.update_failed', { error: err.message }), 'danger')
  }
}

const updatePassword = async () => {
  if (security.new_password !== security.confirm_password) {
    return uiStore.notify(t('userSettings.notifications.password_mismatch'), 'warning')
  }
  try {
    await api.users.changePassword({
      old_password: security.old_password,
      new_password: security.new_password
    })
    uiStore.notify(t('userSettings.notifications.password_updated'), 'success')
    security.old_password = ''
    security.new_password = ''
    security.confirm_password = ''
  } catch (err) {
    uiStore.notify(t('userSettings.notifications.password_failed', { error: err.message }), 'danger')
  }
}

const saveAgent = async () => {
  try {
    await api.users.updateIntelligence({
      provider: agent.provider,
      key: agent.key,
      model: agent.model
    })
    uiStore.notify(t('userSettings.notifications.agent_updated'), 'success')
  } catch (err) {
    uiStore.notify(t('userSettings.notifications.agent_failed', { error: err.message }), 'danger')
  }
}

const fetchPersonalModels = async () => {
  if (!agent.key) {
    uiStore.notify(t('userSettings.notifications.api_key_required'), 'warning')
    return
  }
  
  agent.fetching = true
  try {
    // 1. Save settings first 
    await saveAgent()
    
    // 2. Call backend fetch
    const resp = await api.request('/users/agent/models', {
      method: 'POST',
      body: JSON.stringify({
        provider: agent.provider,
        key: agent.key,
        base_url: agent.model && agent.model.startsWith('http') ? agent.model : null
      })
    })
    
    if (resp.models && resp.models.length > 0) {
      agent.availableModels = resp.models.map(m => ({ label: m, value: m }))
      uiStore.notify(t('userSettings.notifications.models_fetched', { count: resp.models.length }), 'success')
    } else {
      uiStore.notify(t('userSettings.notifications.no_models'), 'info')
    }
  } catch (err) {
    uiStore.notify(t('userSettings.notifications.fetch_failed', { error: err.message }), 'danger')
  } finally {
    agent.fetching = false
  }
}

const toggleChannel = (c) => {
  if (c.status === 'active') {
    c.status = 'idle'
  } else {
    c.configuring = !c.configuring
  }
}

const saveChannel = async (c) => {
  try {
    await api.users.updateIntegrations({ [c.id]: c.token })
    c.status = 'active'
    c.configuring = false
    uiStore.notify(t('userSettings.notifications.channel_connected', { name: c.name }), 'success')
  } catch (err) {
    uiStore.notify(t('userSettings.notifications.channel_failed', { name: c.name }), 'danger')
  }
}

const applyScale = () => {
  uiStore.setScale(uiSettings.scale)
  uiStore.apply()
}

const applyTheme = () => {
  uiStore.setColor(uiSettings.color)
  uiStore.setPastel(uiSettings.pastel)
  uiStore.setLang(uiSettings.lang)
  uiStore.apply()
}

onMounted(fetchUser)
</script>

<style scoped>
.settings-window {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
  overflow: hidden;
}

.settings-sidebar {
  width: 260px;
  border-right: 1px solid var(--border-subtle);
  padding: 24px;
  display: flex;
  flex-direction: column;
  background: var(--bg-glass);
}

.back-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 24px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  border-radius: 12px;
  transition: all 0.2s;
  border: 1px solid transparent;
}
.back-link:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  border-color: var(--border-subtle);
}
.back-link svg {
  opacity: 0.6;
  transition: transform 0.2s;
}
.back-link:hover svg {
  opacity: 1;
  transform: translateX(-3px);
}

.sidebar-brand {
  font-size: 24px;
  font-weight: 900;
  padding: 0 16px 32px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sidebar-brand span:last-child {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 2px;
  opacity: 0.4;
  margin-top: 4px;
}

.settings-nav { display: flex; flex-direction: column; gap: 8px; }
.nav-item {
  display: flex; align-items: center; gap: 14px; padding: 14px 18px; border-radius: 12px;
  background: transparent; border: none; color: var(--text-secondary); font-weight: 700; font-size: 14px;
  cursor: pointer; text-align: left; transition: all 0.2s;
}
.nav-item:hover, .nav-item.active { background: rgba(255,255,255,0.05); color: var(--text-primary); }
.nav-item.active { color: var(--mango-primary); background: rgba(255, 170, 0, 0.05); border: 1px solid rgba(255, 170, 0, 0.1); }
.nav-icon { width: 20px; height: 20px; opacity: 0.7; }
.nav-item.active .nav-icon { opacity: 1; color: var(--mango-primary); }
.nav-icon :deep(svg) { width: 100%; height: 100%; fill: currentColor; }

.settings-main { flex: 1; padding: 60px 80px; overflow-y: auto; background: var(--bg-primary); }

.pane-header { margin-bottom: 48px; }
.breadcrumb { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; opacity: 0.4; margin-bottom: 12px; font-weight: 800; }
.pane-header h1 { font-size: 2.5rem; font-weight: 900; margin-bottom: 8px; letter-spacing: -1px; }
.pane-header p { color: var(--text-secondary); font-size: 15px; max-width: 600px; line-height: 1.6; }

.tab-pane { display: flex; flex-direction: column; gap: 32px; max-width: 1000px; }

.profile-hero { display: flex; align-items: flex-start; gap: 48px; background: var(--bg-glass); padding: 40px; border-radius: 32px; border: 1px solid var(--border-subtle); }
.avatar-manager { position: relative; }
.avatar-large {
  width: 120px; height: 120px; border-radius: 50%; background: var(--mango-primary);
  display: flex; align-items: center; justify-content: center; font-size: 3rem; font-weight: 900; color: #000;
  box-shadow: 0 10px 40px var(--mango-glow);
}
.avatar-upload-btn {
  position: absolute; bottom: 0; right: 0; width: 40px; height: 40px; border-radius: 50%;
  background: var(--bg-tertiary); border: 2px solid var(--border-strong); color: var(--text-primary);
  display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s;
}
.avatar-upload-btn:hover { background: var(--mango-primary); color: #000; transform: scale(1.1); }
.avatar-upload-btn svg { width: 20px; fill: currentColor; }

.hero-info { flex: 1; display: flex; flex-direction: column; gap: 24px; }

.h1-input {
  font-size: 2rem; font-weight: 900; background: transparent; border: none;
  border-bottom: 2px solid var(--border-subtle); color: var(--text-primary); width: 100%; outline: none;
  padding: 8px 0; transition: border-color 0.3s;
}
.h1-input:focus { border-bottom-color: var(--mango-primary); }

.name-edit-wrap { position: relative; }
.username-tag {
  position: absolute; right: 0; bottom: 12px; font-size: 14px; font-weight: 700;
  color: var(--text-secondary); opacity: 0.5; pointer-events: none;
}

.email-control { display: flex; gap: 12px; align-items: center; }
.verification-box { 
  display: flex; gap: 12px; align-items: center; padding: 16px; 
  background: rgba(var(--mango-primary-rgb, 255, 170, 0), 0.05); border-radius: 12px; border: 1px dashed var(--mango-primary);
}
.code-input { width: 180px; text-align: center; letter-spacing: 4px; font-weight: 900; font-size: 1.2rem; }

.btn-micro {
  padding: 6px 12px; border-radius: 8px; font-size: 11px; font-weight: 800;
  text-transform: uppercase; border: 1px solid var(--border-strong);
  background: var(--bg-tertiary); color: var(--text-primary); cursor: pointer;
  transition: all 0.2s; white-space: nowrap;
}
.btn-micro:hover:not(:disabled) { background: var(--bg-hover); transform: translateY(-1px); }
.btn-micro.btn-success { color: #00ff88; border-color: rgba(0, 255, 136, 0.2); }
.btn-micro.btn-danger { color: #ff4d4d; border-color: rgba(255, 77, 77, 0.2); }
.btn-micro.btn-locked { opacity: 0.5; cursor: not-allowed; border-color: transparent; background: transparent; color: var(--text-secondary); }
.btn-micro:disabled { opacity: 0.5; pointer-events: none; }

.input-group label {
  display: block; font-size: 11px; font-weight: 800; color: var(--mango-primary);
  text-transform: uppercase; margin-bottom: 8px;
}

.label-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.label-with-action label {
  margin-bottom: 0;
}
.btn-text-action {
  background: transparent;
  border: none;
  color: var(--mango-primary);
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
  opacity: 0.8;
}
.btn-text-action:hover:not(:disabled) {
  opacity: 1;
  background: rgba(var(--mango-primary-rgb, 255, 170, 0), 0.1);
}
.btn-text-action:disabled {
  opacity: 0.4;
  cursor: wait;
}

textarea {
  background: var(--bg-tertiary); border: 1px solid var(--border-strong);
  padding: 12px; border-radius: 10px; color: var(--text-primary); width: 100%; resize: vertical; outline: none;
}

.setting-item {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 24px; border-bottom: 1px solid var(--border-subtle);
}

.item-info h3 { font-size: 14px; margin-bottom: 2px; }
.item-info p { font-size: 12px; opacity: 0.5; }

.item-control { display: flex; align-items: center; gap: 16px; min-width: 200px; justify-content: flex-end; }

.theme-grid { display: flex; gap: 8px; }
.color-dot {
  width: 20px; height: 20px; border-radius: 50%; cursor: pointer; border: 2px solid transparent;
}
.color-dot.active { border-color: #fff; transform: scale(1.2); }

.color-dot.xoai { background: linear-gradient(135deg, #00ff88, #ffaa00); }
.color-dot.red { background: #ff4d4d; }
.color-dot.pink { background: #ff69b4; }
.color-dot.blue { background: #0088ff; }
.color-dot.yellow { background: #ffcc00; }
.color-dot.green { background: #00cc66; }
.color-dot.contrast { background: #fff; }

.toggle-wrap { display: flex; align-items: center; gap: 12px; }
.toggle-label { font-size: 12px; font-weight: 600; }

.toggle-btn {
  padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border-strong);
  background: transparent; color: var(--text-secondary); font-size: 11px; font-weight: 800; cursor: pointer;
}
.toggle-btn.active { background: var(--mango-primary); color: #000; border-color: var(--mango-primary); }

.key-field { display: flex; gap: 8px; width: 100%; }
.key-field input { flex: 1; }
.icon-toggle { background: var(--bg-tertiary); border: 1px solid var(--border-strong); border-radius: 8px; padding: 0 10px; cursor: pointer; }

.channel-card {
  padding: 20px; display: flex; flex-direction: column; gap: 12px;
}
.c-header { display: flex; justify-content: space-between; align-items: center; }
.c-info { display: flex; align-items: center; gap: 12px; }
.c-icon { font-size: 1.5rem; }
.c-meta { display: flex; flex-direction: column; }
.c-meta strong { font-size: 14px; }
.c-meta span { font-size: 11px; opacity: 0.5; }

.btn-status {
  padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border-strong);
  background: transparent; color: var(--text-primary); font-size: 11px; font-weight: 700; cursor: pointer;
}
.btn-status.active { color: var(--danger); border-color: var(--danger); }

.scale-display { font-family: monospace; font-weight: 900; font-size: 14px; color: var(--mango-primary); }

.mt-4 { margin-top: 16px; }
.p-4 { padding: 24px; }
</style>
