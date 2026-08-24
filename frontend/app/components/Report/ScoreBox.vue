<template>
  <div class="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div class="mb-6 text-center">
      <p class="text-sm text-slate-400">总分</p>
      <p class="text-5xl font-bold text-blue-600">{{ score?.total_score ?? '—' }}</p>
      <p class="mt-1 text-xs text-slate-400">满分 {{ score?.max_score ?? 100 }}</p>
    </div>

    <div class="mb-6 space-y-3">
      <div
        v-for="item in subScores"
        :key="item.key"
        class="rounded-xl border border-slate-100 p-4"
      >
        <div class="mb-2 flex items-center justify-between text-sm">
          <span class="text-slate-600">{{ item.label }}</span>
          <span class="font-semibold text-slate-900">{{ item.value }}</span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            class="h-full rounded-full bg-blue-500 transition-all"
            :style="{ width: `${item.percent}%` }"
          />
        </div>
      </div>
    </div>

    <div class="border-t border-slate-100 pt-5">
      <p v-if="report?.summary" class="mb-4 text-sm leading-6 text-slate-600">
        {{ report.summary }}
      </p>

      <div v-if="report?.strengths?.length" class="mb-3">
        <h3 class="mb-2 text-sm font-semibold text-emerald-600">做得好的地方</h3>
        <ul class="space-y-1 text-sm text-slate-600">
          <li v-for="item in report.strengths" :key="item" class="flex gap-2">
            <span>·</span>
            <span>{{ item }}</span>
          </li>
        </ul>
      </div>

      <div v-if="report?.weaknesses?.length" class="mb-3">
        <h3 class="mb-2 text-sm font-semibold text-rose-600">需要改进</h3>
        <ul class="space-y-1 text-sm text-slate-600">
          <li v-for="item in report.weaknesses" :key="item" class="flex gap-2">
            <span>·</span>
            <span>{{ item }}</span>
          </li>
        </ul>
      </div>

      <div v-if="report?.suggestions?.length" class="mb-3">
        <h3 class="mb-2 text-sm font-semibold text-blue-600">建议</h3>
        <ul class="space-y-1 text-sm text-slate-600">
          <li v-for="item in report.suggestions" :key="item" class="flex gap-2">
            <span>·</span>
            <span>{{ item }}</span>
          </li>
        </ul>
      </div>

      <div v-if="report?.detailed_comments?.length" class="space-y-3">
        <h3 class="mb-2 text-sm font-semibold text-slate-900">分项评价</h3>
        <div
          v-for="comment in report.detailed_comments"
          :key="comment.criteria"
          class="rounded-xl bg-slate-50 p-4"
        >
          <div class="mb-1 flex items-center justify-between text-sm">
            <span class="font-medium text-slate-700">{{ comment.criteria }}</span>
            <span class="text-slate-500">{{ comment.score }} / {{ comment.max_score }}</span>
          </div>
          <p class="text-sm leading-6 text-slate-600">{{ comment.comment }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ReportData, ScoreData } from '~/types'

const props = defineProps<{
  score: ScoreData | null
  report: ReportData | null
}>()

const labels: Record<string, string> = {
  history_taking: '病史采集',
  communication: '沟通技巧',
  clinical_reasoning: '临床推理',
  professionalism: '职业素养',
}

const maxMap: Record<string, number> = {
  history_taking: 30,
  communication: 25,
  clinical_reasoning: 25,
  professionalism: 20,
}

const subScores = computed(() => {
  const entries = Object.entries(props.score?.sub_scores || {})
  return entries.map(([key, value]) => ({
    key,
    label: labels[key] || key,
    value,
    percent: Math.min(100, Math.round((Number(value) / (maxMap[key] || 25)) * 100)),
  }))
})
</script>
