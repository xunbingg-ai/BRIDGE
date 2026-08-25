import { expect, test, type Page } from '@playwright/test'

/**
 * feat-013 回归：查体 / 辅助检查结果要在会话框（viva 阶段）解密显示。
 *
 * 约定：考官在「体格检查」「辅助检查」小节结束后，紧跟点评输出一行
 * `[PART: pe]` / `[PART: investigations]` 标记；前端把它从 UI 剥掉，并在该消息
 * 处解密一张「体格检查结果 / 辅助检查结果」卡片（数据来自 session.case 的
 * peFindings / investigations）。
 *
 * 运行环境：**真实 DeepSeek API**。考官提问的措辞与推进节奏由模型决定，且模型
 * 会严格按「诊断 → 鉴别 → 体格检查 → 辅助检查 → 处理」的顺序推进，若答非所问
 * 会被卡住。因此本用例**读取考官当前问的问题并给出对应答案**，从而推进到
 * 「体格检查 / 辅助检查」小节，触发 [PART: pe] / [PART: investigations] 与解密卡片。
 */

const API = 'http://127.0.0.1:5000/api'

// 给考官的答案（严格按「当前阶段可用的信息」作答，避免被考官判定为提前泄露后续结果）：
//   - Q1/Q2 只依据「病史」推断（不引用查体/化验/影像结果——真实考官会要求 diagnosis
//     只基于 history）；
//   - Q3/Q4 只给「计划 / 预期」，具体客观结果由 [PART: ...] 解密卡片揭晓。
const ANSWERS = {
  dx: '我的初步诊断是社区获得性肺炎。依据病史：3天前熬夜受凉后急性起病，发热（最高38.8℃）、咳嗽、咳黄黏痰、右侧胸膜性胸痛（咳嗽/深吸气加重），伴乏力、全身肌肉酸痛；无咯血、盗汗、体重下降；既往体健，无结核接触史。',
  diff: '鉴别诊断考虑：①急性支气管炎——有咳嗽咳痰但通常无胸膜性胸痛；②肺结核——多慢性、低热盗汗、好发上叶尖后段，本例急性高热且无结核接触史；③肺栓塞——以呼吸困难为主、发热不突出、常伴DVT危险因素，本例不符；④肺癌——中老年多见、常有咯血消瘦，本例年轻、急性病程。',
  pe: '我会先测生命体征（T、HR、RR、BP、SpO₂、BMI）与一般状况，再重点做呼吸系统检查：视诊胸廓活动度、触诊语颤、叩诊清浊、听诊呼吸音（重点看右下肺湿啰音/支气管呼吸音/胸膜摩擦音），同时检查循环系统与有无发绀、神志改变。',
  inv: '我会查血常规、CRP、必要时的降钙素原、胸部X线，以及痰涂片革兰染色+培养。血培养、动脉血气、胸部CT、非典型病原体/流感核酸、D-二聚体仅在有特定指征（重症、低氧、胸片不能解释、疑肺栓塞等）时查。',
  mgmt: '根据CURB-65为0分属低危，门诊治疗。首选阿莫西林500mg口服每日3次×5天；不耐受或疑非典型病原体可替代多西环素或阿奇霉素。辅以对症退热、补水、休息、戒烟宣教；做好安全网并告知转诊/住院指征，48～72小时复评。',
}

/** 根据考官最后一条问题内容，挑选对应答案（题目可能是英文或中文，用双语关键词匹配）。 */
function pickAnswer(lastExamText: string): string {
  const t = (lastExamText || '').toLowerCase()
  // 辅助检查 / investigations
  if (/辅助检查|化验|investigation|which test|laboratory|lab\b|blood test|imaging|workup/.test(t)) return ANSWERS.inv
  // 体格检查 / physical examination
  if (/体格检查|查体|physical exam|examination|examine|percus|auscul|fremitus|inspect/.test(t)) return ANSWERS.pe
  // 鉴别诊断 / differential
  if (/鉴别诊断|鉴别|differen|distinguish|tell .* apart/.test(t)) return ANSWERS.diff
  // 处理 与随访 / management
  if (/处理方案|治疗|管理|随访|management|treatment|plan|red flag|referral|antibiotic/.test(t)) return ANSWERS.mgmt
  // 默认当作「诊断」问题
  return ANSWERS.dx
}

async function loginStudent(page: Page, uname: string) {
  await page.goto('/login')
  await page.waitForLoadState('networkidle')
  await page.getByLabel('用户名').fill(uname)
  await page.getByLabel('密码').fill('test123')
  await page.locator('button[type="submit"]').click()
  await page.waitForURL('**/')
}

async function sendInSession(page: Page, text: string) {
  const req = page.waitForRequest(
    (r) => r.method() === 'POST' && /\/sessions\/\d+\/message$/.test(r.url()),
  )
  await page.getByPlaceholder(/输入你的问诊内容/).fill(text)
  await page.getByRole('button', { name: '发送' }).click()
  await req
  // 让 Vue 渲染完考官新回复（真实模型回复需数秒）
  await page.waitForTimeout(800)
}

/** 读取考官当前最后一条问题（聊天气泡，排除解密结果卡片），给出对应的回答并发送。 */
async function answerExaminerQuestion(page: Page): Promise<void> {
  const lastExam = ((await page.locator('.chat-bubble-md').last().textContent()) ?? '').trim()
  await sendInSession(page, pickAnswer(lastExam))
}

test.setTimeout(240_000)

test('viva reveals PE + investigations result cards when the examiner emits [PART] tags', async ({ page, request }) => {
  // 注册 + 登录一个全新学生
  const uname = 'reveal_' + Date.now()
  const reg = await request.post(`${API}/auth/register`, {
    data: { username: uname, password: 'test123' },
  })
  expect(reg.status()).toBeLessThan(300)
  await loginStudent(page, uname)

  // 进入第一例病例的会话
  await page.locator('article').first().scrollIntoViewIfNeeded()
  await page.locator('article').first().getByRole('button', { name: '开始练习' }).click()
  await page.waitForURL('**/session/**')
  await page.waitForLoadState('networkidle')

  // 病人阶段：学生先开口问一次
  await sendInSession(page, '您好，请问您哪里不舒服？')
  await expect(page.locator('.markdown-body').first()).toBeVisible()

  // 结束问询 → 考官（viva）阶段
  await page.getByRole('button', { name: '结束问询' }).click()

  const peCard = page.locator('.viva-result-card').filter({ hasText: '体格检查结果' })
  const invCard = page.locator('.viva-result-card').filter({ hasText: '辅助检查结果' })

  // 逐轮推进，直到两张解密卡片都出现（最多 14 轮）。
  // 未出现 PE 卡前按「考官当前问题」回答；一旦考官输出了 [PART: pe]（PE 卡出现），
  // 说明已进入「辅助检查」小节（考官按诊断→鉴别→体检→辅助→处理顺序推进），
  // 直接给出辅助检查答案，从而触发 [PART: investigations]。
  let peShown = false
  let invShown = false
  for (let i = 0; i < 14; i++) {
    if (await peCard.first().isVisible().catch(() => false)) peShown = true
    if (await invCard.first().isVisible().catch(() => false)) invShown = true
    if (peShown && invShown) break
    if (peShown) {
      await sendInSession(page, ANSWERS.inv)
    } else {
      await answerExaminerQuestion(page)
    }
  }

  await expect(peCard.first()).toBeVisible()
  await expect(invCard.first()).toBeVisible()

  // 卡片有实际内容，且不含分节标记
  const peText = ((await peCard.textContent()) ?? '').replace(/\s+/g, ' ')
  expect(peText.length).toBeGreaterThan(20)
  expect(peText).not.toContain('[PART:')

  const invText = ((await invCard.textContent()) ?? '').replace(/\s+/g, ' ')
  expect(invText.length).toBeGreaterThan(20)
  expect(invText).not.toContain('[PART:')

  // 整段聊天的可见文本都不得再出现 `[PART:` 标记（前端已剥掉）。
  // 注：`not.toContainText` 要求单一元素，而 `.markdown-body` 会命中多条气泡/卡片，
  //  故改用「没有任何元素包含 [PART: 」的计数断言。
  await expect(page.getByText(/\[PART:/)).toHaveCount(0)

  // 两张结果卡片都已出现
  await expect(page.locator('.viva-result-card')).toHaveCount(2)
})
