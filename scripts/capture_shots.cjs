/* Actual screenshots of the supplied viewer; no changes to its simulation or UI. */
const fs = require('fs');
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const output = path.join(root, 'evidence', 'shots');

async function main() {
  fs.mkdirSync(output, { recursive: true });
  const launch = { headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] };
  if (process.env.CHROME_PATH) launch.executablePath = process.env.CHROME_PATH;
  const browser = await chromium.launch(launch);
  const manifest = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1100 }, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('file://' + path.join(root, 'viewer/index.html') + '#lab');
    await page.waitForFunction(() => window.__vlms);
    const data = read('evidence/viewer.json');
    const chosen = read('evidence/fix.json').chosen.policy;

    async function loadLab(doc, name) {
      await page.locator('#labFile').setInputFiles({ name, mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(doc)) });
      await page.waitForFunction(name => document.querySelector('#labSrc').textContent.includes(name), name);
    }
    async function screenshot(file, time, reference) {
      if (await page.evaluate(() => window.__vlms.st.playing)) await page.locator('#play').click();
      const state = await page.evaluate(({ t, lead }) => {
        const app = window.__vlms;
        app.st.playing = false;
        app.st.t = t;
        const f = Math.round(t / window.SimCore.DT);
        const ego = app.R.actors.findIndex(a => a.id === 'ego');
        const offset = (f * app.R.actors.length + ego) * 7;
        Object.assign(app.rig, { follow: false, tx: app.R.F[offset] + lead, tz: app.R.F[offset + 1],
          ty: 0, dist: 62, yaw: 2.15, pitch: 0.85 });
        return { time: t, events: app.R.events.filter(e => e.a === 'ego' || e.b === 'ego') };
      }, { t: time, lead: file === 'hazard_brake.png' ? 12 : 2 });
      // Clear the camera tween through the viewer's regular pointer handler.
      await page.locator('#stage canvas').dispatchEvent('pointerdown', { pointerId: 1, clientX: 900, clientY: 500 });
      await page.locator('#stage canvas').dispatchEvent('pointerup', { pointerId: 1 });
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(output, file) });
      manifest.push({ file, ...reference, ...state });
    }

    await loadLab(data, 'viewer.json');
    for (const mode of ['bus_bypass', 'crosswalk_block', 'replay']) {
      const i = data.runs.findIndex(r => r.label === mode);
      if (i < 0) throw new Error('Missing viewer run: ' + mode);
      await page.locator('#labRuns button').nth(i).click();
      const event = await page.evaluate(() => window.__vlms.R.events.find(e => e.a === 'ego' || e.b === 'ego'));
      if (!event) throw new Error('Expected event: ' + mode);
      await screenshot(mode + '.png', event.t, { source: 'viewer.json', run_id: data.runs[i].id, mode });
    }

    const rescued = await page.evaluate(({ runs, chosen }) => {
      const S = window.SimCore;
      return runs.findIndex(r => r.label === 'bus_bypass' &&
        !S.rollout({ params: r.params, policy: { ...S.POLICY, ...chosen }, ego: 'planner', others: 'reactive' })
          .events.some(e => e.a === 'ego' || e.b === 'ego'));
    }, { runs: data.runs, chosen });
    if (rescued < 0) throw new Error('No saved bus-bypass run rescued by chosen policy');
    const fixed = structuredClone(data);
    const original = fixed.runs[rescued];
    const baseline = await page.evaluate(r => window.SimCore.rollout({ params: r.params, policy: r.policy,
      ego: 'planner', others: 'reactive' }).events.find(e => e.a === 'ego' || e.b === 'ego'), original);
    original.policy = null;  // unpinned runs use data.policy; their ghost uses baseline_policy
    await loadLab(fixed, 'viewer.json · chosen policy on saved run');
    await page.locator('#labRuns button').nth(rescued).click();
    const baselineReadout = await page.locator('#labRead b').nth(2).innerText();
    if (baselineReadout.startsWith('không')) throw new Error('The ghost must show the baseline collision');
    await page.locator('#labRead').scrollIntoViewIfNeeded();
    await screenshot('fix_ghost.png', baseline.t, { source: 'viewer.json + fix.json: chosen.policy',
      run_id: original.id, policy: chosen, baseline_event: baseline, baseline_readout: baselineReadout });

    await page.evaluate(() => window.__vlms.go(9));
    await page.locator('#stuOpen').setInputFiles(path.join(root, 'hazard.json'));
    await page.waitForFunction(() => JSON.parse(document.querySelector('#stuJson').value).hazards[0]?.trig === 45);
    await screenshot('hazard_brake.png', 1.05, { source: 'hazard.json', mode: 'L1 braking after trigger' });
    const studioDoc = JSON.parse(await page.locator('#stuJson').inputValue());
    const hazard = read('hazard.json');
    if (JSON.stringify(studioDoc.hazards) !== JSON.stringify(hazard.hazards)) {
      // Object property ordering is immaterial; compare field values.
      for (const [key, value] of Object.entries(hazard.hazards[0])) {
        if (studioDoc.hazards[0][key] !== value) throw new Error('Studio changed hazard ' + key);
      }
    }
    if (errors.length) throw new Error(errors.join('\n'));
    fs.writeFileSync(path.join(output, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
    console.log('Saved ' + manifest.length + ' viewer screenshots and manifest.');
  } finally {
    await browser.close();
  }
}
main().catch(e => { console.error(e); process.exitCode = 1; });
