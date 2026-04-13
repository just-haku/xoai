<template>
  <div class="share-page">
    <div class="share-card glass-panel">
      <header class="share-header">
        <h1>Share Insight</h1>
        <p>Generate a secure link to share your chat or workspace artifacts.</p>
      </header>

      <div class="share-content">
        <div class="share-item glass-panel">
          <div class="info">
            <strong>Current Chat</strong>
            <span>Discovery Session 1</span>
          </div>
          <button class="mango-button small">Generate Link</button>
        </div>

        <div class="share-item glass-panel">
          <div class="info">
            <strong>Workspace Artifacts</strong>
            <span>src/main.py</span>
          </div>
          <button class="mango-button small">Generate Link</button>
        </div>
      </div>

      <footer class="share-footer">
        <div class="security-info">
          <span>🔒 End-to-end encrypted sharing</span>
          <span>⏳ Links expire in 24h</span>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.share-page {
  padding: 80px 20px;
  display: flex;
  justify-content: center;
}

.share-card {
  width: 100%;
  max-width: 600px;
  padding: 40px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.share-header h1 { font-size: 2rem; }
.share-header p { opacity: 0.6; margin-top: 8px; }

.share-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.share-item {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.share-item .info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.share-item .info span {
  font-size: 13px;
  opacity: 0.6;
}

.share-footer {
  border-top: 1px solid var(--border-subtle);
  padding-top: 24px;
}

.security-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  opacity: 0.5;
}

.mango-button.small {
  padding: 8px 16px;
  font-size: 13px;
}
</style>
