import { isMock } from '@/api'
import { useArticleStore } from '@/store/article'
import { useQuestionStore } from '@/store/question'
import { useUserStore } from '@/store/user'
import { getToken } from '@/utils/auth'

let bootstrapped = false

/** 应用启动：游客可浏览公开内容，有 token 再同步账号数据 */
export async function bootstrapApp(force = false) {
  if (isMock) return
  if (!getToken()) {
    bootstrapped = false
    useUserStore().clearSession()
    return
  }
  if (bootstrapped && !force) return

  const userStore = useUserStore()
  const articleStore = useArticleStore()
  const questionStore = useQuestionStore()

  const ok = await userStore.bootstrap()
  if (!ok) {
    userStore.clearSession()
    return
  }

  bootstrapped = true
  await Promise.all([articleStore.syncStudyData(), questionStore.loadWrongQuestions()])
}

export function resetBootstrap() {
  bootstrapped = false
}
