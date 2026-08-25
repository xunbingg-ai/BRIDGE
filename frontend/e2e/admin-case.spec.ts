import { expect, test } from '@playwright/test'

/**
 * 后台病例管理端到端验证（feat-012 brief 字段落地 + 后台 CRUD/CSV）。
 * 覆盖用户要求的：后台界面新增、编辑病例；CSV 批量导入；确认数据确实写入/修改了病例库。
 * 用数据库 API 做落库复核，避免只靠 UI 表象。
 */

const API = 'http://127.0.0.1:5000/api'

function csvCell(value: string): string {
  // 含逗号/换行/引号的单元格需加引号并转义内部引号
  if (/[",\n\r]/.test(value)) {
    return '"' + value.replace(/"/g, '""') + '"'
  }
  return value
}

async function loginAdmin(page) {
  await page.goto('/login')
  await page.waitForLoadState('networkidle')
  await page.getByLabel('用户名').fill('admin')
  await page.getByLabel('密码').fill('admin123')
  await page.locator('button[type="submit"]').click()
  await page.waitForURL('**/')
}

test('admin UI: create + edit case and CSV import all persist to the case DB', async ({ page, request }) => {
  // 管理员 token（用于 API 落库复核）
  const loginRes = await request.post(`${API}/auth/login`, {
    data: { username: 'admin', password: 'admin123' },
  })
  const token = (await loginRes.json()).token
  const AH = { Authorization: `Bearer ${token}` }

  await loginAdmin(page)
  // 登录后走 SPA 客户端导航进入后台（避免整页刷新导致 Pinia 重置、被 auth/admin 中间件重定向）
  await page.getByRole('link', { name: '管理后台' }).click()
  await page.waitForURL('**/admin')
  await page.waitForLoadState('networkidle')
  await expect(page.getByRole('button', { name: '新增病例' })).toBeVisible()

  const uniq = Date.now().toString()
  const caseNo = 'E2E-' + uniq
  const title1 = 'E2E新增-' + uniq
  const title2 = 'E2E修改-' + uniq
  const brief1 = '35岁，男性，腹痛'
  const brief2 = '35岁，男性，发热'
  const scenario = '### 一般情况\n35岁男，上班族，汉族。\n### 主诉\n腹痛1天。'
  const reference = '诊断：腹痛待查；治疗：对症支持。'

  // ========== 1) 后台界面新增病例 ==========
  await page.getByRole('button', { name: '新增病例' }).click()
  await page.getByLabel('病例编号').fill(caseNo)
  await page.getByLabel('标题').fill(title1)
  await page.getByLabel('门类').selectOption('internal')
  await page.getByLabel(/卡片开场信息/).fill(brief1)
  await page.getByLabel(/病人剧本/).fill(scenario)
  await page.getByLabel('参考答案').fill(reference)
  await page.getByRole('button', { name: '保存' }).click()

  // 落库复核：搜索到该病例，brief/title/patientScenario 正确
  await expect(async () => {
    const r = await request.get(`${API}/admin/cases?search=${caseNo}`, { headers: AH })
    const items = (await r.json()).items
    const c = items.find((i) => i.caseNo === caseNo)
    expect(c, '新增病例应出现在管理列表').toBeTruthy()
    expect(c.title).toBe(title1)
    expect(c.brief).toBe(brief1)
    expect(c.patientScenario).toContain('腹痛1天')
  }).toPass({ timeout: 20_000 })

  // ========== 2) 后台界面编辑病例 ==========
  await page.getByPlaceholder(/搜索标题、摘要或编号/).fill(caseNo)
  await page.waitForTimeout(600)
  await page.getByRole('button', { name: '修改' }).first().click()
  // 编辑标题 + 卡片开场信息
  await page.getByLabel('标题').fill(title2)
  await page.getByLabel(/卡片开场信息/).fill(brief2)
  await page.getByRole('button', { name: '保存' }).click()

  await expect(async () => {
    const r = await request.get(`${API}/admin/cases?search=${caseNo}`, { headers: AH })
    const c = (await r.json()).items.find((i) => i.caseNo === caseNo)
    expect(c?.title).toBe(title2)
    expect(c?.brief).toBe(brief2)
  }).toPass({ timeout: 20_000 })

  // ========== 3) CSV 批量导入新增病例 ==========
  const csvCaseNo = 'E2ECSV-' + uniq
  const csvTitle = 'E2ECSV病例-' + uniq
  const csvBrief = '30岁，女性，头晕'
  await page.getByRole('button', { name: 'CSV 批量导入' }).click()
  await page.waitForLoadState('networkidle')
  const csv = [
    ['case_no', 'title', 'department', 'brief', 'patient_scenario', 'reference_answer'],
    [csvCaseNo, csvTitle, 'general', csvBrief,
      '### 一般情况\n王女士（化名），女，30岁，职员，汉族。\n### 主诉\n头晕1天。',
      '诊断：头晕待查；处理：进一步检查。'],
  ]
    .map((row) => row.map(csvCell).join(','))
    .join('\n')
  const fileInput = page.locator('input[type="file"]')
  await fileInput.setInputFiles({
    name: 'cases.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from('\ufeff' + csv, 'utf-8'),
  })

  // 导入提示"新增 1 条"
  await expect(page.getByText(/新增\s*1\s*条/)).toBeVisible({ timeout: 20_000 })

  // 落库复核
  await expect(async () => {
    const r = await request.get(`${API}/admin/cases?search=${csvCaseNo}`, { headers: AH })
    const c = (await r.json()).items.find((i) => i.caseNo === csvCaseNo)
    expect(c, 'csv 导入病例应出现在管理列表').toBeTruthy()
    expect(c.title).toBe(csvTitle)
    expect(c.brief).toBe(csvBrief)
  }).toPass({ timeout: 20_000 })

  // ========== 4) 清理：删除新增/导入的用例，保持病例库干净 ==========
  for (const no of [caseNo, csvCaseNo]) {
    const r = await request.get(`${API}/admin/cases?search=${no}`, { headers: AH })
    for (const it of (await r.json()).items.filter((i) => i.caseNo === no)) {
      await request.delete(`${API}/admin/cases/${it.caseId}`, { headers: AH })
    }
  }
  // 复核：已删除
  let leftCount = 0
  for (const no of [caseNo, csvCaseNo]) {
    const r = await request.get(`${API}/admin/cases?search=${no}`, { headers: AH })
    leftCount += (await r.json()).items.filter((i) => i.caseNo === no).length
  }
  expect(leftCount).toBe(0)
})
