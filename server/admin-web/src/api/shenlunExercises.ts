import http, { getData } from './http'
export type ExerciseType = 'summary' | 'countermeasure' | 'implementation' | 'essay'
export interface ShenlunExercise {
  id?: string; question_type: ExerciseType; title: string; source_article_id?: string | null
  source_material_id?: string | null; fact_material_summary: string; fact_material_limit: string
  fact_training?: FactTrainingBundle
  source_title: string; source_url: string; source_date: string; source_excerpt: string
  prompt: string; requirements: string; max_chars: number; hint: string
  key_points: { point: string; evidence: string }[]; rubric: { name: string; description: string }[]
  sample_answer: string; analysis: string; related_assets: { type: string; id: string; title: string }[]
  difficulty: string; estimated_minutes: number; sort_order: number; is_featured: boolean; status: 'draft' | 'published' | 'archived'
  human_review: {decision:'pending'|'approved'|'revision_required'|'rejected';issue_tags:string[];notes:string;corrections_made:boolean;reviewer?:string;reviewed_at?:string;legacy_record?:boolean;content_fingerprint?:string}
  human_review_history?: {decision:string;issue_tags?:string[];notes?:string;corrections_made?:boolean;reviewer?:string;reviewed_at?:string}[]
  generation_job_id?: string; generation_model?: string; generation_rule_version?: string; quality_score?: number
  quality_report?: {pass?:boolean;score?:number;dimensions?:Record<string,number>;errors?:string[];notes?:string[];taskCard?:{focus?:string;scene?:string;anchor?:string};keyPointsRationale?:string;benchmarkSetVersion?:string;benchmarkCaseIds?:string[];semantic_review?:{pass?:boolean;score?:number;task_specificity?:boolean;material_dependence?:boolean;candidate_answerability?:boolean;scope_bounded?:boolean;critical_issues?:string[];key_points_granularity_ok?:boolean;point_checks?:{point_index:number;supported:boolean;quote:string;reason?:string}[];answer_point_checks?:{point_index:number;covered:boolean;quote:string;reason?:string}[];blocking_findings?:{severity?:string;issue_type?:string;dimension?:string;target?:string;reason?:string}[];findings?:{severity?:string;issue_type?:string;dimension?:string;target?:string;reason?:string;quote?:string}[];suggestions?:string[]}}
}
export interface FactTrainingBundle {
  version?: number; anchor_material_id?: string; generated_by?: string; review_notice?: string
  related_materials?: Array<{id:string;text:string;fact:string;result:string;proves:string;evidence:string;source_title:string;source_url:string;source_date:string;theme:string;relation_reason:string}>
  themes?: Array<{id:string;theme:string;fit_reason:string;task_prompt:string;point:string;analysis:string;paragraph:string;citations:Array<{material_id:string;exact_evidence:string}>}>
}
export interface ShenlunFactMaterial {
  id:string; text:string; fact:string; source_evidence:string; source_anchor:string; source_title:string
  source_section:string; source_url:string; source_date:string; result:string; proves:string; do_not_use_for:string
  theme_code:string
}
export interface ShenlunExerciseJob {
  id:string; issue_date:string; trigger_mode:string; status:string; attempts:number; error:string
  progress:{candidateArticles?:number;selectedArticles?:number;processedArticles?:number;remainingCandidates?:number;dailyLimitReached?:boolean;currentArticle?:string;generated?:{id:string;title:string;questionType:string;score:number;sourceTitle:string}[];rejected?:{title:string;score?:number;errors?:string[]}[];skipped?:{title?:string;reason?:string}[];failures?:{title?:string;errors?:string[]}[]}
  started_at?:string|null; finished_at?:string|null
}
export interface ShenlunReviewMetrics {
  total_exercises:number; reviewed_count:number; corrections_made_count:number; history_event_count:number
  decision_counts:Record<'pending'|'approved'|'revision_required'|'rejected',number>
  issue_counts:Record<string,number>; by_type:Record<string,Record<string,number>>
  by_rule_version:Record<string,{total:number;reviewed:number;approved:number;revision_required:number;rejected:number;pending:number;corrections_made:number}>
}
export interface ShenlunReviewDataset {
  schema_version:number; exported_at:string; count:number; total_available:number
  items:Array<{exercise_id:string;reviewed_at?:string|null;reviewer?:string|null;decision:string;issue_tags:string[];notes:string;corrections_made:boolean;generation_rule_version?:string|null;benchmark_set_version?:string;legacy_snapshot?:boolean;content:Record<string,unknown>}>
}
export const list = (params: Record<string, unknown>) => getData<{items:ShenlunExercise[];total:number}>(http.get('/admin/shenlun-exercises',{params}))
export const jobs = () => getData<ShenlunExerciseJob[]>(http.get('/admin/shenlun-exercises/jobs'))
export const reviewMetrics = () => getData<ShenlunReviewMetrics>(http.get('/admin/shenlun-exercises/review-metrics'))
export const reviewDataset = (params:Record<string,unknown>) => getData<ShenlunReviewDataset>(http.get('/admin/shenlun-exercises/review-dataset',{params}))
export const generate = (issue_date:string) => getData<ShenlunExerciseJob>(http.post('/admin/shenlun-exercises/generate',{issue_date}))
export const standards = () => getData<Record<string,unknown>>(http.get('/admin/shenlun-exercises/standards'))
export const articles = () => getData<{id:string;title:string;source_url:string;publish_date:string}[]>(http.get('/admin/shenlun-exercises/articles'))
export const factMaterials = () => getData<ShenlunFactMaterial[]>(http.get('/admin/shenlun-exercises/fact-materials'))
export const generateFactTraining = (source_material_id:string) => getData<FactTrainingBundle>(http.post('/admin/shenlun-exercises/fact-training/generate',{source_material_id}))
export const save = (data:ShenlunExercise) => getData<ShenlunExercise>(data.id ? http.put(`/admin/shenlun-exercises/${data.id}`,data) : http.post('/admin/shenlun-exercises',data))
export const archive = (id:string) => getData(http.delete(`/admin/shenlun-exercises/${id}`))
