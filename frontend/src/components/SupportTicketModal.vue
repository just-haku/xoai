<template>
  <div v-if="show" class="support-overlay" @click.self="$emit('close')">
    <div class="support-modal glass-panel shadow-premium">
      <div class="modal-header">
        <div class="title-group">
          <svg viewBox="0 0 24 24" class="icon"><path d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4A2,2 0 0,0 20,2Z"/></svg>
          <h2>{{ $t('support.title') }}</h2>
        </div>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <p class="description">
          {{ $t('support.description') }}
        </p>

        <div class="form-group">
          <label>{{ $t('support.type') }}</label>
          <CSelect 
            v-model="category" 
            :options="categoryOptions"
          />
        </div>

        <div class="form-group">
          <label>{{ $t('support.subject') }}</label>
          <input 
            v-model="subject" 
            :placeholder="$t('support.subject_placeholder')" 
            class="xoai-input"
          />
        </div>

        <div class="form-group">
          <label>{{ $t('support.message') }}</label>
          <textarea 
            v-model="message" 
            :placeholder="$t('support.placeholder')" 
            class="xoai-input"
            rows="5"
          ></textarea>
        </div>
      </div>

      <div class="modal-footer">
        <button class="cancel-btn" @click="$emit('close')">{{ $t('actions.cancel') }}</button>
        <button 
          class="submit-btn mango-button" 
          @click="submitTicket" 
          :disabled="loading || !message"
        >
          {{ loading ? $t('actions.sending') : $t('support.send') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUIStore } from '../stores/ui'
import { api } from '../services/api'
import CSelect from './common/CSelect.vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  show: Boolean
})

const emit = defineEmits(['close'])
const uiStore = useUIStore()
const { t } = useI18n()

const category = ref('others')
const subject = ref('')
const message = ref('')
const loading = ref(false)

const categoryOptions = computed(() => [
  { label: t('support.types.feature_request'), value: 'feature_request' },
  { label: t('support.types.feature_error'), value: 'feature_error' },
  { label: t('support.types.security_error'), value: 'security_error' },
  { label: t('support.types.others'), value: 'others' }
])

const submitTicket = async () => {
  loading.value = true
  try {
    await api.post('/tickets/', {
      category: category.value,
      subject: subject.value || '(No Subject)',
      message: message.value
    })
    
    uiStore.notify(t('support.success'), 'success')
    message.value = ''
    subject.value = ''
    emit('close')
  } catch (err) {
    uiStore.notify(t('support.error'), 'error')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.support-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  backdrop-filter: blur(12px); z-index: 10000;
  display: flex; align-items: center; justify-content: center;
}

.support-modal {
  width: 520px; padding: 40px; border-radius: 28px;
  background: var(--bg-glass); border: 1px solid var(--border-strong);
  display: flex; flex-direction: column; gap: 24px;
  animation: modalIn 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes modalIn {
  from { opacity: 0; transform: translateY(30px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.modal-header { display: flex; justify-content: space-between; align-items: center; }
.title-group { display: flex; align-items: center; gap: 16px; }
.title-group h2 { margin: 0; font-size: 1.5rem; color: var(--mango-primary); font-weight: 800; }
.title-group .icon { width: 28px; fill: var(--mango-primary); }

.close-btn { background: none; border: none; color: var(--text-secondary); font-size: 24px; cursor: pointer; transition: color 0.2s; }
.close-btn:hover { color: var(--mango-primary); }

.description { font-size: 14px; opacity: 0.6; line-height: 1.6; color: var(--text-primary); }

.form-group { display: flex; flex-direction: column; gap: 10px; }
.form-group label { font-size: 11px; text-transform: uppercase; font-weight: 800; opacity: 0.4; letter-spacing: 0.5px; color: var(--text-primary); }

.xoai-input {
  background: rgba(var(--bg-rgb), 0.05); border: 1px solid var(--border-subtle);
  padding: 14px; border-radius: 14px; color: var(--text-primary); font-size: 14px; outline: none;
  transition: all 0.2s; width: 100%;
}
.xoai-input:focus { border-color: var(--mango-primary); background: rgba(var(--bg-rgb), 0.08); }

select option {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.modal-footer { display: flex; justify-content: flex-end; gap: 16px; margin-top: 12px; }
.cancel-btn { background: transparent; border: none; color: var(--text-secondary); cursor: pointer; font-size: 15px; font-weight: 600; }
.cancel-btn:hover { color: var(--text-primary); }
.submit-btn { padding: 12px 32px; font-size: 15px !important; }
</style>
