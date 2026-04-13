<template>
  <div class="register-page">
    <div class="login-card glass-panel">
      <div class="brand">
        <span class="mango-text">XO</span>AI
      </div>
      <h2>Join the Platform</h2>
      <p class="status-tip">Your account will require admin approval after registration.</p>
      
      <form @submit.prevent="handleRegister">
        <div class="input-group">
          <label>Full Name</label>
          <input v-model="name" type="text" placeholder="John Doe" required />
        </div>
        <div class="input-group">
          <label>Email</label>
          <input v-model="email" type="email" placeholder="john@example.com" required />
        </div>
        <div class="input-group">
          <label>Password</label>
          <input v-model="password" type="password" placeholder="••••••••" required />
        </div>
        <button class="mango-button" :disabled="loading">
          {{ loading ? 'Creating Account...' : 'Register' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../services/api'

const name = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const router = useRouter()

const handleRegister = async () => {
  loading.value = true
  try {
    await api.auth.register({ name: name.value, email: email.value, password: password.value })
    alert('Registration successful! Please wait for admin approval.')
    router.push('/login')
  } catch (e) {
    alert(e.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
@import './LoginView.vue'; /* Reuse styles */

.status-tip {
  font-size: var(--font-size-sm);
  color: var(--mango-primary);
  margin-bottom: var(--spacing-2);
}
</style>
