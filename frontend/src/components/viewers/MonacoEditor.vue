<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as monaco from 'monaco-editor'

const props = defineProps({
  modelValue: String,
  language: String,
  readOnly: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'save'])

const container = ref(null)
let editor = null

onMounted(() => {
  if (container.value) {
    editor = monaco.editor.create(container.value, {
      value: props.modelValue,
      language: props.language || 'javascript',
      theme: 'vs-dark',
      automaticLayout: true,
      readOnly: props.readOnly,
      fontSize: 14,
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      minimap: { enabled: true },
      scrollBeyondLastLine: false,
      roundedSelection: true,
      padding: { top: 20, bottom: 20 }
    })

    editor.onDidChangeModelContent(() => {
      emit('update:modelValue', editor.getValue())
    })

    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      emit('save')
    })
  }
})

onUnmounted(() => {
  if (editor) editor.dispose()
})

watch(() => props.modelValue, (newVal) => {
  if (editor && newVal !== editor.getValue()) {
    editor.setValue(newVal)
  }
})

watch(() => props.language, (newLang) => {
  if (editor) {
    const model = editor.getModel()
    if (model) monaco.editor.setModelLanguage(model, newLang)
  }
})
</script>

<template>
  <div class="monaco-wrapper">
    <div ref="container" class="monaco-container"></div>
  </div>
</template>

<style scoped>
.monaco-wrapper {
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: #1e1e1e;
}
.monaco-container {
  height: 100%;
  width: 100%;
}
</style>
