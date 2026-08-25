export interface User {
  userId: number
  username: string
  email: string | null
  phone: string | null
  realName: string | null
  avatar: string | null
  role: 'student' | 'teacher' | 'admin'
  createdAt: string
  updatedAt: string
}

export interface AuthResponse {
  token: string
  user: User
}

export interface CaseSummary {
  caseId: number
  caseNo: string
  title: string
  department: string
  /** OSCE 开场信息：年龄 + 性别 + 一个核心症状（后端从病人剧本派生），不含诊断/完整病史 */
  brief: string
  createdAt: string
  updatedAt: string
}

export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
}

export interface SessionContent {
  session_id: number
  case_id: number
  started_at: string | null
  ended_at: string | null
  duration_seconds: number
  patient_phase: ChatMessage[]
  examiner_phase: ChatMessage[]
}

export interface ScoreData {
  total_score?: number
  max_score?: number
  sub_scores?: Record<string, number>
  graded_at?: string
}

export interface ReportComment {
  criteria: string
  score: number
  max_score: number
  comment: string
}

export interface ReportData {
  summary?: string
  strengths?: string[]
  weaknesses?: string[]
  suggestions?: string[]
  detailed_comments?: ReportComment[]
}

export interface SessionDetail {
  sessionId: number
  userId: number
  caseId: number
  createAt: string
  deadlineAt: string
  status: 'patient' | 'examiner' | 'scoring' | 'completed' | 'expired'
  content: SessionContent
  score: ScoreData | null
  report: ReportData | null
  endedAt: string | null
  updatedAt: string
  caseTitle?: string
  department?: string
  referenceAnswer?: string
  /** viva 阶段解密展示的体格检查客观结果（markdown），无该小节时为空 */
  peFindings?: string
  /** viva 阶段解密展示的辅助检查结果（markdown），无该小节时为空 */
  investigations?: string
}

export interface SessionHistoryItem {
  sessionId: number
  caseId: number
  caseTitle: string
  department: string
  status: string
  createAt: string
  endedAt: string | null
  totalScore: number | null | undefined
}

export interface PagedResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export interface CaseDetail extends CaseSummary {
  /** 完整病人剧本（患者角色扮演用），只供管理后台编辑，不提供给考生端 */
  patientScenario: string
  referenceAnswer: string
  isActive: number
}

export interface LlmConfig {
  id?: number
  name: string
  baseUrl: string
  apiKey: string
  hasApiKey?: boolean
  headers: Record<string, string>
  model: string | null
  backupModel: string | null
  createdAt?: string
  updatedAt?: string
}

export interface LlmTestResult {
  model: string
  latencyMs: number
  content?: string
}
