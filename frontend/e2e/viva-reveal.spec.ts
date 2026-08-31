import { expect, test, type Page } from '@playwright/test'

/**
 * feat-013 回归：查体 / 辅助检查结果要在会话框（viva 阶段）解密显示。
 *
 * 约定：考官在「体格检查」「辅助检查」小节结束后，紧跟点评输出一行
 * `[PART: pe]` / `[PART: investigations]` 标记；前端把它从 UI 剥掉，并在该消息
 * 处解密一张「Physical Examination Findings / Investigation Results」卡片（数据来自
 * session.case 的 peFindings / investigations）。
 *
 * 运行环境：**真实 DeepSeek API**。考官按「概括病史 → 诊断 → 鉴别 → 体格检查 →
 * 辅助检查 → 处理」的固定顺序推进（prompt 已规定）。为规避真实模型措辞多变、
 * 反馈里混入其它小节词汇造成误判，本用例采用**顺序推进**策略：给出切题的答案
 * （hist/dx/diff/pe/inv），并在发现「体格检查」卡片后直接给出辅助检查答案，
 * 从而触发 [PART: pe] / [PART: investigations] 与两张解密卡片。
 */

const API = 'http://127.0.0.1:5000/api'

// 给考官的答案（严格按「当前阶段可用的信息」作答，避免被考官判定为提前泄露后续结果）：
//   - 概括病史(Q1)/诊断(Q2) 只依据「病史」推断（不引用查体/化验/影像结果——真实考官会要求
//     diagnosis 只基于 history）；
//   - 鉴别(Q3)/体格检查(Q4) 只给「计划 / 预期」，具体客观结果由 [PART: ...] 解密卡片揭晓。
const ANSWERS = {
  hist: '患者是32岁男性，约3天前熬夜受凉后急性起病，发热（最高38.8℃）、咳嗽、咳黄黏痰，伴右侧胸膜性胸痛（咳嗽及深吸气时加重）、乏力、全身肌肉酸痛。无咯血、盗汗、体重下降；既往体健，无结核接触史，无药物过敏史。总体为急性起病的感染性呼吸道疾病表现。',
  dx: '我的初步诊断是社区获得性肺炎。依据病史：3天前熬夜受凉后急性起病，发热（最高38.8℃）、咳嗽、咳黄黏痰、右侧胸膜性胸痛（咳嗽/深吸气加重），伴乏力、全身肌肉酸痛；无咯血、盗汗、体重下降；既往体健，无结核接触史。',
  diff: '鉴别诊断考虑：①急性支气管炎——有咳嗽咳痰但通常无胸膜性胸痛；②肺结核——多慢性、低热盗汗、好发上叶尖后段，本例急性高热且无结核接触史；③肺栓塞——以呼吸困难为主、发热不突出、常伴DVT危险因素，本例不符；④肺癌——中老年多见、常有咯血消瘦，本例年轻、急性病程。',
  pe: '我会先测生命体征（T、HR、RR、BP、SpO₂、BMI）与一般状况，再重点做呼吸系统检查：视诊胸廓活动度、触诊语颤、叩诊清浊、听诊呼吸音（重点看右下肺湿啰音/支气管呼吸音/胸膜摩擦音），同时检查循环系统与有无发绀、神志改变。',
  inv: '我会查血常规、CRP、必要时的降钙素原、胸部X线，以及痰涂片革兰染色+培养。血培养、动脉血气、胸部CT、非典型病原体/流感核酸、D-二聚体仅在有特定指征（重症、低氧、胸片不能解释、疑肺栓塞等）时查。',
  mgmt: '根据CURB-65为0分属低危，门诊治疗。首选阿莫西林500mg口服每日3次×5天；不耐受或疑非典型病原体可替代多西环素或阿奇霉素。辅以对症退热、补水、休息、戒烟宣教；做好安全网并告知转诊/住院指征，48～72小时复评。',
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
  // 必须先等 end-inquiry 完成并切到考官阶段，再开始作答，否则第一条答案会被路由到病人阶段。
  const endInquiryResp = page.waitForResponse((r) => r.url().includes('/end-inquiry'))
  await page.getByRole('button', { name: '结束问询' }).click()
  await endInquiryResp
  await page.waitForTimeout(800)

  const peCard = page.locator('.viva-result-card').filter({ hasText: 'Physical Examination' })
  const invCard = page.locator('.viva-result-card').filter({ hasText: 'Investigation' })

  // 逐轮推进，直到两张解密卡片都出现（最多 20 轮）。
  // 考官按「概括病史 → 诊断 → 鉴别 → 体格检查 → 辅助检查 → 处理」顺序推进（prompt 规定），
  // 这里顺序给出切题答案即可推进；一旦发现「体格检查」卡片（考官已输出 [PART: pe]），
  // 说明已进入「辅助检查」小节，直接给出辅助检查答案以触发 [PART: investigations] 卡片。
  const sequence = [ANSWERS.hist, ANSWERS.dx, ANSWERS.diff, ANSWERS.pe, ANSWERS.inv, ANSWERS.mgmt]
  let step = 0
  let peShown = false
  let invShown = false
  for (let i = 0; i < 20; i++) {
    if (await peCard.first().isVisible().catch(() => false)) peShown = true
    if (await invCard.first().isVisible().catch(() => false)) invShown = true
    if (peShown && invShown) break
    if (peShown) {
      // 已进入「辅助检查」小节，持续给出辅助检查答案，直到 investigations 卡片出现。
      await sendInSession(page, ANSWERS.inv)
    } else if (step < sequence.length) {
      await sendInSession(page, sequence[step])
      step++
    } else {
      // 兜底：若已答完全部题目仍未触发卡片，则继续按辅助检查答案尝试（避免越界）。
      await sendInSession(page, ANSWERS.inv)
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
