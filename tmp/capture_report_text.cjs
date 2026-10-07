const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  await page.goto(process.env.WEB_BASE_URL || 'http://127.0.0.1:8014');
  await page.waitForFunction(() => document.querySelectorAll('.card').length === 40);
  await page.locator('#search-input').fill('black shoes');
  await page.locator('#search-input').press('Enter');
  await page.waitForFunction(() => document.querySelector('#status').textContent.startsWith('Đã tìm thấy'));
  await page.screenshot({ path: 'tmp/docx-assets/text-search-full.png', fullPage: true });
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
