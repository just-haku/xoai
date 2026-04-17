<template>
  <div class="register-page">
    <div class="login-card glass-panel">
      <div class="brand">
        <span class="mango-text">XO</span>AI
      </div>
      <h2>{{ $t('auth.register.title') }}</h2>
      <p class="status-tip">{{ $t('auth.register.approval_tip') }}</p>
      
      <form @submit.prevent="handleRegister">
        <div class="input-group">
          <label>{{ $t('auth.register.name') }}</label>
          <input v-model="name" type="text" placeholder="John Doe" required :disabled="loading" />
        </div>
        
        <div class="input-group">
          <label>{{ $t('auth.register.email') }}</label>
          <input v-model="email" type="email" placeholder="john@example.com" required :disabled="loading || isVerified" />
        </div>

        <div class="input-group">
          <label>{{ $t('auth.register.password') }}</label>
          <input v-model="password" type="password" placeholder="••••••••" required :disabled="loading" />
        </div>
        
        <button class="mango-button" :disabled="loading || !password || !name || !isEmailValid">
          {{ loading ? $t('auth.register.loading') : $t('auth.register.submit') }}
        </button>
      </form>
      <div class="auth-footer">
        {{ $t('auth.register.have_account') }} <router-link to="/login">{{ $t('auth.register.login_link') }}</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../services/api'

const name = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const router = useRouter()

const isEmailValid = computed(() => {
  return email.value.includes('@') && email.value.includes('.') && email.value.length > 5
})

const handleRegister = async () => {
  loading.value = true
  try {
    await api.auth.register({ name: name.value, email: email.value, password: password.value })
    alert('Registration successful. Check your email for the verification link, then wait for admin approval.')
    router.push('/login')
  } catch (e) {
    alert(e.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.verif-action-zone {
  margin-bottom: var(--spacing-4);
  text-align: center;
}
.verif-btn { 
  width: 100%;
  padding: 12px; 
  font-size: 14px; 
  font-weight: 700;
}
.verif-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  box-shadow: none;
}
.verif-label {
  display: flex;
  justify-content: space-between;
}
.error-text {
  color: var(--danger);
  font-size: 11px;
}
.verif-input {
  letter-spacing: 4px;
  font-family: monospace;
  font-size: 16px;
  text-align: center;
}
.success-badge {
  background: rgba(0, 255, 122, 0.1);
  color: var(--success);
  border: 1px solid rgba(0, 255, 122, 0.2);
  padding: 12px;
  border-radius: 8px;
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: var(--spacing-4);
}
.slide-down {
  animation: slideDown 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
