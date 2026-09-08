import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export function useAdminList() {
  const loading = ref(false)
  const loadError = ref('')
  async function runLoad(fn: () => Promise<void>, errMsg = '加载失败') {
    loading.value = true
    loadError.value = ''
    try {
      await fn()
    } catch (e) {
      loadError.value = e instanceof Error ? e.message : errMsg
      ElMessage.error(loadError.value)
    } finally {
      loading.value = false
    }
  }
  return { loading, loadError, runLoad }
}
