import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useUIStore = defineStore('ui', () => {
  const theme = ref(localStorage.getItem('xoai_theme') || 'dark') // 'dark' or 'light'
  const color = ref(localStorage.getItem('xoai_color') || 'xoai') // 'dark', 'contrast', 'blue', 'green', 'yellow', 'xoai'
  const lang = ref(localStorage.getItem('xoai_lang') || 'en')
  const scale = ref(parseFloat(localStorage.getItem('xoai_scale')) || 1.0)
  const showSettings = ref(false)

  const setTheme = (val) => {
    theme.value = val
    localStorage.setItem('xoai_theme', val)
    apply()
  }

  const setColor = (val) => {
    color.value = val
    localStorage.setItem('xoai_color', val)
    apply()
  }

  const setLang = (val) => {
    lang.value = val
    localStorage.setItem('xoai_lang', val)
    // Update i18n instance
    import('../i18n').then(module => {
      module.default.global.locale.value = val
    })
  }

  const setScale = (val) => {
    scale.value = Math.min(1.5, Math.max(0.8, val))
    localStorage.setItem('xoai_scale', scale.value)
    apply()
  }

  const apply = () => {
    if (!document?.documentElement) return
    document.documentElement.setAttribute('data-theme', theme.value)
    document.documentElement.setAttribute('data-color', color.value)
    document.documentElement.style.setProperty('--ui-scale', scale.value)
    document.documentElement.style.fontSize = `${16 * scale.value}px`
    localStorage.setItem('xoai_scale', scale.value)
    localStorage.setItem('xoai_theme', theme.value)
    localStorage.setItem('xoai_color', color.value)
  }

  return { theme, color, lang, scale, showSettings, setTheme, setColor, setLang, setScale, apply }
})
