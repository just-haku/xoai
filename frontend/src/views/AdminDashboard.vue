<template>
  <div class="admin-dashboard">
    <header class="dashboard-header glass-panel">
      <h1>Admin Control Center</h1>
      <div class="status-bar">
        <div class="status-item">
          <span class="dot green"></span> System Online
        </div>
      </div>
    </header>
    
    <div class="dashboard-grid">
      <section class="card glass-panel stats-card">
        <h3>Platform Overview</h3>
        <div class="stats-grid">
          <div class="stat">
            <span class="label">Total Users</span>
            <span class="value">1</span>
          </div>
          <div class="stat">
            <span class="label">Pending Approvals</span>
            <span class="value accent">0</span>
          </div>
          <div class="stat">
            <span class="label">Open Tickets</span>
            <span class="value">0</span>
          </div>
        </div>
      </section>
      
      <section class="card glass-panel settings-card">
        <h3>Agent Configurations</h3>
        <div class="settings-list">
          <div v-for="agent in agents" :key="agent.id" class="setting-item">
            <div class="agent-info">
              <strong>{{ agent.name }}</strong>
              <span>{{ agent.model }}</span>
            </div>
            <button class="edit-btn">Configure</button>
          </div>
        </div>
      </section>

      <section class="card glass-panel infrastructure-card">
        <h3>Infrastructure</h3>
        <div class="service-status">
          <div class="service">
            <span>MongoDB</span>
            <span class="tag success">Connected</span>
          </div>
          <div class="service">
            <span>Redis</span>
            <span class="tag success">Connected</span>
          </div>
          <div class="service">
            <span>Storage</span>
            <span class="tag">1.2GB / 100GB</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const agents = ref([
  { id: 'a0', name: 'Agent 0 (Supervisor)', model: 'gemini-1.5-pro' },
  { id: 'a1', name: 'Agent 1 (Architect)', model: 'gemini-1.5-pro' },
  { id: 'a2', name: 'Agent 2 (Executor)', model: 'gpt-4o' }
])
</script>

<style scoped>
.admin-dashboard {
  padding: var(--spacing-10);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-10);
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
  padding: var(--spacing-6) var(--spacing-8);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  opacity: 0.8;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.green {
  background: var(--success);
  box-shadow: 0 0 8px var(--success);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: var(--spacing-8);
}

.card {
  padding: var(--spacing-8);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

h3 {
  color: var(--mango-primary);
  font-size: var(--font-size-lg);
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: var(--spacing-2);
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-6);
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat .label {
  font-size: 12px;
  opacity: 0.6;
}

.stat .value {
  font-size: 24px;
  font-weight: 700;
}

.stat .value.accent {
  color: var(--mango-primary);
}

.settings-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
}

.agent-info {
  display: flex;
  flex-direction: column;
}

.agent-info span {
  font-size: 12px;
  opacity: 0.6;
}

.edit-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
}

.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 122, 0, 0.1);
  color: var(--mango-primary);
}

.tag.success {
  background: rgba(0, 255, 122, 0.1);
  color: var(--success);
}

.service-status {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.service {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
