import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { login as apiLogin, fetchMe } from '@/api/auth'
import { canAccess } from '@/config/nav'

const TOKEN_KEY = 'zhengkao_admin_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const username = ref('')
  const role = ref('')
  const permissions = ref<string[]>([])

  const isSuperAdmin = computed(() => role.value === 'super_admin')

  function setToken(value: string) {
    token.value = value
    if (value) localStorage.setItem(TOKEN_KEY, value)
    else localStorage.removeItem(TOKEN_KEY)
  }

  async function login(user: string, password: string) {
    const data = await apiLogin(user, password)
    setToken(data.access_token)
    username.value = data.username
    role.value = data.role
    permissions.value = data.permissions || []
  }

  async function loadMe() {
    if (!token.value) return
    const me = await fetchMe()
    username.value = me.username
    role.value = me.role_code
    permissions.value = me.permissions || []
  }

  function logout() {
    setToken('')
    username.value = ''
    role.value = ''
    permissions.value = []
  }

  function hasPermission(...required: string[]) {
    if (isSuperAdmin.value) return true
    return canAccess(permissions.value, required)
  }

  return {
    token,
    username,
    role,
    permissions,
    isSuperAdmin,
    login,
    loadMe,
    logout,
    setToken,
    hasPermission,
  }
})
