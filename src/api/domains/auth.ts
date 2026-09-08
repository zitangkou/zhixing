import * as d from '../_shared'
import { CURRENT_PRODUCT_KEY, LOCAL_PRODUCT_DEFAULTS } from '@/constants/product'

export const apiAuth = {
  getPublicConfig(): Promise<d.ApiRes<{ allowRegister: boolean; product: d.ProductPublicConfig }>> {
    if (d.isMock) {
      const product = LOCAL_PRODUCT_DEFAULTS[CURRENT_PRODUCT_KEY]
      return Promise.resolve({
        code: 0,
        data: {
          allowRegister: true,
          product: {
            key: CURRENT_PRODUCT_KEY,
            ...product,
            enabledModules: ['today', 'learning', 'quiz', 'profile'],
            tabs: [],
          },
        },
        message: 'ok',
      })
    }
    return d.request<{ allowRegister: boolean; product: d.ProductPublicConfig }>('/api/config', {
      auth: false,
    })
  },

  register(
    username: string,
    password: string,
    passwordConfirm: string,
  ): Promise<d.ApiRes<d.AuthResult>> {
    return d.isMock
      ? d.mockService.register(username, password)
      : d.request<d.AuthResult>('/api/auth/register', {
          method: 'POST',
          data: { username, password, passwordConfirm },
          auth: false,
        })
  },

  login(username: string, password: string): Promise<d.ApiRes<d.AuthResult>> {
    return d.isMock
      ? d.mockService.login(username, password)
      : d.request<d.AuthResult>('/api/auth/login', {
          method: 'POST',
          data: { username, password },
          auth: false,
        })
  },

  getUserMe(): Promise<d.ApiRes<d.UserMeData>> {
    return d.isMock ? d.mockService.getUserMe() : d.request<d.UserMeData>('/api/user/me')
  },

  updateProfile(data: {
    nickname?: string
    email?: string
    phone?: string
  }): Promise<d.ApiRes<d.UserMeData>> {
    return d.isMock
      ? d.mockService.updateProfile(data)
      : d.request<d.UserMeData>('/api/user/me', { method: 'PUT', data })
  },

  changePassword(data: {
    oldPassword: string
    newPassword: string
    newPasswordConfirm: string
  }): Promise<d.ApiRes<{ ok: boolean }>> {
    return d.isMock
      ? d.mockService.changePassword(data)
      : d.request<{ ok: boolean }>('/api/user/password', { method: 'POST', data })
  },

  uploadAvatar(filePath: string, file?: File): Promise<d.ApiRes<d.UserMeData>> {
    if (d.isMock) return d.mockService.uploadAvatar(filePath)
    return d.uploadFile<d.UserMeData>(`${d.BASE_URL}/api/user/avatar`, filePath, { file })
  },
}
