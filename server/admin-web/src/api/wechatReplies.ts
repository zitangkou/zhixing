import http, { getData } from './http'

export interface WechatPromotionEntry {
  id: string
  name: string
  pagePath: string
  enabled: boolean
  instruction: string
  fallbackText: string
}

export interface WechatKeywordRule {
  id: string
  name: string
  keywords: string[]
  matchType: 'exact' | 'contains'
  responseText: string
  enabled: boolean
  entryId?: string
  priority: number
}

export interface WechatReplyConfig {
  welcomeReply: string
  fallbackReply: string
  unsupportedMessageReply: string
  unsupportedEventReply: string
  promotionEntries?: WechatPromotionEntry[]
  keywordRules: WechatKeywordRule[]
}

export interface WechatReplyRelease {
  id: string
  version: number
  publishedByName: string
  rollbackFromVersion: number | null
  publishedAt: string
  isCurrent: boolean
}

export interface WechatReplyState {
  draft: WechatReplyConfig
  active: WechatReplyConfig
  activeReleaseId: string | null
  activeVersion: number | null
  updatedByName: string
  updatedAt: string | null
  releases: WechatReplyRelease[]
}

export interface WechatReplyValidation {
  valid: boolean
  errors: string[]
  warnings: string[]
}

export interface WechatReplyPreview {
  intent: string
  reply: string | null
  matchedRuleId: string
}

export const fetchWechatReplyState = () => getData<WechatReplyState>(http.get('/admin/wechat-replies/config'))
export const saveWechatReplyDraft = (config: WechatReplyConfig) => getData<WechatReplyState>(http.put('/admin/wechat-replies/draft', config))
export const validateWechatReplyConfig = (config: WechatReplyConfig) => getData<WechatReplyValidation>(http.post('/admin/wechat-replies/validate', config))
export const previewWechatReply = (message: string, config: WechatReplyConfig, msgType: 'text' | 'event' = 'text', event = '') =>
  getData<WechatReplyPreview>(http.post('/admin/wechat-replies/preview', { message, config, msgType, event }))
export const publishWechatReplyDraft = () => getData<WechatReplyState>(http.post('/admin/wechat-replies/publish'))
export const rollbackWechatReply = (releaseId: string) => getData<WechatReplyState>(http.post('/admin/wechat-replies/rollback', { releaseId }))

export const prepareWechatPromotionTemplate = (config: WechatReplyConfig) => getData<WechatReplyConfig>(http.post('/admin/wechat-replies/promotion-template', config))
