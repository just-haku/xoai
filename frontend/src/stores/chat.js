import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getActiveToken } from '../services/session'
import { loadCachedConversation, saveCachedConversation } from '../services/chatCache'

export const useChatStore = defineStore('chat', () => {
    const messages = ref([])
    const conversations = ref([
        { id: 'omni', title: 'Work Chat', isOmni: true }
    ])
    const activeConversationId = ref('omni')
    const isStreaming = ref(false)
    const ws = ref(null)
    const channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('xoai_chat_sync') : null
    const omniChannelId = 'omni'
    const currentChatTitle = computed(() => {
        const current = conversations.value.find((item) => item.id === activeConversationId.value)
        return current?.title || 'New Chat'
    })

    const persistConversationState = async () => {
        await saveCachedConversation(activeConversationId.value, {
            messages: messages.value,
            conversations: conversations.value,
        }).catch(() => {})
    }

    const hydrateConversation = async (conversationId) => {
        const cached = await loadCachedConversation(conversationId).catch(() => null)
        if (!cached) return
        messages.value = Array.isArray(cached.messages) ? cached.messages : []
        if (Array.isArray(cached.conversations) && cached.conversations.length) {
            conversations.value = cached.conversations
        }
    }

    const broadcast = (payload) => {
        if (!channel) return
        channel.postMessage(payload)
    }

    if (channel) {
        channel.onmessage = (event) => {
            const data = event.data || {}
            if (data.type === 'chat_state' && data.conversationId === activeConversationId.value) {
                messages.value = data.messages || []
            }
            if (data.type === 'chat_list') {
                conversations.value = data.conversations || conversations.value
            }
        }
    }

    const connect = async (conversationId = omniChannelId) => {
        activeConversationId.value = conversationId
        await hydrateConversation(conversationId)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`
        if (ws.value && ws.value.readyState === WebSocket.OPEN) {
            ws.value.close()
        }
        ws.value = new WebSocket(wsUrl)

        ws.value.onopen = () => {
            ws.value.send(JSON.stringify({
                token: getActiveToken(),
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
                persistConversationState()
                broadcast({ type: 'chat_state', conversationId: activeConversationId.value, messages: messages.value })
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
                persistConversationState()
            } else if (data.type === 'conversation_state' && Array.isArray(data.messages)) {
                messages.value = data.messages
                persistConversationState()
            } else if (data.type === 'tool_start') {
                // Handle tool status in ToolCog
            }
        }

        ws.value.onclose = () => {
            isStreaming.value = false
        }
    }

    const stopGeneration = () => {
        if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
        ws.value.send(JSON.stringify({ type: 'abort' }))
        isStreaming.value = false
    }

    const sendMessage = async (text, files = []) => {
        if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return

        const clientMessageId = `client_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
        const messageData = {
            id: clientMessageId,
            role: 'user',
            content: text,
            files: files.map(f => ({ name: f.name, size: f.size, type: f.type })),
            pending: true,
        }

        messages.value.push(messageData)
        isStreaming.value = true
        await persistConversationState()
        broadcast({ type: 'chat_state', conversationId: activeConversationId.value, messages: messages.value })

        ws.value.send(JSON.stringify({ 
            type: 'message',
            text,
            attachments: files.map(f => f.name), // Simplified for the prototype, backend would handle real upload
            client_message_id: clientMessageId,
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
        persistConversationState()
    }

    const handleTriageAction = async ({ index, action, ticketId }) => {
        const msg = messages.value[index]
        msg.responded = true
        msg.response = action
        
        if (action === 'approve') {
            try {
                const response = await fetch(`/api/tickets/${ticketId}/approve`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${getActiveToken()}` }
                })
                if (!response.ok) throw new Error('Approval failed')
            } catch (err) {
                msg.responded = false
            }
        }
    }

    const createChat = () => {
        const id = 'chat_' + Math.random().toString(36).substr(2, 9)
        conversations.value.push({ id, title: 'New Chat', isOmni: false })
        broadcast({ type: 'chat_list', conversations: conversations.value })
        return id
    }

    const newChat = async () => {
        const id = createChat()
        await connect(id)
        return id
    }

    const loadChat = async (id) => {
        await connect(id)
    }

    const deleteChat = (id) => {
        if (id === omniChannelId) return
        conversations.value = conversations.value.filter(c => c.id !== id)
        if (activeConversationId.value === id) {
            connect(omniChannelId)
        }
        broadcast({ type: 'chat_list', conversations: conversations.value })
    }

    const setChatTitle = (id, title) => {
        const chat = conversations.value.find(c => c.id === id)
        if (chat) chat.title = title
        broadcast({ type: 'chat_list', conversations: conversations.value })
    }

    return { 
        messages, conversations, activeConversationId, isStreaming, omniChannelId, currentChatTitle,
        connect, sendMessage, stopGeneration, sendInputResponse, handleTriageAction,
        createChat, newChat, loadChat, deleteChat, setChatTitle
    }
})
