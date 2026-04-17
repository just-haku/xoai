import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useUIStore = defineStore('ui', () => {
  const theme = ref(localStorage.getItem('xoai_theme') || 'light')
  const color = ref(localStorage.getItem('xoai_color') || 'xoai')
  const pastel = ref(localStorage.getItem('xoai_pastel') === 'true')
  const lang = ref(localStorage.getItem('xoai_lang') || 'en')
  const scale = ref(parseFloat(localStorage.getItem('xoai_scale')) || 1.0)
  const showSettings = ref(false)
  const showSupport = ref(false)
  const layout = ref(localStorage.getItem('xoai_layout') || 'chat-only') // 'chat-only', 'split'
  const windows = ref(JSON.parse(localStorage.getItem('xoai_windows')) || {
    chat: { floating: false, minimized: false, x: 50, y: 50, w: 900, h: 600, order: 1 },
    workspace: { floating: true, minimized: false, x: 100, y: 100, w: 320, h: 450, order: 2 }
  })

  // Global Notifications (Top-Right)
  const notifications = ref([])

  const notify = (message, type = 'info', duration = 5000) => {
    const id = Math.random().toString(36).substring(2, 9)
    notifications.value.push({ id, message, type })
    if (duration > 0) {
      setTimeout(() => removeNotification(id), duration)
    }
    return id
  }

  const removeNotification = (id) => {
    notifications.value = notifications.value.filter(n => n.id !== id)
  }

  // Specialized Notice/Input Modal (Centered)
  const notice = ref({
    visible: false,
    type: 'info',
    title: '',
    message: '',
    inputPlaceholder: 'Enter value...',
    showCancel: false,
    callback: null
  })

  const closeNotice = () => {
    if (notice.value.visible && notice.value.callback) {
      // If closing without submit, send false to resolve confirm/prompt as cancelled
      notice.value.callback(false)
    }
    notice.value.visible = false
    // Clear callback after use to prevent double-firing
    notice.value.callback = null
  }

  const handleSubmit = (value) => {
    if (notice.value.callback) {
      notice.value.callback(value)
      // Prevent closeNotice from firing it again with false
      notice.value.callback = null
    }
    closeNotice()
  }

  const confirm = (title, message, type = 'warning') => {
    return new Promise((resolve) => {
      notice.value = {
        visible: true,
        type,
        title,
        message,
        requiresInput: false,
        showCancel: true,
        callback: (resp) => resolve(resp !== false)
      }
    })
  }

  const prompt = (title, message, placeholder = '') => {
    return new Promise((resolve) => {
      notice.value = {
        visible: true,
        type: 'info',
        title,
        message,
        requiresInput: true,
        inputPlaceholder: placeholder,
        showCancel: true,
        callback: (val) => resolve(val)
      }
    })
  }

  const setTheme = (val) => {
    theme.value = val
    apply()
  }

  const setColor = (val) => {
    color.value = val
    apply()
  }

  const setPastel = (val) => {
    pastel.value = val
    apply()
  }

  const setLang = (val) => {
    lang.value = val
    localStorage.setItem('xoai_lang', val)
    import('../i18n').then(module => {
      module.default.global.locale.value = val
    })
  }

  const setScale = (val) => {
    scale.value = Math.min(1.5, Math.max(0.8, val))
    apply()
  }

  const setLayout = (val) => {
    layout.value = val
    localStorage.setItem('xoai_layout', val)
  }

  const updateWindow = (id, state) => {
    windows.value[id] = { ...windows.value[id], ...state }
    localStorage.setItem('xoai_windows', JSON.stringify(windows.value))
  }

  const resetWindows = () => {
    windows.value = {
      chat: { floating: false, minimized: false, x: 50, y: 50, w: 900, h: 600, order: 1 },
      workspace: { floating: true, minimized: false, x: 100, y: 100, w: 320, h: 450, order: 2 }
    }
    layout.value = 'split'
    localStorage.setItem('xoai_windows', JSON.stringify(windows.value))
    localStorage.setItem('xoai_layout', 'split')
  }

  const maximizeAll = () => {
    Object.keys(windows.value).forEach(id => {
      windows.value[id].floating = false
      windows.value[id].minimized = false
    })
    layout.value = 'split'
    localStorage.setItem('xoai_windows', JSON.stringify(windows.value))
    localStorage.setItem('xoai_layout', 'split')
  }

  const minimizeAll = () => {
    Object.keys(windows.value).forEach(id => {
      windows.value[id].minimized = true
    })
    localStorage.setItem('xoai_windows', JSON.stringify(windows.value))
  }

  const apply = () => {
    if (!document?.documentElement) return
    document.documentElement.setAttribute('data-theme', theme.value)
    document.documentElement.setAttribute('data-color', color.value)
    document.documentElement.setAttribute('data-pastel', pastel.value)
    document.documentElement.style.setProperty('--ui-scale', scale.value)
    document.documentElement.style.fontSize = `${16 * scale.value}px`
    localStorage.setItem('xoai_scale', scale.value)
    localStorage.setItem('xoai_theme', theme.value)
    localStorage.setItem('xoai_color', color.value)
    localStorage.setItem('xoai_pastel', pastel.value)
  }

  return { 
    theme, color, pastel, lang, scale, showSettings, showSupport, layout, windows, notice,
    notifications,
    setTheme, setColor, setPastel, setLang, setScale, setLayout, updateWindow, resetWindows, maximizeAll, minimizeAll,
    apply, notify, removeNotification, closeNotice, handleSubmit, confirm, prompt 
  }
})
