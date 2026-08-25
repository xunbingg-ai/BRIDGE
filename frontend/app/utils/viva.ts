/**
 * Viva 分节 tag 工具。
 *
 * 考官（examiner）在「体格检查」与「辅助检查」小节结束后，会输出一行标记：
 *   [PART: pe]
 *   [PART: investigations]
 * 这些 tag 不是给考生看的，而是前后端约定的结构化信号——前端从 UI 文本里剥掉它，
 * 并在出现该 tag 的消息处解密一张对应的结果卡片（数据来自 session.case 的 peFindings / investigations）。
 */

export type VivaPart = 'pe' | 'investigations'

const PART_TAG_PATTERN = /\[PART:\s*(pe|investigations)\s*\]/g

/** 从一段文本中提取所有出现的 viva 分节 tag。 */
export function extractVivaParts(text: string): VivaPart[] {
  const parts: VivaPart[] = []
  if (!text) return parts
  const re = new RegExp(PART_TAG_PATTERN.source, 'g')
  let m: RegExpExecArray | null
  while ((m = re.exec(text))) {
    const part = m[1] as VivaPart
    if (!parts.includes(part)) parts.push(part)
  }
  return parts
}

/** 判断一段文本是否包含指定分节 tag。 */
export function hasVivaPart(text: string, part: VivaPart): boolean {
  if (!text) return false
  return new RegExp(`\\[PART:\\s*${part}\\s*\\]`).test(text)
}

/** 从 UI 文本中剥掉所有 viva 分节 tag（保留其余内容不变）。 */
export function stripVivaTags(text: string): string {
  if (!text) return text
  return text
    .replace(new RegExp(PART_TAG_PATTERN.source, 'g'), ' ')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}
