<template>
  <article
    ref="rootRef"
    class="min-h-44 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
  >
    <div v-if="!visible" class="flex h-36 items-center justify-center text-sm text-slate-400">
      加载中…
    </div>

    <div v-else>
      <div class="mb-3 flex items-start justify-between gap-3">
        <div>
          <p class="mb-1 text-xs font-medium text-blue-600">
            {{ departmentLabel }}
          </p>
          <h3 class="font-semibold text-slate-900">{{ caseItem.title }}</h3>
        </div>
      </div>

      <p class="mb-4 line-clamp-3 text-sm leading-6 text-slate-500">
        {{ caseItem.summary }}
      </p>

      <div class="flex items-center justify-between">
        <span class="text-xs text-slate-400">{{ caseItem.caseNo }}</span>
        <button
          type="button"
          class="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="starting"
          @click="handleStart"
        >
          {{ starting ? '正在创建…' : '开始练习' }}
        </button>
      </div>
    </div>
  </article>
</template>

<script lang="ts" setup>
import type { CaseSummary } from '~/types'

const props = defineProps<{ caseItem: CaseSummary }>()

const authStore = useAuthStore()
const sessionStore = useSessionStore()
const rootRef = ref<HTMLElement | null>(null)
const visible = ref(false)
const starting = ref(false)
let observer: IntersectionObserver | null = null

const departmentMap: Record<string, string> = {
  internal: '内科',
  surgery: '外科',
  obgyn: '妇产',
  pediatrics: '儿科',
  general: '全科',
  psychiatry: '精神',
}

const departmentLabel = computed(() => departmentMap[props.caseItem.department] || props.caseItem.department)

async function handleStart() {
  if (!authStore.isAuthenticated) {
    navigateTo({
      path: '/login',
      query: { redirect: `/session?caseid=${props.caseItem.caseId}` },
    })
    return
  }

  starting.value = true
  try {
    const sessionId = await sessionStore.startSession(props.caseItem.caseId)
    navigateTo(`/session/${sessionId}`)
  } catch (error: any) {
    alert(error.message || '创建会话失败')
  } finally {
    starting.value = false
  }
}

onMounted(() => {
  if (!('IntersectionObserver' in window)) {
    visible.value = true
    return
  }

  observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]
      if (entry?.isIntersecting) {
        visible.value = true
        observer?.disconnect()
      }
    },
    { rootMargin: '120px' },
  )

  if (rootRef.value) {
    observer.observe(rootRef.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>
