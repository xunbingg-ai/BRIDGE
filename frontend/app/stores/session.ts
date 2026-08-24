import { defineStore } from 'pinia'
import type { ChatMessage, SessionDetail } from '~/types'
import { apiFetch } from '~/composables/useApi'

interface SessionState {
  current: SessionDetail | null
  phase: 'patient' | 'examiner' | 'scoring' | 'completed' | 'expired'
  replyLoading: boolean
  submitting: boolean
}

export const useSessionStore = defineStore('session', {
  state: (): SessionState => ({
    current: null,
    phase: 'patient',
    replyLoading: false,
    submitting: false,
  }),

  getters: {
    messages: (state): ChatMessage[] => {
      if (!state.current?.content) return []
      return [
        ...(state.current.content.patient_phase || []),
        ...(state.current.content.examiner_phase || []),
      ]
    },
  },

  actions: {
    async startSession(caseId: number) {
      const data = await apiFetch<{
        session: SessionDetail
        reply: string
        phase: 'patient' | 'examiner'
      }>('/sessions', {
        method: 'POST',
        body: { caseId },
      })
      this.current = data.session
      this.phase = data.phase
      return data.session.sessionId
    },

    async loadSession(sessionId: number) {
      const data = await apiFetch<{ session: SessionDetail }>(`/sessions/${sessionId}`)
      this.current = data.session
      this.phase = this.statusToPhase(data.session.status)
      return data.session
    },

    async sendMessage(content: string) {
      if (!this.current) throw new Error('会话不存在')
      this.replyLoading = true
      try {
        const data = await apiFetch<{
          reply: string
          phase: 'patient' | 'examiner'
          session: SessionDetail
        }>(`/sessions/${this.current.sessionId}/message`, {
          method: 'POST',
          body: { content },
        })
        this.current = data.session
        this.phase = data.phase
        return data.reply
      } finally {
        this.replyLoading = false
      }
    },

    async endInquiry() {
      if (!this.current) throw new Error('会话不存在')
      const data = await apiFetch<{
        reply: string
        phase: 'examiner'
        session: SessionDetail
      }>(`/sessions/${this.current.sessionId}/end-inquiry`, {
        method: 'POST',
      })
      this.current = data.session
      this.phase = data.phase
      return data.reply
    },

    async submit() {
      if (!this.current) throw new Error('会话不存在')
      this.submitting = true
      try {
        const data = await apiFetch<{ status: string; message: string }>(
          `/sessions/${this.current.sessionId}/submit`,
          {
            method: 'POST',
            body: { content: this.current.content },
          },
        )
        this.phase = 'scoring'
        return data
      } finally {
        this.submitting = false
      }
    },

    statusToPhase(status: SessionDetail['status']) {
      if (status === 'examiner') return 'examiner'
      if (status === 'scoring') return 'scoring'
      if (status === 'completed') return 'completed'
      if (status === 'expired') return 'expired'
      return 'patient'
    },
  },
})
