import { expect, test } from '@playwright/test'

/**
 * feat-012 内容泄漏回归断言。
 *
 * 修复目标（贴近真实 OSCE）：
 *   1. 考生在问诊前只看到「年龄 + 性别 + 一个核心症状」（卡片派生 brief），
 *      看不到完整病历 / 诊断 / 参考答案。
 *   2. 进入对话后由学生先开口，系统不自动弹出 SP 开场气泡。
 *   3. 病人按学生问到的问题回答，简短、患者口吻，绝不回吐完整病历/答案。
 */

const API = 'http://127.0.0.1:5000/api'

// 完整病史/答案的典型标记，卡片与病人开场/回复都不应出现
const LEAK_MARKERS = [
  '现病史',
  '主诉',
  '既往史',
  '过敏史',
  '月经史',
  '手术',
  '婚育史',
  '系统回顾',
  '家族史',
  '鉴别诊断',
  '诊断',
  '###',
]

function markersIn(text: string): string[] {
  return LEAK_MARKERS.filter((m) => text.includes(m))
}

test('home card shows only age/gender/symptom, not the full case history', async ({ page }) => {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.locator('article').first().scrollIntoViewIfNeeded()
  await expect(page.locator('article').first()).toBeVisible()

  const brief = (await page.locator('article').first().locator('p.line-clamp-3').textContent())?.trim() ?? ''
  console.log('CARD_BRIEF=' + brief)

  // 必须是简短的开场信息（年龄 + 性别 + 核心症状）
  expect(brief.length).toBeGreaterThan(0)
  expect(brief.length).toBeLessThan(80)
  expect(brief).toMatch(/岁/)
  expect(brief).toMatch(/男|女/)

  // 不得泄露完整病历 / 诊断 / 参考答案
  expect(markersIn(brief)).toEqual([])
})

test('session: student speaks first; patient answers short and non-leaky', async ({ page, request }) => {
  // 用 API 注册一个全新学生（绝对后端地址，避开前端无 /api 代理的问题）
  const uname = 'leak_' + Date.now()
  const reg = await request.post(`${API}/auth/register`, {
    data: { username: uname, password: 'test123' },
  })
  expect(reg.status()).toBeLessThan(300)

  // UI 登录
  await page.goto('/login')
  await page.waitForLoadState('networkidle')
  await page.getByLabel('用户名').fill(uname)
  await page.getByLabel('密码').fill('test123')
  await page.locator('button[type="submit"]').click()
  await page.waitForURL('**/')

  // 从首页第一张卡进入会话
  await page.locator('article').first().scrollIntoViewIfNeeded()
  await page.locator('article').first().getByRole('button', { name: '开始练习' }).click()
  await page.waitForURL('**/session/**')
  await page.waitForLoadState('networkidle')

  // 学生先开口：此时不应有任何病人气泡（markdown-body = 0），只有「请开始你的 OSCE 问诊」空态
  const markdown = page.locator('.markdown-body')
  await expect(markdown).toHaveCount(0)
  await expect(page.getByText(/请开始你的 OSCE 问诊/)).toBeVisible()

  // 学生发问
  await page.getByPlaceholder(/输入你的问诊内容/).fill('您好，请问您哪里不舒服？')
  await page.getByRole('button', { name: '发送' }).click()

  // 等待病人回复气泡出现
  await expect(markdown).toHaveCount(1)
  const reply = (await markdown.first().textContent())?.trim() ?? ''
  console.log('PATIENT_REPLY=' + reply)

  expect(reply.length).toBeGreaterThan(0)
  expect(reply.length).toBeLessThan(200)
  // 病人回复不应泄露完整病历/答案
  expect(markersIn(reply)).toEqual([])
})
