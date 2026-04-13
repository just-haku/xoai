/* API Service — Frontend-to-Backend communication */

const API_BASE = '/api'

export const api = {
    async request(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
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

    auth: {
        login: (email, password) => api.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        }),
        register: (data) => api.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        me: () => api.request('/auth/me'),
    },

    admin: {
        listUsers: () => api.request('/users/'),
        getSettings: () => api.request('/admin/settings'),
        updateSetting: (key, value) => api.request(`/admin/settings/${key}`, {
            method: 'POST',
            body: JSON.stringify({ value }),
        }),
    },

    workspace: {
        listFiles: () => api.request('/workspace/files'),
        uploadFile: (file) => {
            const formData = new FormData()
            formData.append('file', file)
            return fetch(`${API_BASE}/workspace/files/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('xoai_token')}`,
                },
                body: formData,
            }).then(res => res.json())
        }
    }
}
