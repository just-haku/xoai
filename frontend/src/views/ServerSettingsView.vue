<template>
  <div class="settings-page server-settings">
    <header class="settings-header">
      <h1>Server Administration</h1>
      <p>Configure global platform defaults and manage system orchestration.</p>
    </header>

    <div class="settings-grid">
      <!-- Tri-Agent Keys -->
      <section class="settings-card glass-panel">
        <div class="section-header"><h3>🤖 Triad Orchestration Keys</h3></div>
        <p class="section-desc">These keys power the core agents (A0, A1, A2) for all users.</p>
        
        <div v-for="agent in triad" :key="agent.id" class="agent-key-item">
           <label>{{ agent.name }}</label>
           <div class="key-input-row">
              <input type="password" v-model="agent.apiKey" placeholder="System Key..." />
              <select v-model="agent.provider">
                <option value="gemini">Gemini</option>
                <option value="openai">OpenAI</option>
              </select>
           </div>
        </div>
        <button class="mango-button save-btn">Update Orchestrator</button>
      </section>

      <!-- Server Config -->
      <section class="settings-card glass-panel">
        <div class="section-header"><h3>⚙️ System Infrastructure</h3></div>
        <div class="setting-item">
           <label>SMTP Relay (Support Notifications)</label>
           <input type="text" placeholder="smtp.gmail.com" />
           <input type="password" placeholder="Relay Password" />
        </div>
        <div class="setting-item">
           <label>Platform Token Quota (Default)</label>
           <input type="number" value="1000000" />
        </div>
      </section>

      <!-- User Management -->
      <section class="settings-card glass-panel full-width">
        <div class="section-header"><h3>👥 User Management</h3></div>
        <table class="user-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.name }}</td>
              <td>{{ u.email }}</td>
              <td><span class="role-tag" :class="u.role">{{ u.role }}</span></td>
              <td><span class="status-dot" :class="u.status"></span> {{ u.status }}</td>
              <td>
                <button class="icon-btn">🚫</button>
                <button class="icon-btn">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

const triad = reactive([
  { id: 'a0', name: 'Agent 0 (Supervisor)', provider: 'gemini', apiKey: '' },
  { id: 'a1', name: 'Agent 1 (Architect)', provider: 'gemini', apiKey: '' },
  { id: 'a2', name: 'Agent 2 (Executor)', provider: 'openai', apiKey: '' }
])

const users = ref([
  { id: 1, name: 'Admin', email: 'admin@xoai.io', role: 'admin', status: 'active' },
  { id: 2, name: 'John Doe', email: 'john@example.com', role: 'user', status: 'pending' }
])
</script>

<style scoped>
.settings-page {
  padding: 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.full-width { grid-column: span 2; }

.agent-key-item {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.key-input-row {
  display: flex;
  gap: 12px;
}

.key-input-row input { flex: 1; }
.key-input-row select { width: 120px; }

.section-desc {
  font-size: 12px;
  opacity: 0.6;
  margin-bottom: 20px;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
}

.user-table th {
  text-align: left;
  padding: 12px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 12px;
  text-transform: uppercase;
  opacity: 0.5;
}

.user-table td {
  padding: 16px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.role-tag {
  font-size: 10px;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255,255,255,0.05);
}

.role-tag.admin { color: #0096ff; background: rgba(0, 150, 255, 0.1); }

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.status-dot.active { background: var(--success); }
.status-dot.pending { background: var(--mango-primary); }

.icon-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  margin-right: 8px;
  font-size: 16px;
}
</style>
