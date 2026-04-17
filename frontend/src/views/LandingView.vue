<template>
  <div class="landing-page">
    <!-- Hero Section -->
    <header class="hero">
      <nav class="top-nav">
        <div class="brand">XO<span class="mango-text">AI</span></div>
      </nav>

      <div class="hero-content">
        <h1 class="hero-title">{{ $t('landing.hero.title_main') }} <span class="gradient-text">{{ $t('landing.hero.title_accent') }}</span></h1>
        <p class="hero-subtitle">{{ $t('landing.hero.subtitle') }}</p>
        <div class="cta-group">
          <router-link to="/register" class="cta-button primary">{{ $t('landing.hero.cta') }}</router-link>
        </div>
      </div>
    </header>

    <footer class="landing-footer">
      <div class="footer-content max-width">
        <div class="brand">XO<span class="mango-text">AI</span></div>
        <p>&copy; {{ $t('landing.footer.copy') }}</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing-page {
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.hero {
  height: 80vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 0 40px;
  text-align: center;
}

.max-width {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.top-nav {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  padding: 40px 80px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 100;
}

.brand { font-size: 28px; font-weight: 900; letter-spacing: -1.5px; }

.nav-links { display: flex; gap: 40px; align-items: center; }
.nav-link { font-size: 14px; font-weight: 700; text-decoration: none; color: var(--text-secondary); transition: color 0.3s; }
.nav-link:hover { color: var(--mango-primary); }
.login-box { padding: 8px 16px; border: 1px solid var(--border-strong); border-radius: 8px; color: var(--text-primary); }

.hero-content {
  max-width: 900px;
  z-index: 10;
}

.hero-title {
  font-size: clamp(3rem, 8vw, 5rem);
  font-weight: 900;
  line-height: 1.1;
  margin-bottom: 24px;
  letter-spacing: -3px;
}

.gradient-text {
  background: var(--mango-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-subtitle {
  font-size: 1.25rem;
  opacity: 0.6;
  max-width: 650px;
  margin: 0 auto 48px;
  line-height: 1.5;
}

.cta-button {
  padding: 16px 40px;
  border-radius: 12px;
  font-weight: 800;
  font-size: 16px;
  text-decoration: none;
  display: inline-block;
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  background: var(--mango-gradient);
  color: #000;
  box-shadow: 0 15px 40px var(--mango-glow);
}

.cta-button:hover { transform: scale(1.05); }

.platform-brief {
  padding: 100px 40px;
  background: rgba(255,255,255,0.01);
}

.brief-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 60px;
}

.brief-item h3 {
  font-size: 20px;
  font-weight: 800;
  margin-bottom: 16px;
  color: var(--mango-primary);
}

.brief-item p {
  opacity: 0.6;
  line-height: 1.6;
}

.landing-footer {
  padding: 80px 40px;
  border-top: 1px solid var(--border-subtle);
  margin-top: auto;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-content p {
  opacity: 0.4;
  font-size: 14px;
  font-weight: 600;
}
</style>
