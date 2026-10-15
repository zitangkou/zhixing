import http, { getData } from './http'
export interface LlmUsageRow { date: string; purpose: string; model: string; calls: number; successes: number; failures: number; promptTokens: number; completionTokens: number; totalTokens: number; avgDurationMs: number; estimatedCost: number | null }
export interface LlmUsageSummary { start: string; end: string; items: LlmUsageRow[]; pricingConfigured: boolean; inputPricePerMillion: number; outputPricePerMillion: number }
export const getLlmUsageSummary = (params: { start: string; end: string }) => getData<LlmUsageSummary>(http.get('/admin/llm-usage/summary', { params }))
