import { expect, test } from '@playwright/test'

/**
 * OSCE web-app smoke test.
 *
 * These are intentionally small, deterministic flow checks that the
 * independent-context EVALUATOR subagent runs before any handoff. They cover
 * the two most load-bearing paths: the case list (home) and authentication.
 */

test.describe('OSCE smoke', () => {
  test('home page renders the case list', async ({ page }) => {
    await page.goto('/')

    // Heading + total counter render from the store
    await expect(page.locator('h1', { hasText: '病例列表' })).toBeVisible()
    await expect(page.locator('text=共')).toBeVisible()

    // Category filters + search box (NavBar)
    await expect(page.getByRole('button', { name: '全部' })).toBeVisible()
    await expect(page.getByRole('button', { name: '内科' })).toBeVisible()
    await expect(page.getByPlaceholder(/搜索/i)).toBeVisible()

    // At least one case card renders and offers "开始练习"
    await expect(page.locator('article').first()).toBeVisible()
    await expect(
      page.locator('article').first().getByRole('button', { name: '开始练习' }),
    ).toBeVisible()
  })

  test('admin can log in and reach the admin entry', async ({ page }) => {
    await page.goto('/login')
    // Wait for the Nuxt app to hydrate; otherwise the form's submit handler
    // is not attached yet and the click can fall through to a native submit.
    await page.waitForLoadState('networkidle')

    await page.getByLabel('用户名').fill('admin')
    await page.getByLabel('密码').fill('admin123')
    await page.locator('button[type="submit"]').click()

    // Login succeeds: token is persisted and we land back on the home page
    await page.waitForURL('**/')
    const token = await page.evaluate(() => localStorage.getItem('oscae_token'))
    expect(token).toBeTruthy()

    // Admin role surfaces the admin console link in the top bar
    await expect(page.getByRole('link', { name: '管理后台' })).toBeVisible()
    await expect(page.getByRole('link', { name: '个人中心' })).toBeVisible()
  })
})
