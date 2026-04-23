<template>
  <div class="login-page">
    <div class="login-card glass-panel">
      <div class="brand">
        <span class="mango-text">XO</span>AI
      </div>
      <h2>{{ $t('auth.login.title') }}</h2>
      <form @submit.prevent="handleLogin">
        <div v-if="error" class="error-banner">{{ error }}</div>
        <div class="input-group">
          <label>{{ $t('auth.login.identifier') }}</label>
          <input v-model="identifier" type="text" placeholder="user_name" required />
        </div>
        <div class="input-group">
          <label>{{ $t('auth.login.password') }}</label>
          <input v-model="password" type="password" placeholder="••••••••" required />
        </div>
        <button class="mango-button" :disabled="loading">
          {{ loading ? $t('auth.login.loading') : $t('auth.login.submit') }}
        </button>
      </form>
      <div class="auth-footer">
        {{ $t('auth.login.no_account') }} <router-link to="/register">{{ $t('auth.login.register_link') }}</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../services/api'
import { setPrimaryToken, setRefreshToken } from '../services/session'

const identifier = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const router = useRouter()

const handleLogin = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await api.auth.login(identifier.value, password.value)
    setPrimaryToken(data.access_token)
    setRefreshToken(data.refresh_token)
    router.push('/chat')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Removed illegal import */
</style>
