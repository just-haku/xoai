import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
    const messages = ref([])
    const conversations = ref([
        { id: 'omni', title: 'Work Chat', isOmni: true }
    ])
    const activeConversationId = ref('omni')
    const isStreaming = ref(false)
    const ws = ref(null)

    const connect = (conversationId = 'omni') => {
        activeConversationId.value = conversationId
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`
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
            } else if (data.type === 'input_required') {
                messages.value.push({
                    role: 'assistant',
                    type: 'input_required',
                    tool: data.tool,
                    args: data.args,
                    tc_id: data.tc_id,
                    responded: false
                })
                isStreaming.value = false
            } else if (data.type === 'tool_start') {
                // Handle tool status in ToolCog
            }
        }
    }

    const stopGeneration = () => {
        if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
        ws.value.send(JSON.stringify({ type: 'abort' }))
        isStreaming.value = false
    }

    const sendMessage = async (text, files = []) => {
        if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return

        const messageData = {
            role: 'user',
            content: text,
            files: files.map(f => ({ name: f.name, size: f.size, type: f.type }))
        }

        messages.value.push(messageData)
        isStreaming.value = true

        ws.value.send(JSON.stringify({ 
            type: 'message',
            text,
            attachments: files.map(f => f.name) // Simplified for the prototype, backend would handle real upload
        }))
    }

    const sendInputResponse = ({ index, response }) => {
        if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
        
        const msg = messages.value[index]
        msg.responded = true
        msg.response = response
        
        ws.value.send(JSON.stringify({
            type: 'input_response',
            response: response,
            tc_id: msg.tc_id
        }))

        if (response === 'deny') {
            isStreaming.value = false
        }
    }

    const handleTriageAction = async ({ index, action, ticketId }) => {
        const msg = messages.value[index]
        msg.responded = true
        msg.response = action
        
        if (action === 'approve') {
            try {
                const response = await fetch(`/api/tickets/${ticketId}/approve`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('xoai_token')}` }
                })
                if (!response.ok) throw new Error('Approval failed')
            } catch (err) {
                console.error('Failed to approve ticket:', err)
                msg.responded = false
            }
        }
    }

    const createChat = () => {
        const id = 'chat_' + Math.random().toString(36).substr(2, 9)
        conversations.value.push({ id, title: 'New Chat', isOmni: false })
        return id
    }

    const deleteChat = (id) => {
        if (id === 'omni') return // Cannot delete omni
        conversations.value = conversations.value.filter(c => c.id !== id)
        if (activeConversationId.value === id) {
            connect('omni')
        }
    }

    const setChatTitle = (id, title) => {
        const chat = conversations.value.find(c => c.id === id)
        if (chat) chat.title = title
    }

    return { 
        messages, conversations, activeConversationId, isStreaming, 
        connect, sendMessage, stopGeneration, sendInputResponse, handleTriageAction,
        createChat, deleteChat, setChatTitle
    }
})
