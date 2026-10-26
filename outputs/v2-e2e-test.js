// E2E acceptance for family-learning-workbench-v2.html
const fs = require('fs');
const path = require('path');
const http = require('http');
const { chromium } = require('playwright-core');

const ROOT = 'C:/Users/sPark/WorkBuddy/2026-10-09-16-55-37/outputs';
const HTML = fs.readFileSync(path.join(ROOT, 'family-learning-workbench-v2.html'), 'utf8');

(async () => {
  // serve the page over a real loopback http server: matches real usage and keeps
  // Chrome's private-network rules identical to opening the file locally.
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
  process.on('unhandledRejection', e => console.log('REJECT', e && e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

  await page.goto('http://127.0.0.1:' + port + '/');

  const results = {};
  const check = (name, cond) => { results[name] = !!cond; if (!cond) console.log('FAIL:', name); };

  // view: today default
  check('today-default-active', await page.evaluate(() => document.getElementById('today').classList.contains('active')));
  check('date-shown', (await page.locator('#todayDate').textContent() || '').length > 4);

  // navigate learn
  await page.evaluate(() => window.__WB.route('learn'));
  check('learn-active', await page.evaluate(() => document.getElementById('learn').classList.contains('active')));
  check('three-modules', await page.locator('#learn .module').count() === 3);
  check('stat-english-seeded', /253 个单词/.test(await page.locator('#statEnglish').textContent()));
  check('stat-chinese-seeded', /245 个字词/.test(await page.locator('#statChinese').textContent()));
  check('no-seed-ui-entry', await page.evaluate(() => !document.getElementById('seedGrade3') && !document.querySelector('[data-seed]') && !/一键初始化/.test(document.body.innerText)));

  // import english via modal
  await page.locator('[data-module="english"]').first().click();
  await page.locator('[data-module-import="english"]').first().click();
  check('import-modal-open', await page.evaluate(() => document.getElementById('wImport').open));
  await page.evaluate(() => window.__WB.setImportText('desk,书桌,第1单元\nblackboard,黑板,第1单元\nwindow,窗户,第2单元\nfriend,朋友,第3单元\nbad row!!?,x,第9单元\ndesk,书桌,第1单元'));
  await page.locator('#importParse').click();
  check('import-parse-preview', /新增 4 条/.test(await page.locator('#wImport #wbImportPreview').textContent()));
  check('import-parse-invalid', /无效 1/.test(await page.locator('#wImport #wbImportPreview').textContent()));
  check('import-parse-dup', /跳过重复 1/.test(await page.locator('#wImport #wbImportPreview').textContent()));
  await page.locator('#importCommit').click();
  await page.waitForTimeout(300);
  check('import-committed', (await page.evaluate(() => window.__WB.state.english.entries.length)) === 257);
  check('import-batch-logged', (await page.evaluate(() => window.__WB.state.importLog.length)) === 3);
  check('import-in-module', await page.evaluate(() => document.getElementById('moduleEnglish').classList.contains('active')));
  await page.evaluate(() => window.__WB.route('learn'));
  check('back-to-learn', await page.evaluate(() => document.getElementById('learn').classList.contains('active')));
  check('stat-english-updated', /257 个单词/.test(await page.locator('#statEnglish').textContent()));

  // library
  await page.locator('[data-module="english"]').first().click();
  check('library-open', await page.evaluate(() => document.getElementById('moduleEnglish').classList.contains('active')));
  check('library-rows', await page.locator('#moduleEnglish .library-row').count() === 257);
  // search filter
  await page.locator('[data-lib-search="english"]').fill('win');
  await page.waitForTimeout(200);
  check('library-search-1', await page.locator('#moduleEnglish .library-row').count() === 1);
  await page.locator('[data-lib-search="english"]').fill('');
  await page.waitForTimeout(200);
  check('library-search-reset', await page.locator('#moduleEnglish .library-row').count() === 257);
  // select items and start
  await page.locator('[data-lib-item="english"]').first().check();
  await page.locator('[data-lib-item="english"]').nth(1).check();
  check('lib-selected-count', /已选 2 项/.test(await page.locator('#libSelCount_english').textContent()));
  await page.locator('[data-lib-start="english"]').click();
  check('play-open', await page.evaluate(() => document.getElementById('play').classList.contains('active')));
  check('play-count-1', /第 1 \/ 2 题/.test(await page.locator('#playCount').textContent()));

  // play engine: manual advance through all items
  const statuses = [];
  for (let i = 0; i < 2; i++) {
    await page.locator('#playNext').click();
    await page.waitForTimeout(750);
    statuses.push(await page.locator('#playCount').textContent());
  }
  check('play-done-view', await page.evaluate(() => document.getElementById('playDone').classList.contains('active')));
  check('done-stats', /2\/2/.test(await page.locator('#doneBody').textContent()));
  check('done-no-judgement', !/正确率|判定/.test(await page.locator('#doneBody').textContent()));

  // create task via range dialog (auto mode with mocked speech)
  await page.evaluate(() => {
    // speechSynthesis is a read-only IDL attribute; use defineProperty to replace it
    Object.defineProperty(window, 'speechSynthesis', {
      value: {
        cancel() {},
        speak(u) { setTimeout(() => u.onstart && u.onstart(), 30); }
      },
      configurable: true
    });
    window.SpeechSynthesisUtterance = function (t) { this.text = t; };
  });
  await page.evaluate(() => window.__WB.route('learn'));
  await page.locator('[data-module="english"]').first().click();
  await page.locator('[data-lib-create="english"]').click();
  check('create-modal-open', await page.evaluate(() => document.getElementById('wCreate').open));
  await page.locator('#createCount').fill('3');
  await page.locator('#createGo').click();
  check('play-auto-started', await page.evaluate(() => document.getElementById('play').classList.contains('active')));
  // countdown should begin after playback confirms (neural TTS may take ~1-2s on first synthesis)
  await page.waitForFunction(() => /^\d+$/.test((document.getElementById('playTimer').textContent || '').trim()), null, { timeout: 8000 });
  const timerText = await page.locator('#playTimer').textContent();
  check('countdown-starts', /^\d+$/.test(timerText) && Number(timerText) >= 7);
  // skip current
  await page.locator('#playSkip').click();
  await page.waitForTimeout(400);
  check('skip-recorded', (await page.evaluate(() => window.__WB.state.tasks.slice(-1)[0].skips.length)) === 1);
  check('play-count-2', /第 2 \/ 3 题/.test(await page.locator('#playCount').textContent()));
  // manual next interplay: no double advance
  const beforeIdx = await page.evaluate(() => window.__WB.state.tasks.slice(-1)[0].index);
  await page.locator('#playNext').click();
  await page.locator('#playNext').click(); // second click within lock window
  await page.waitForTimeout(600);
  const afterIdx = await page.evaluate(() => window.__WB.state.tasks.slice(-1)[0].index);
  check('advance-lock', afterIdx - beforeIdx === 1);
  // pause
  await page.locator('#playPause').click({ force: true });
  check('paused-status', /已暂停/.test(await page.locator('#playStatus').textContent()));
  const cd = await page.evaluate(() => window.__WB.play.countdown);
  check('pause-clears-countdown', cd === 0);
  await page.locator('#playPause').click(); // resume
  await page.waitForTimeout(200);
  check('resumed', await page.evaluate(() => window.__WB.state.tasks.slice(-1)[0].status) === 'active');
  await page.locator('#playEnd').click();
  check('end-completes', (await page.evaluate(() => window.__WB.state.tasks.slice(-1)[0].status)) === 'completed');
  check('done-remaining-note', /1 题未播报/.test(await page.locator('#doneBody').textContent()));

  // ===== new today-task system =====
  await page.evaluate(() => window.__WB.route('today'));
  // independent tasks are created only from selected presets
  await page.evaluate(() => {
    const W = window.__WB.state;
    const off = String((new Date().getDay() + 1) % 7); // a weekday that is not today, so presets do not auto-generate
    W.presets.push({ id: 'p-man', name: '课外阅读', kind: 'manual', note: '', enabled: true, createdAt: Date.now(), rule: { weekdays: [off], startDate: null, endDate: null } });
    W.presets.push({ id: 'p-man-2', name: '整理书包', kind: 'manual', note: '', enabled: true, createdAt: Date.now(), rule: { weekdays: [off], startDate: null, endDate: null } });
    W.tasks.push({ id: 'legacy-module', module: 'english', kind: 'module', dateKey: window.__WB.todayKey(), title: '旧英语练习', status: 'completed', createdAt: 1 });
    window.__WB.route('today');
  });
  await page.locator('#addTaskBtn').click();
  check('candidate-open', await page.evaluate(() => document.getElementById('wCandidate').open));
  check('candidate-no-search-or-dragzone', await page.locator('#wCandidate input[type="search"], #candDropzone').count() === 0);
  check('candidate-preset-list', await page.locator('#candList input[type="checkbox"]').count() === 2);
  await page.locator('#candList input[type="checkbox"]').first().check();
  await page.locator('#candList input[type="checkbox"]').nth(1).check();
  await page.locator('#candBatchAdd').click();
  await page.locator('#wCandidate').evaluate(d => d.close());
  check('candidate-adds-selected-manuals', await page.evaluate(() => {
    const ts = window.__WB.state.tasks.filter(t => t.dateKey === window.__WB.todayKey() && t.presetId);
    return ts.length === 2 && ts.every(t => t.kind === 'manual' && !t.module);
  }));
  const g1 = await page.evaluate(() => { window.__WB.route('today'); return window.__WB.state.tasks.length; });
  const g2 = await page.evaluate(() => { window.__WB.route('today'); return window.__WB.state.tasks.length; });
  check('preset-idempotent', g1 === g2);
  check('module-task-excluded-today', await page.locator('#todayTasks').innerText().then(t => !t.includes('旧英语练习')));
  check('module-task-excluded-heat', await page.evaluate(() => window.__WB.doneCountByDate()[window.__WB.todayKey()] || 0) === 0);
  // manual task checkbox + heat recalc (target by task id: list re-sorts on toggle, .first() would hit another row)
  const lvOf = c => Number((c.match(/lv(\d)/) || [0, 0])[1]);
  const heatTargetId = await page.evaluate(() => window.__WB.state.tasks.filter(t => t.kind === 'manual')[0].id);
  const baseLv = lvOf(await page.locator('.heat-cell.today').getAttribute('class'));
  await page.locator('input[data-task-toggle="' + heatTargetId + '"]').check();
  const afterCheck = lvOf(await page.locator('.heat-cell.today').getAttribute('class'));
  check('heat-up-on-check', afterCheck === baseLv + 1);
  await page.locator('input[data-task-toggle="' + heatTargetId + '"]').uncheck();
  const afterUncheck = lvOf(await page.locator('.heat-cell.today').getAttribute('class'));
  check('heat-down-on-uncheck', afterUncheck === baseLv);
  // cancel then re-add reuses instance
  const manualId = await page.evaluate(() => window.__WB.state.tasks.filter(t => t.kind === 'manual')[0].id);
  await page.evaluate(id => {
    const t = window.__WB.state.tasks.find(x => x.id === id);
    t.status = 'cancelled';
    window.__WB.route('today');
  }, manualId);
  check('cancel-no-revive', (await page.evaluate(id => { window.__WB.route('today'); window.__WB.route('today'); return window.__WB.state.tasks.find(x => x.id === id).status; }, manualId)) === 'cancelled');
  await page.locator('#addTaskBtn').click();
  check('candidate-readd-shown', await page.locator('#candList [data-day-readd]').count() === 1);
  await page.locator('#candList [data-day-readd]').click();
  check('readd-restores-pending', (await page.evaluate(id => window.__WB.state.tasks.find(x => x.id === id).status, manualId)) === 'pending');
  check('readd-single-instance', (await page.evaluate(id => window.__WB.state.tasks.filter(x => x.id === id).length, manualId)) === 1);
  await page.evaluate(() => document.getElementById('wCandidate').close());
  check('today-tasks-render', await page.locator('#todayTasks .task').count() >= 2);
  check('all-visible-tasks-manual', await page.evaluate(() => [...document.querySelectorAll('#todayTasks input[data-task-toggle]')].length === document.querySelectorAll('#todayTasks .task').length));

  // records
  await page.evaluate(() => window.__WB.route('wrecords'));
  check('records-active', await page.evaluate(() => document.getElementById('wrecords').classList.contains('active')));
  check('records-english-filter', await page.locator('[data-rfilter="english"]').isVisible());
  await page.locator('[data-rfilter="english"]').click();
  const recHtml = await page.locator('#wrecordList').textContent();
  check('records-english-items', /英语听写/.test(recHtml));
  check('records-objective', !/正确率/.test(recHtml));
  await page.locator('[data-rfilter="phonics"]').click();
  check('records-phonics-empty', /拼读模块还没有训练记录/.test(await page.locator('#wrecordList').textContent()));

  // phonics module opens
  await page.evaluate(() => window.__WB.route('learn'));
  await page.locator('[data-module="phonics"]').first().click();
  check('phonics-visible', await page.evaluate(() => !document.getElementById('phonicsApp').hidden));
  check('phonics-no-wb-view', !(await page.evaluate(() => document.getElementById('learn').classList.contains('active'))));
  check('phonics-lands-courses', await page.evaluate(() => document.getElementById('courses').classList.contains('active') && !document.getElementById('phonicsApp').hidden));
  await page.locator('#phonicsApp .grid [data-enter-course="C02"]').click();
  await page.waitForTimeout(300);
  check('phonics-detail-view', await page.evaluate(() => document.getElementById('detail').classList.contains('active') && !document.getElementById('phonicsApp').hidden));
  const selectedCount = await page.locator('#phonicsApp #items .word-item').count();
  check('phonics-c02-all-40', selectedCount === 40);
  check('phonics-no-manual-picking', await page.evaluate(() => !document.querySelector('#phonicsApp #items input[type="checkbox"]') && !document.getElementById('selectVisible') && !document.getElementById('selectCourse') && !document.getElementById('search') && !document.getElementById('lessonFilter') && !document.getElementById('sort')));
  check('phonics-hash', /ph\/course-detail\/C02/.test(await page.evaluate(() => location.hash)));
  check('phonics-practice-mode-present', await page.locator('#phonicsApp #practiceMode').count() === 1);
  check('train-group-buttons', await page.locator('#phonicsApp [data-pick-group]').count() >= 3);
  await page.locator('#phonicsApp #practiceMode').selectOption('flash');
  await page.waitForTimeout(200);
  check('flash-no-group-buttons', await page.locator('#phonicsApp [data-pick-group]').count() === 0);
  await page.locator('#phonicsApp #trainStart').click();
  await page.waitForTimeout(300);
  check('phonics-flash-mode-opens', await page.evaluate(() => document.getElementById('flash').classList.contains('active')));
  await page.locator('#phonicsApp [data-go="detail"]').click();
  await page.waitForTimeout(200);
  await page.locator('#phonicsApp #practiceMode').selectOption('train');
  await page.waitForTimeout(200);
  // train mode = ordered learning with group bulk pick
  await page.locator('#phonicsApp [data-pick-group]').first().click();
  await page.waitForTimeout(200);
  const pickedWords = await page.locator('#phonicsApp #items .word-item.picked b').allTextContents();
  check('train-group-picked-highlight', pickedWords.length > 0);
  await page.locator('#phonicsApp #trainStart').click();
  await page.waitForTimeout(300);
  check('train-ordered-first', (await page.locator('#phonicsApp #trainWord').textContent()).trim() === pickedWords[0].trim());
  // back to workbench nav
  await page.evaluate(() => window.__WB.route('today'));
  check('back-to-wb-hides-phonics', await page.evaluate(() => document.getElementById('phonicsApp').hidden));
  check('back-to-today', await page.evaluate(() => document.getElementById('today').classList.contains('active')));

  // more: settings + backup export availability
  await page.evaluate(() => window.__WB.route('more'));
  check('more-active', await page.evaluate(() => document.getElementById('more').classList.contains('active')));
  await page.locator('[data-open-dialog="wAudio"]').first().click();
  check('audio-modal-open', await page.evaluate(() => document.getElementById('wAudio').open));
  check('audio-separate-voice-selects', await page.locator('#enVoice').count() === 1 && await page.locator('#zhVoice').count() === 1);
  check('audio-rate-selects', await page.locator('#enRate').count() === 1 && await page.locator('#zhRate').count() === 1);
  check('audio-test-buttons', await page.locator('#audioTestEn').count() === 1 && await page.locator('#audioTestZh').count() === 1);
  check('audio-engine-select', await page.locator('#audioEngine').count() === 1);
  check('audio-engine-status-shown', (await page.locator('#audioEngineStatus').textContent() || '').length > 2);
  await page.locator('#enRate').selectOption('0.8');
  await page.locator('#zhRate').selectOption('0.7');
  await page.locator('#enGap').selectOption('10');
  await page.locator('#audioSave').click();
  check('gap-saved', (await page.evaluate(() => window.__WB.state.settings.enGap)) === 10);
  check('rate-saved-separately', await page.evaluate(() => window.__WB.state.settings.enRate === 0.8 && window.__WB.state.settings.zhRate === 0.7));
  check('utterance-lang-rate-differ', await page.evaluate(() => {
    const en = window.__WB.makeUtterance('apple', 'english');
    const zh = window.__WB.makeUtterance('山坡', 'chinese');
    return en.lang === 'en-US' && zh.lang === 'zh-CN' && en.rate === 0.8 && zh.rate === 0.7;
  }));
  check('audio-summary-updated', /英语 10 秒/.test(await page.locator('#audioSummary').textContent()));

  // responsive overflow checks
  const overflow = {};
  for (const w of [390, 768, 1024, 1440]) {
    await page.setViewportSize({ width: w, height: 900 });
    await page.evaluate(() => window.__WB.route('today'));
    overflow.today = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    await page.evaluate(() => window.__WB.route('learn'));
    const o2 = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    await page.locator('[data-module="english"]').first().click();
    const o3 = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    await page.evaluate(() => window.__WB.route('wrecords'));
    const o4 = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    overflow[w] = overflow.today || o2 || o3 || o4;
  }
  check('no-overflow-390', !overflow[390]);
  check('no-overflow-768', !overflow[768]);
  check('no-overflow-1024', !overflow[1024]);
  check('no-overflow-1440', !overflow[1440]);

  // mobile nav visible at 390
  await page.setViewportSize({ width: 390, height: 844 });
  check('mobile-nav-visible', await page.evaluate(() => getComputedStyle(document.querySelector('.mobile-nav')).display !== 'none'));
  await page.setViewportSize({ width: 1280, height: 900 });

  // persistence across reload
  await page.reload();
  await page.waitForTimeout(300);
  check('persist-entries', (await page.evaluate(() => window.__WB.state.english.entries.length)) === 257);
  check('persist-tasks', (await page.evaluate(() => window.__WB.state.tasks.length)) >= 3);

  // migration v1 -> v2
  const mig = await page.evaluate(() => {
    localStorage.setItem('family-learning-workbench-state-v1', JSON.stringify({
      settings: { enGap: 8, zhGap: 6 }, child: { name: '小宇', grade: '三年级' },
      english: { entries: [{ id: 'e1', word: 'apple', meaning: '苹果', unit: 'U1' }], batches: [] },
      chinese: { entries: [{ id: 'c1', text: '天', reading: 'tiān', meaning: 'sky', unit: 'U1' }], batches: [] },
      importLog: [], plans: [],
      tasks: [{ id: 't-legacy', module: 'english', source: 'temp', planId: null, dateKey: '2026-10-20', rangeLabel: 'U1', units: ['U1'], count: 1, mode: 'auto', gap: 8, items: [{ id: 'e1', text: 'apple' }], index: 1, status: 'done', skips: [], audioErrors: [], startedAt: null, endedAt: null, activeMs: 60, createdAt: 1 }]
    }));
    location.reload();
    return 'ok';
  });
  check('migration-triggered', mig === 'ok');
  await page.waitForTimeout(800);
  const migState = await page.evaluate(() => {
    const s = window.__WB.state;
    const t = s.tasks.find(x => x.id === 't-legacy');
    const cell = document.querySelector('[data-heat-date="2026-10-20"]');
    return { schema: s.schema_version, kind: t && t.kind, status: t && t.status, cell: cell && cell.className };
  });
  check('migration-schema2', migState.schema === 2);
  check('migration-kind-module', migState.kind === 'module');
  check('migration-status-completed', migState.status === 'completed');
  check('migration-heat-excludes-module', /lv0/.test(migState.cell || ''));
  await page.evaluate(() => localStorage.removeItem('family-learning-workbench-state-v1'));
  await page.reload();
  await page.waitForTimeout(400);

  // forbidden texts
  const fullText = await page.evaluate(() => document.body.innerText);
  check('no-parent-review-term', !/家长核对|待核对|去核对/.test(fullText));
  check('no-accuracy-term', !/正确率/.test(fullText));

  const passed = Object.values(results).filter(Boolean).length;
  const failed = Object.entries(results).filter(([, v]) => !v).map(([k]) => k);
  console.log('RESULT', JSON.stringify({ passed, total: Object.keys(results).length, failed, pageErrors: errors }, null, 2));

  await page.screenshot({ path: path.join(ROOT, 'v2-final-home.png'), fullPage: false });
  await browser.close();
  server.close();
  if (failed.length || errors.length) process.exit(1);
  console.log('ALL-PASS');
})().catch(e => { console.error('E2E-ERROR', e); process.exit(2); });
