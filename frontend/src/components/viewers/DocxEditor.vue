<script setup>
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { watch, onMounted } from 'vue'

const props = defineProps({
  modelValue: String,
  readOnly: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'save'])

const editor = useEditor({
  content: props.modelValue,
  editable: !props.readOnly,
  extensions: [StarterKit],
  onUpdate: ({ editor }) => {
    emit('update:modelValue', editor.getHTML())
  }
})

watch(() => props.modelValue, (newVal) => {
  const isSame = editor.value.getHTML() === newVal
  if (isSame) return
  editor.value.commands.setContent(newVal, false)
})

onMounted(() => {
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault()
      emit('save')
    }
  })
})
</script>

<template>
  <div class="docx-editor">
    <div v-if="editor" class="tiptap-menu glass-panel shadow-premium">
      <button @click="editor.chain().focus().toggleBold().run()" :class="{ 'is-active': editor.isActive('bold') }">B</button>
      <button @click="editor.chain().focus().toggleItalic().run()" :class="{ 'is-active': editor.isActive('italic') }">I</button>
      <button @click="editor.chain().focus().toggleHeading({ level: 1 }).run()" :class="{ 'is-active': editor.isActive('heading', { level: 1 }) }">H1</button>
      <button @click="editor.chain().focus().toggleHeading({ level: 2 }).run()" :class="{ 'is-active': editor.isActive('heading', { level: 2 }) }">H2</button>
      <span class="divider"></span>
      <button @click="editor.chain().focus().toggleBulletList().run()" :class="{ 'is-active': editor.isActive('bulletList') }">List</button>
      <button @click="emit('save')" class="save-tiptap-btn">Save</button>
    </div>
    <div class="editor-viewport scrollable">
      <div class="tiptap-page shadow-premium">
        <EditorContent :editor="editor" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.docx-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f4f4f5;
  color: #1a1a1a;
}

.tiptap-menu {
  padding: 12px;
  background: white;
  border-bottom: 1px solid #e2e2e7;
  display: flex;
  gap: 8px;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 10;
}

.tiptap-menu button {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #e2e2e7;
  background: white;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  transition: all 0.2s;
}
.tiptap-menu button:hover { background: #f4f4f5; }
.tiptap-menu button.is-active { background: #1a1a1a; color: white; border-color: #1a1a1a; }

.divider { width: 1px; height: 16px; background: #e2e2e7; margin: 0 4px; }

.save-tiptap-btn { margin-left: auto; background: var(--mango-primary) !important; color: white !important; border: none !important; }

.editor-viewport {
  flex: 1;
  padding: 40px;
  overflow-y: auto;
}

.tiptap-page {
  background: white;
  width: 100%;
  max-width: 800px;
  min-height: 100%;
  margin: 0 auto;
  padding: 80px 100px;
  outline: none;
}

:deep(.ProseMirror) {
  outline: none;
  min-height: 100%;
  font-family: 'Inter', serif;
  font-size: 16px;
  line-height: 1.6;
}

:deep(.ProseMirror p) { margin-bottom: 1em; }
:deep(.ProseMirror h1) { font-size: 2em; margin-bottom: 0.5em; font-weight: 800; }
:deep(.ProseMirror h2) { font-size: 1.5em; margin-bottom: 0.5em; font-weight: 700; }
</style>
