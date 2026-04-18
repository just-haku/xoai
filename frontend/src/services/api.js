/* API Service — Frontend-to-Backend communication */

import { getActiveToken } from './session'

const API_BASE = '/api'

const parseErrorResponse = async (res) => {
    const error = await res.json().catch(() => ({}))
    throw new Error(error.detail || 'Request failed')
}

export const api = {
    async request(endpoint, options = {}) {
        const headers = { ...options.headers }
        
        // Only set Content-Type if not already set and body is not FormData
        if (!(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json'
        }

        const token = getActiveToken()
        if (token) headers['Authorization'] = `Bearer ${token}`

        const res = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        })

        if (!res.ok) {
            await parseErrorResponse(res)
        }

        return res.json()
    },

    authHeaders() {
        const token = getActiveToken()
        return token ? { Authorization: `Bearer ${token}` } : {}
    },

    async requestText(endpoint, options = {}) {
        const headers = { ...options.headers, ...api.authHeaders() }
        const res = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        })
        if (!res.ok) {
            await parseErrorResponse(res)
        }
        return res.text()
    },

    async requestBlob(endpoint, options = {}) {
        const headers = { ...options.headers, ...api.authHeaders() }
        const res = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        })
        if (!res.ok) {
            await parseErrorResponse(res)
        }
        return res.blob()
    },

    auth: {
        login: (identifier, password) => api.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ identifier, password }),
        }),
        register: (data) => api.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        me: () => api.request('/auth/me'),
    },

    users: {
        updateIntegrations: (data) => api.request('/users/integrations', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),
        setWorkChat: (work_chat_id) => api.request('/users/work_chat', {
            method: 'PUT',
            body: JSON.stringify({ work_chat_id }),
        }),
        updateIntelligence: (data) => api.request('/users/intelligence', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),
        updateProfile: (data) => api.request('/users/profile', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),
        changePassword: (data) => api.request('/users/change-password', {
            method: 'POST',
            body: JSON.stringify(data),
        })
    },

    admin: {
        listUsers: () => api.request('/users/'),
        stats: () => api.request('/admin/stats'),
        getSettings: () => api.request('/admin/settings'),
        getSetting: (key) => api.request(`/admin/settings/${key}`),
        updateSetting: (key, value) => api.request('/admin/settings', {
            method: 'PUT',
            body: JSON.stringify({ key, value }),
        }),
        fetchModels: (data) => api.request('/admin/settings/intelligence/models', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        updateQuota: (userId, limitBytes) => api.request(`/admin/users/${userId}/quota`, {
            method: 'PUT',
            body: JSON.stringify({ limit_bytes: limitBytes }),
        }),
        createProxySession: (userId) => api.request(`/admin/users/${userId}/proxy-session`, {
            method: 'POST',
        }),
        listQueryRuns: () => api.request('/admin/query-runs'),
        getQueryRun: (queryId) => api.request(`/admin/query-runs/${queryId}`),
        listExperienceInsights: () => api.request('/admin/experience/insights'),
        listExperienceLessons: () => api.request('/admin/experience/lessons'),
        listExperienceConsolidations: () => api.request('/admin/experience/consolidations'),
        consolidateExperienceLesson: (lessonId, data) => api.request(`/admin/experience/lessons/${lessonId}/consolidate`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        listPromptCandidates: () => api.request('/admin/prompt-candidates'),
        evaluatePromptCandidate: (candidateId) => api.request(`/admin/prompt-candidates/${candidateId}/evaluate`, {
            method: 'POST',
        }),
        benchmarkPromptCandidate: (candidateId) => api.request(`/admin/prompt-candidates/${candidateId}/benchmark`, {
            method: 'POST',
        }),
        listPromptCandidateBenchmarks: (candidateId) => api.request(`/admin/prompt-candidates/${candidateId}/benchmarks`),
        promotePromptCandidate: (candidateId) => api.request(`/admin/prompt-candidates/${candidateId}/promote`, {
            method: 'POST',
        }),
        rejectPromptCandidate: (candidateId) => api.request(`/admin/prompt-candidates/${candidateId}/reject`, {
            method: 'POST',
        }),
        listPromptVersions: () => api.request('/admin/prompt-versions'),
        getPromptVersion: (versionId) => api.request(`/admin/prompt-versions/${versionId}`),
        rollbackPromptVersion: (versionId) => api.request(`/admin/prompt-versions/${versionId}/rollback`, {
            method: 'POST',
        }),
        listPrompts: () => api.request('/admin/prompts'),
        createPromptVersion: (role, data) => api.request(`/admin/prompts/${role}/versions`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        activatePromptVersion: (versionId) => api.request(`/admin/prompts/versions/${versionId}/activate`, {
            method: 'POST',
        }),
        getPromptDiff: (versionId) => api.request(`/admin/prompts/versions/${versionId}/diff`),
        listAgentProfiles: () => api.request('/admin/agent-profiles'),
        saveAgentProfile: (data) => api.request('/admin/agent-profiles', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        updateAgentProfile: (agentKey, data) => api.request(`/admin/agent-profiles/${agentKey}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),
        deleteAgentProfile: (agentKey) => api.request(`/admin/agent-profiles/${agentKey}`, {
            method: 'DELETE',
        }),
        runStorageGc: (dryRun = true) => api.request('/admin/storage-gc/run', {
            method: 'POST',
            body: JSON.stringify({ dry_run: dryRun }),
        }),
        // Scheduler CRUD
        listScheduledTasks: () => api.request('/admin/scheduled-tasks'),
        getScheduledTask: (taskId) => api.request(`/admin/scheduled-tasks/${taskId}`),
        createScheduledTask: (data) => api.request('/admin/scheduled-tasks', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        updateScheduledTask: (taskId, data) => api.request(`/admin/scheduled-tasks/${taskId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),
        toggleScheduledTask: (taskId, enabled) => api.request(`/admin/scheduled-tasks/${taskId}/toggle`, {
            method: 'PATCH',
            body: JSON.stringify({ enabled }),
        }),
        deleteScheduledTask: (taskId) => api.request(`/admin/scheduled-tasks/${taskId}`, {
            method: 'DELETE',
        }),
        listTaskRuns: (taskId) => api.request(`/admin/scheduled-tasks/${taskId}/runs`),
        // Engram Compaction
        runEngramCompaction: (data = {}) => api.request('/admin/engram-compaction/run', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
    },

    mcp: {
        list: () => api.request('/mcp/'),
        create: (data) => api.request('/mcp/', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        update: (serverId, data) => api.request(`/mcp/${serverId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),
        delete: (serverId) => api.request(`/mcp/${serverId}`, {
            method: 'DELETE',
        }),
        refresh: (serverId) => api.request(`/mcp/${serverId}/refresh`, {
            method: 'POST',
        }),
    },

    workspace: {
        listFiles: () => api.request('/workspace/files'),
        initUpload: (data) => api.request('/workspace/files/upload/init', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        uploadChunk: (uploadId, chunkIndex, blob, filename = 'chunk.bin') => {
            const formData = new FormData()
            formData.append('file', new File([blob], filename))
            return fetch(`${API_BASE}/workspace/files/upload/${uploadId}/chunk/${chunkIndex}`, {
                method: 'PUT',
                headers: api.authHeaders(),
                body: formData,
            }).then(async res => {
                if (!res.ok) {
                    const error = await res.json().catch(() => ({}))
                    throw new Error(error.detail || 'Chunk upload failed')
                }
                return res.json()
            })
        },
        completeUpload: (uploadId, data = {}) => api.request(`/workspace/files/upload/${uploadId}/complete`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        abortUpload: (uploadId) => api.request(`/workspace/files/upload/${uploadId}`, {
            method: 'DELETE',
        }),
        uploadFile: async (file, path = '', onProgress = null) => {
            const fallbackChunkSize = 8 * 1024 * 1024
            const requestedChunks = Math.max(1, Math.ceil(file.size / fallbackChunkSize))
            const init = await api.workspace.initUpload({
                path,
                filename: file.name,
                total_size: file.size,
                total_chunks: requestedChunks,
                mime_type: file.type || 'application/octet-stream',
            })
            const chunkSize = init.chunk_size || fallbackChunkSize
            const totalChunks = init.total_chunks || requestedChunks
            let uploadedBytes = 0
            try {
                for (let index = 0; index < totalChunks; index += 1) {
                    const start = index * chunkSize
                    if (start >= file.size) break
                    const end = Math.min(file.size, start + chunkSize)
                    const chunk = file.slice(start, end)
                    await api.workspace.uploadChunk(init.upload_id, index, chunk, `${file.name}.part`)
                    uploadedBytes += chunk.size
                    if (onProgress) onProgress({ uploadedBytes, totalBytes: file.size })
                }
                return await api.workspace.completeUpload(init.upload_id)
            } catch (error) {
                await api.workspace.abortUpload(init.upload_id).catch(() => {})
                throw error
            }
        },
    }
}
