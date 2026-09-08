/**
 * H5：把 AppFeedback 挂到 body，全页可用。
 * 小程序：依赖页面内 <AppFeedback />（见 AppTabBar / 关键页面）。
 */
import { createApp } from 'vue'
import AppFeedback from '@/components/AppFeedback.vue'
import { feedbackState, registerFeedbackHostEnsure } from '@/utils/feedback'

const HOST_ID = 'zk-feedback-host'
let mounted = false

function mountH5Host() {
  if (mounted || typeof document === 'undefined') return
  let el = document.getElementById(HOST_ID)
  if (!el) {
    el = document.createElement('div')
    el.id = HOST_ID
    document.body.appendChild(el)
  }
  createApp(AppFeedback).mount(el)
  mounted = true
  feedbackState.hostReady = true
}

export function ensureFeedbackHost() {
  if (process.env.TARO_ENV === 'h5') {
    mountH5Host()
  } else {
    // 小程序端由页面内组件承接；标记 ready 以便调用方不阻塞
    feedbackState.hostReady = true
  }
}

registerFeedbackHostEnsure(ensureFeedbackHost)
