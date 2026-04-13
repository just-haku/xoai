<template>
  <div class="login-page">
    <div class="login-card glass-panel">
      <div class="brand">
        <span class="mango-text">XO</span>AI
      </div>
      <h2>System Access</h2>
      <form @submit.prevent="handleLogin">
        <div class="input-group">
          <label>Email</label>
          <input v-model="email" type="email" placeholder="admin@xoai.io" required />
        </div>
        <div class="input-group">
          <label>Password</label>
          <input v-model="password" type="password" placeholder="••••••••" required />
        </div>
        <button class="mango-button" :disabled="loading">
          {{ loading ? 'Authenticating...' : 'Login' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const email = ref('')
const password = ref('')
const loading = ref(false)
const router = useRouter()

const handleLogin = async () => {
  loading.value = true
  // TODO: Implement API call
  setTimeout(() => {
    loading.value = false
    router.push('/')
  }, 1000)
}
</script>

<style scoped>
.login-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-4);
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: var(--spacing-8);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
  text-align: center;
}

.brand {
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -1px;
}

.mango-text {
  color: var(--mango-primary);
}

.input-group {
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  margin-bottom: var(--spacing-4);
}

label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

input {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-strong);
  color: var(--text-primary);
  padding: 0.75rem;
  border-radius: 8px;
  outline: none;
  transition: var(--transition-fast);
}

input:focus {
  border-color: var(--mango-primary);
}

button {
  width: 100%;
  margin-top: var(--spacing-2);
}
</style>
