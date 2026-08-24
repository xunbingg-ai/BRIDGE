import { defineStore } from 'pinia'
import type { CaseSummary, PagedResult } from '~/types'
import { apiFetch } from '~/composables/useApi'

interface CasesState {
  items: CaseSummary[]
  total: number
  page: number
  pageSize: number
  department: string
  search: string
  loading: boolean
  loadingMore: boolean
}

export const useCasesStore = defineStore('cases', {
  state: (): CasesState => ({
    items: [],
    total: 0,
    page: 1,
    pageSize: 8,
    department: 'all',
    search: '',
    loading: false,
    loadingMore: false,
  }),

  getters: {
    hasMore: (state) => state.items.length < state.total,
  },

  actions: {
    async fetchCases(params: { department?: string; search?: string; page?: number } = {}) {
      this.loading = true
      this.loadingMore = false
      try {
        this.department = params.department ?? this.department
        this.search = params.search ?? this.search
        this.page = params.page ?? 1

        const data = await apiFetch<PagedResult<CaseSummary>>('/cases', {
          query: {
            department: this.department,
            search: this.search,
            page: this.page,
            pageSize: this.pageSize,
          },
        })

        this.items = data.items
        this.total = data.total
        this.page = data.page
      } finally {
        this.loading = false
      }
    },

    async loadMore() {
      if (this.loading || this.loadingMore || !this.hasMore) return

      this.loadingMore = true
      try {
        const nextPage = this.page + 1
        const data = await apiFetch<PagedResult<CaseSummary>>('/cases', {
          query: {
            department: this.department,
            search: this.search,
            page: nextPage,
            pageSize: this.pageSize,
          },
        })

        const merged = [...this.items, ...data.items]
        const seen = new Set<number>()
        this.items = merged.filter((item) => {
          if (seen.has(item.caseId)) return false
          seen.add(item.caseId)
          return true
        })
        this.total = data.total
        this.page = data.page
      } finally {
        this.loadingMore = false
      }
    },
  },
})
