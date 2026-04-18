/* API Service — Frontend-to-Backend communication */

const API_BASE = '/api'

export const api = {
    async request(endpoint, options = {}) {
        const headers = { ...options.headers }
        
        // Only set Content-Type if not already set and body is not FormData
        if (!(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json'
        }

        const token = localStorage.getItem('xoai_token')
        if (token) headers['Authorization'] = `Bearer ${token}`

        const res = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        })

        if (!res.ok) {
            const error = await res.json()
            throw new Error(error.detail || 'Request failed')
        }

        return res.json()
    },

    authHeaders() {
        const token = localStorage.getItem('xoai_token')
        return token ? { Authorization: `Bearer ${token}` } : {}
    },

    async requestText(endpoint, options = {}) {
        const headers = { ...options.headers, ...api.authHeaders() }
        const res = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        })
        if (!res.ok) {
            const error = await res.json().catch(() => ({}))
            throw new Error(error.detail || 'Request failed')
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
            const error = await res.json().catch(() => ({}))
            throw new Error(error.detail || 'Request failed')
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
        uploadFile: (file, path = '') => {
            const formData = new FormData()
            formData.append('file', file)
            return fetch(`${API_BASE}/workspace/files/upload?path=${encodeURIComponent(path)}`, {
                method: 'POST',
                headers: api.authHeaders(),
                body: formData,
            }).then(async res => {
                if (!res.ok) {
                    const error = await res.json().catch(() => ({}))
                    throw new Error(error.detail || 'Upload failed')
                }
                return res.json()
            })
        }
    }
}
