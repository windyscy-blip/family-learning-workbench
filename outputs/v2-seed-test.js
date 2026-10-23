// Built-in word bank auto-init E2E test for family-learning-workbench-v2.html
// Model: seeds install silently on first boot as import batches; NO UI entry anywhere.
const fs = require('fs');
const path = require('path');
const http = require('http');
const { chromium } = require('playwright-core');

const ROOT = 'C:/Users/sPark/WorkBuddy/2026-10-09-16-55-37/outputs';
const HTML = fs.readFileSync(path.join(ROOT, 'family-learning-workbench-v2.html'), 'utf8');

(async () => {
  const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(HTML);
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

  await page.goto('http://127.0.0.1:' + port + '/');

  const results = {};
  const check = (name, cond) => { results[name] = !!cond; if (!cond) console.log('FAIL:', name); };

  // 1. auto-installed on first boot, logged as import batches
  check('english-seeded-253', (await page.evaluate(() => window.__WB.state.english.entries.length)) === 253);
  check('chinese-seeded-245', (await page.evaluate(() => window.__WB.state.chinese.entries.length)) === 245);
  check('english-batch-1', (await page.evaluate(() => window.__WB.state.english.batches.length)) === 1);
  check('chinese-batch-1', (await page.evaluate(() => window.__WB.state.chinese.batches.length)) === 1);
  check('importlog-2', (await page.evaluate(() => window.__WB.state.importLog.length)) === 2);
  check('batch-names', await page.evaluate(() => /沪教牛津版三年级上册/.test(window.__WB.state.english.batches[0].name) && /统编版三年级上册语文词语表/.test(window.__WB.state.chinese.batches[0].name)));

  // 2. no init UI anywhere
  check('no-seed-button', await page.evaluate(() => !document.getElementById('seedGrade3')));
  await page.evaluate(() => window.__WB.route('learn'));
  check('no-seed-link-or-text', await page.evaluate(() => !document.querySelector('[data-seed]') && !/一键初始化|初始化三年级/.test(document.body.innerText)));
  check('stat-english-253', /253 个单词/.test(await page.locator('#statEnglish').textContent()));
  check('stat-chinese-245', /245 个字词/.test(await page.locator('#statChinese').textContent()));

  // 3. chinese library shows seeded units and rows
  await page.locator('[data-module="chinese"]').first().click();
  await page.waitForTimeout(200);
  check('chinese-library-rows-245', await page.locator('#moduleChinese .library-row').count() === 245);
  check('chinese-library-20-units', (await page.locator('[data-lib-unit="chinese"] option').count()) === 20); // all + 19 sections
  check('chinese-reading-kept', await page.evaluate(() => window.__WB.state.chinese.entries.some(e => e.reading === 'shān pō' && e.text === '山坡')));

  // 4. english library still 10 units
  await page.evaluate(() => window.__WB.route('learn'));
  await page.locator('[data-module="english"]').first().click();
  await page.waitForTimeout(200);
  check('english-library-rows-253', await page.locator('#moduleEnglish .library-row').count() === 253);
  check('english-library-11-units', (await page.locator('[data-lib-unit="english"] option').count()) === 11);

  // 5. task creation from seeded pool works
  await page.evaluate(() => window.__WB.route('learn'));
  await page.locator('[data-module="chinese"]').first().click();
  await page.waitForTimeout(200);
  await page.locator('[data-lib-create="chinese"]').click();
  await page.locator('#createCount').fill('5');
  await page.locator('#createGo').click();
  await page.waitForTimeout(200);
  check('zh-task-created-5', (await page.evaluate(() => window.__WB.state.tasks.slice(-1)[0].items.length)) === 5);

  // 6. idempotency across reload + forced reinstall
  await page.reload();
  await page.waitForTimeout(300);
  check('persist-english-253', (await page.evaluate(() => window.__WB.state.english.entries.length)) === 253);
  check('persist-chinese-245', (await page.evaluate(() => window.__WB.state.chinese.entries.length)) === 245);
  await page.evaluate(() => { window.__WB.installSeed(); window.__WB.installZhSeed(); });
  await page.waitForTimeout(200);
  check('reinstall-no-dup', await page.evaluate(() => window.__WB.state.english.entries.length === 253 && window.__WB.state.chinese.entries.length === 245));
  check('seed-installed-checks', await page.evaluate(() => window.__WB.seedInstalled() && window.__WB.zhSeedInstalled()));

  // 7. merge mode: remove one chinese entry, reinstall restores it
  await page.evaluate(() => { window.__WB.state.chinese.entries.splice(3, 1); });
  check('zh-entry-removed', (await page.evaluate(() => window.__WB.state.chinese.entries.length)) === 244);
  await page.evaluate(() => window.__WB.installZhSeed());
  await page.waitForTimeout(200);
  check('zh-merge-restores-245', (await page.evaluate(() => window.__WB.state.chinese.entries.length)) === 245);

  // 8. no forbidden texts
  const fullText = await page.evaluate(() => document.body.innerText);
  check('no-parent-review-term', !/家长核对|待核对|去核对/.test(fullText));
  check('no-accuracy-term', !/正确率/.test(fullText));

  const passed = Object.values(results).filter(Boolean).length;
  const failed = Object.entries(results).filter(([, v]) => !v).map(([k]) => k);
  console.log('RESULT', JSON.stringify({ passed, total: Object.keys(results).length, failed, pageErrors: errors }, null, 2));
  await page.screenshot({ path: path.join(ROOT, 'v2-seed-learn.png'), fullPage: false });
  await browser.close();
  server.close();
  if (failed.length || errors.length) process.exit(1);
  console.log('SEED-ALL-PASS');
})().catch(e => { console.error('E2E-ERROR', e); process.exit(2); });
