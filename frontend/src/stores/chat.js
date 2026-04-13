import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
    const messages = ref([])
    const activeConversationId = ref(null)
    const isStreaming = ref(false)
    const ws = ref(null)

    const connect = (conversationId) => {
        activeConversationId.value = conversationId
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        // Detect if we are in a local dev environment using ports or localhost hostname
        const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        const isDevPort = window.location.port === '3080' || window.location.port === '3000'
        
        const wsHost = (isLocalHost && isDevPort) ? `${window.location.hostname}:8080` : window.location.host
        const wsUrl = `${protocol}//${wsHost}/ws/chat`
        ws.value = new WebSocket(wsUrl)

        ws.value.onopen = () => {
            console.log('Chat WebSocket connected')
            ws.value.send(JSON.stringify({
                token: localStorage.getItem('xoai_token'),
                conversation_id: conversationId
            }))
        }

        ws.value.onmessage = (event) => {
            const data = JSON.parse(event.data)
            if (data.type === 'content') {
                // Appending to the last message if it's from the assistant
                const lastMsg = messages.value[messages.value.length - 1]
                if (lastMsg && lastMsg.role === 'assistant') {
                    lastMsg.content += data.content
                } else {
                    messages.value.push({ role: 'assistant', content: data.content })
                }
            } else if (data.type === 'tool_start') {
                // Handle tool status in ToolCog
            }
        }
    }

    const sendMessage = (text) => {
        if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return

        messages.value.push({ role: 'user', content: text })
        ws.value.send(JSON.stringify({ text }))
    }

    return { messages, isStreaming, connect, sendMessage }
})
