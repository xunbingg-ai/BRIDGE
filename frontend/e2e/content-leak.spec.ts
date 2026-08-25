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

test('home card shows only age/gender/symptom, not the diagnosis or full history', async ({ page }) => {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.locator('article').first().scrollIntoViewIfNeeded()
  await expect(page.locator('article').first()).toBeVisible()

  const card = page.locator('article').first()
  // 不应再出现诊断标题（粗体 h3）——卡片只展示核心症状简介
  await expect(card.locator('h3')).toHaveCount(0)

  const brief = (await card.locator('p.font-semibold').textContent())?.trim() ?? ''
  console.log('CARD_BRIEF=' + brief)

  // 必须是简短的开场信息（年龄 + 性别 + 核心症状）
  expect(brief.length).toBeGreaterThan(0)
  expect(brief.length).toBeLessThan(80)
  expect(brief).toMatch(/岁/)
  expect(brief).toMatch(/男|女/)

  // 整张卡的可见文字都不得泄露完整病历 / 诊断 / 参考答案
  const cardText = ((await card.textContent()) ?? '').replace(/\s+/g, ' ')
  expect(markersIn(cardText)).toEqual([])
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

  // 学生发问 —— 关键是：必须先命中「发送消息」的后端 API
  const msgReq = page.waitForRequest(
    (r) => r.method() === 'POST' && /\/sessions\/\d+\/message$/.test(r.url()),
  )
  await page.getByPlaceholder(/输入你的问诊内容/).fill('您好，请问您哪里不舒服？')
  await page.getByRole('button', { name: '发送' }).click()

  // 断言这次确实发起了 message API 请求（用户反馈「聊天窗口没调用 API」的反向锁定）
  await msgReq

  // 等待病人回复气泡出现
  await expect(markdown).toHaveCount(1)
  const reply = (await markdown.first().textContent())?.trim() ?? ''
  console.log('PATIENT_REPLY=' + reply)

  expect(reply.length).toBeGreaterThan(0)
  // 病人回复应短而不泄密（真实大模型回复略长，放宽到 <1000 以兜住「整段病历外泄」）
  expect(reply.length).toBeLessThan(1000)
  // 病人回复不应泄露完整病历/答案
  expect(markersIn(reply)).toEqual([])

  // 【Problem 2】追问「请再告诉我多一点信息」时，SP 一次只回答一个信息点：
  // 不把整段现病史/病程一次性汇报出来，只补一个最相关的新细节。
  const msgReq2 = page.waitForRequest(
    (r) => r.method() === 'POST' && /\/sessions\/\d+\/message$/.test(r.url()),
  )
  await page
    .getByPlaceholder(/输入你的问诊内容/)
    .fill('请再告诉我多一点信息，比如什么时候开始的，还有没有别的症状？')
  await page.getByRole('button', { name: '发送' }).click()
  await msgReq2
  await expect(markdown).toHaveCount(2)
  const followUp = (await markdown.nth(1).textContent())?.trim() ?? ''
  console.log('PATIENT_FOLLOWUP=' + followUp)

  expect(followUp.length).toBeGreaterThan(0)
  // 一次只给一个信息点：回复应短（一两句），远小于整段现病史的长度；且不出现结构标记
  expect(followUp.length).toBeLessThan(500)
  expect(markersIn(followUp)).toEqual([])
})
