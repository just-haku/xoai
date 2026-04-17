import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            name: 'landing',
            component: () => import('../views/LandingView.vue')
        },
        {
            path: '/login',
            name: 'login',
            component: LoginView
        },
        {
            path: '/register',
            name: 'register',
            component: () => import('../views/RegisterView.vue')
        },
        {
            path: '/chat',
            name: 'chat-home',
            component: () => import('../views/ChatView.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/chat/:id',
            name: 'chat',
            component: () => import('../views/ChatView.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/workspace',
            name: 'workspace',
            component: () => import('../views/ChatView.vue'), // ChatView handles workspace mode too
            meta: { requiresAuth: true }
        },
        {
            path: '/server-settings',
            name: 'admin',
            component: () => import('../views/AdminDashboard.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/user-settings',
            name: 'user-settings',
            component: () => import('../views/UserSettingsView.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/view-file',
            name: 'file-viewer',
            component: () => import('../views/FileViewerPage.vue'),
            meta: { requiresAuth: true }
        }
    ]
})

router.beforeEach((to, from, next) => {
    const isAuthenticated = !!localStorage.getItem('xoai_token')
    
    if (to.meta.requiresAuth && !isAuthenticated) {
        next({ name: 'landing' })
    } else {
        next()
    }
})

export default router
