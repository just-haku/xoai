<template>
  <div v-if="show" class="settings-overlay-backdrop" @click.self="$emit('close')">
    <div class="settings-panel glass-panel shadow-premium" @click.stop>
      <div class="panel-header">
        <div class="user-brief">
          <div class="avatar-hub" @click="triggerAvatarUpload">
            <img :src="userAvatar" alt="Avatar" />
            <div class="overlay">{{ $t('settings.profile.change_image') }}</div>
          </div>
          <div class="info">
            <h3>{{ user.name || 'Haku' }}</h3>
            <p>{{ user.email || 'haku@xoai.io' }}</p>
          </div>
        </div>
        <div class="quota-badge">
           <span>{{ $t('admin.users.table.storage') }}: {{ quotaFormatted }} / 15GB</span>
           <div class="progress-bar"><div class="fill" :style="{width: quotaPercent + '%'}"></div></div>
        </div>
        <button class="close-btn-top" @click="$emit('close')">✕</button>
      </div>

      <div class="tabs-nav">
        <button v-for="t in filteredTabs" :key="t.id" :class="{active: activeTab === t.id}" @click="activeTab = t.id">{{ $t(t.label) }}</button>
      </div>

      <div class="tab-content scrollable">
        <!-- Profile Tab -->
        <div v-if="activeTab === 'profile'" class="tab-pane">
           <div class="form-group">
             <label>{{ $t('settings.profile.bio') }}</label>
             <textarea v-model="draft.profile.bio" :placeholder="$t('settings.profile.bio_placeholder')"></textarea>
           </div>
        </div>

        <!-- Appearance Tab -->
        <div v-if="activeTab === 'appearance'" class="tab-pane">
           <div class="form-group">
              <label>{{ $t('settings.interface.scale') }}</label>
              <div class="scale-ctrl">
                <button @click="draft.scale = Math.max(0.8, draft.scale - 0.1)">-</button>
                <span>{{ Math.round(draft.scale * 100) }}%</span>
                <button @click="draft.scale = Math.min(1.5, draft.scale + 0.1)">+</button>
              </div>
           </div>
           <div class="form-group">
             <label>{{ $t('settings.interface.theme.title') }}</label>
             <CSelect 
               v-model="draft.theme" 
               :options="themeOptions"
             />
           </div>
           <div class="form-group">
             <label>{{ $t('settings.interface.language') }}</label>
             <CSelect 
               v-model="draft.lang" 
               :options="langOptions"
             />
           </div>
        </div>

        <!-- Security Tab -->
        <div v-if="activeTab === 'security'" class="tab-pane">
           <div class="form-group">
             <label>{{ $t('settings.security.old_pass') }}</label>
             <input type="password" v-model="draft.pass.old" />
           </div>
           <div class="form-group">
             <label>{{ $t('settings.security.new_pass') }}</label>
             <input type="password" v-model="draft.pass.new" />
           </div>
           <div class="form-group">
             <label>{{ $t('settings.security.confirm_pass') }}</label>
             <input type="password" v-model="draft.pass.confirm" />
           </div>
        </div>

        <!-- Intelligence Tab -->
        <div v-if="activeTab === 'intelligence'" class="tab-pane">
           <div class="form-group">
             <label>{{ $t('settings.intelligence.provider') }}</label>
             <CSelect 
               v-model="draft.intel.provider" 
               :options="providerOptions"
             />
           </div>
           <div class="form-group">
              <label>{{ $t('settings.intelligence.api_keys') }}</label>
              <div class="key-input">
                <input :type="keyVisible ? 'text' : 'password'" v-model="draft.intel.key" placeholder="••••••••••••" />
                <button class="btn-text-action" @click="keyVisible = !keyVisible">
                   {{ keyVisible ? 'HIDE' : 'SHOW' }}
                </button>
              </div>
           </div>
        </div>

        <!-- Integrations Tab -->
        <div v-if="activeTab === 'integrations'" class="tab-pane">
           <div class="form-group">
             <label>{{ $t('settings.integrations.discord') }}</label>
             <input type="password" v-model="draft.integrations.discord" placeholder="Bot Token..." />
           </div>
           <div class="form-group">
             <label>{{ $t('settings.integrations.telegram') }}</label>
             <input type="password" v-model="draft.integrations.telegram" placeholder="Bot Token..." />
           </div>
           <div class="form-group">
             <label>{{ $t('settings.integrations.zalo') }}</label>
             <input type="password" v-model="draft.integrations.zalo" placeholder="Bot Token..." />
           </div>
           <p style="font-size: 11px; opacity: 0.6; margin-top: 8px;">
             {{ $t('settings.integrations.tip') }}
           </p>
        </div>
      </div>

      <div class="panel-footer">
        <button class="save-btn mango-button" @click="saveChanges">{{ $t('settings.common.save') }}</button>
      </div>
    </div>

    <!-- Image Crop Modal -->
    <ImageCrop :is-open="isCropping" :image-src="cropSrc" @close="isCropping = false" @confirm="handleCropConfirm" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { useUIStore } from '../stores/ui'
import ImageCrop from './ImageCrop.vue'
import { api } from '../services/api'
import CSelect from './common/CSelect.vue'

const DEFAULT_AVATAR = `data:image/svg+xml;base64,${btoa('<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100" fill="#FF7A00"/><text x="50" y="65" font-family="Arial" font-size="50" font-weight="bold" fill="white" text-anchor="middle">X</text></svg>')}`

const props = defineProps({
  show: Boolean
})

const emit = defineEmits(['close'])

const uiStore = useUIStore()
const activeTab = ref('profile')
const keyVisible = ref(false)

const themeOptions = [
  { label: 'Light', value: 'light' },
  { label: 'Dark', value: 'dark' }
]

const langOptions = [
  { label: 'English (US)', value: 'en' },
  { label: 'Tiếng Việt', value: 'vi' }
]

const providerOptions = [
  { label: 'Google Gemini', value: 'gemini' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' }
]

const isCropping = ref(false)
const cropSrc = ref('')
const userAvatar = ref(localStorage.getItem('xoai_avatar') || DEFAULT_AVATAR)
const user = ref({ name: '', email: '', role: 'user' })

const tabs = [
  { id: 'profile', label: 'settings.profile.title' },
  { id: 'appearance', label: 'settings.interface.title' },
  { id: 'security', label: 'settings.security.title' },
  { id: 'intelligence', label: 'settings.intelligence.title' },
  { id: 'integrations', label: 'settings.integrations.title' }
]

const filteredTabs = computed(() => tabs)

const draft = reactive({
  profile: { bio: localStorage.getItem('xoai_bio') || '' },
  pass: { old: '', new: '', confirm: '' },
  intel: { 
    provider: localStorage.getItem('xoai_provider') || 'gemini', 
    key: localStorage.getItem('xoai_key') || '' 
  },
  integrations: {
    discord: localStorage.getItem('xoai_bot_discord') || '',
    telegram: localStorage.getItem('xoai_bot_telegram') || '',
    zalo: localStorage.getItem('xoai_bot_zalo') || ''
  },
  scale: uiStore.scale,
  theme: uiStore.theme,
  lang: uiStore.lang
})

const quotaPercent = ref(12) 
const quotaFormatted = computed(() => '1.8GB')

const fetchUserData = async () => {
  try {
    const data = await api.auth.me()
    user.value = data
  } catch (err) {
    console.error('Failed to fetch user data:', err)
  }
}

const saveChanges = async () => {
  uiStore.setScale(draft.scale)
  uiStore.setTheme(draft.theme)
  uiStore.setLang(draft.lang)
  
  localStorage.setItem('xoai_bio', draft.profile.bio)
  localStorage.setItem('xoai_provider', draft.intel.provider)
  localStorage.setItem('xoai_key', draft.intel.key)
  localStorage.setItem('xoai_bot_discord', draft.integrations.discord)
  localStorage.setItem('xoai_bot_telegram', draft.integrations.telegram)
  localStorage.setItem('xoai_bot_zalo', draft.integrations.zalo)
  
  try {
     await api.users.updateIntelligence({
       provider: draft.intel.provider,
       key: draft.intel.key
     })

     await api.users.updateIntegrations({
       discord: draft.integrations.discord,
       telegram: draft.integrations.telegram,
       zalo: draft.integrations.zalo
     })

     uiStore.notify('Settings synchronized with server.', 'success', 3000)
  } catch (err) {
     uiStore.notify('Partial save: ' + err.message, 'warning')
  }

  emit('close')
}

const triggerAvatarUpload = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = (e) => {
    const file = e.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (re) => {
        cropSrc.value = reader.result
        isCropping.value = true
      }
      reader.readAsDataURL(file)
    }
  }
  input.click()
}

const handleCropConfirm = (data) => {
  userAvatar.value = cropSrc.value 
  localStorage.setItem('xoai_avatar', cropSrc.value)
  isCropping.value = false
}

const handleKey = (e) => { if (e.key === 'Escape') emit('close') }

onMounted(() => { 
  window.addEventListener('keydown', handleKey)
  fetchUserData()
})
onUnmounted(() => { 
  window.removeEventListener('keydown', handleKey)
})
</script>

<style scoped>
.settings-overlay-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(8px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.settings-panel {
  width: 720px; height: 800px; max-height: 90vh; padding: 40px;
  display: flex; flex-direction: column; 
  background: var(--bg-glass);
  backdrop-filter: blur(40px);
  border: 1px solid var(--border-strong);
  border-radius: 32px;
  gap: 32px;
  position: relative;
  animation: modalIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes modalIn {
  from { opacity: 0; transform: translateY(20px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.close-btn-top {
  position: absolute; top: 32px; right: 32px;
  background: transparent; border: none; color: var(--text-secondary);
  font-size: 24px; cursor: pointer; transition: color 0.2s;
}
.close-btn-top:hover { color: var(--mango-primary); }

.panel-header { flex-shrink: 0; display: flex; flex-direction: column; gap: 20px; }
.user-brief { display: flex; align-items: center; gap: 20px; }
.avatar-hub {
  position: relative; width: 64px; height: 64px;
  border-radius: 18px; overflow: hidden; border: 2px solid var(--border-subtle);
  cursor: pointer;
}
.avatar-hub img { width: 100%; height: 100%; object-fit: cover; }
.avatar-hub .overlay {
  position: absolute; bottom: 0; width: 100%; height: 24px;
  background: rgba(0,0,0,0.6); color: white; font-size: 11px;
  display: flex; align-items: center; justify-content: center; opacity: 0;
}
.avatar-hub:hover .overlay { opacity: 1; }

.info h3 { margin: 0; font-size: 1.25rem; color: var(--text-primary); }
.info p { margin: 0; font-size: 0.9rem; opacity: 0.5; color: var(--text-primary); }

.quota-badge { font-size: 12px; display: flex; flex-direction: column; gap: 8px; color: var(--text-primary); }
.progress-bar { height: 6px; background: rgba(0,0,0,0.1); border-radius: 3px; }
.progress-bar .fill { height: 100%; background: var(--mango-primary); border-radius: 3px; }

.tabs-nav { display: flex; gap: 12px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px; }
.tabs-nav button {
  background: transparent; border: none; color: var(--text-secondary);
  font-size: 13px; padding: 6px 12px; cursor: pointer; opacity: 0.6; font-weight: 600;
  transition: all 0.2s;
}
.tabs-nav button.active { color: var(--mango-primary); opacity: 1; border-bottom: 2px solid var(--mango-primary); }

.tab-content { flex: 1; overflow-y: auto; padding-right: 12px; }
.form-group { display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px; }
.form-group label { font-size: 11px; text-transform: uppercase; font-weight: 800; opacity: 0.4; color: var(--text-primary); letter-spacing: 0.5px; }

input, select, textarea {
  background: rgba(var(--bg-rgb), 0.05); border: 1px solid var(--border-subtle);
  padding: 12px 16px; border-radius: 12px; color: var(--text-primary); font-size: 14px; outline: none;
  transition: all 0.2s; width: 100%;
}
input:focus, select:focus, textarea:focus { border-color: var(--mango-primary); background: rgba(var(--bg-rgb), 0.08); }

select option { background: var(--bg-primary); color: var(--text-primary); }

.scale-ctrl { display: flex; align-items: center; gap: 16px; }
.scale-ctrl button { 
  width: 36px; height: 36px; border-radius: 10px; border: 1px solid var(--border-subtle); 
  background: transparent; color: var(--text-primary); cursor: pointer; font-size: 18px;
  transition: all 0.2s;
}
.scale-ctrl button:hover { border-color: var(--mango-primary); color: var(--mango-primary); }
.scale-ctrl span { font-weight: 700; font-size: 16px; color: var(--text-primary); min-width: 60px; text-align: center; }

.key-input { display: flex; gap: 12px; }
.key-input input { flex: 1; }
.key-input button { background: none; border: none; color: var(--text-primary); cursor: pointer; font-size: 18px; }

.panel-footer { padding-top: 24px; border-top: 1px solid var(--border-subtle); }
.save-btn { width: 100%; padding: 16px !important; font-size: 16px !important; }

/* Custom scrollbar */
.scrollable::-webkit-scrollbar { width: 6px; }
.scrollable::-webkit-scrollbar-track { background: transparent; }
.scrollable::-webkit-scrollbar-thumb { background: rgba(var(--text-rgb), 0.1); border-radius: 3px; }
.scrollable::-webkit-scrollbar-thumb:hover { background: rgba(var(--text-rgb), 0.2); }
</style>
