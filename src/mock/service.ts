/* Mock 服务聚合：按域拆分后统一导出 mockService，保持调用方兼容。 */
import { mockAuth } from './mockAuth'
import { mockExam } from './mockExam'
import { mockKnowledge } from './mockKnowledge'
import { mockManualWrong } from './mockManualWrong'
import { mockPersonal } from './mockPersonal'
import { mockPlan } from './mockPlan'
import { mockRmrb } from './mockRmrb'
import { mockZiliao } from './mockZiliao'
export { questionBank } from './_core'

export const mockService = {
  ...mockAuth,
  ...mockPlan,
  ...mockKnowledge,
  ...mockManualWrong,
  ...mockExam,
  ...mockRmrb,
  ...mockPersonal,
  ...mockZiliao,
}
