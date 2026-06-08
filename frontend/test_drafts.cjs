const { chromium } = require('playwright');
const APP = 'http://localhost:5174';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(30000);
  
  // Capture ALL console output
  const logs = [];
  page.on('console', msg => logs.push({ t: msg.type(), txt: msg.text().substring(0, 200) }));
  page.on('pageerror', err => logs.push({ t: 'FATAL', txt: err.message }));

  await page.goto(APP + '/?tauri', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(5000);

  // Open modal
  await page.evaluate(() => {
    for (const b of document.querySelectorAll('button')) {
      if (b.textContent?.trim() === '登录') { b.click(); break; }
    }
  });
  await page.waitForTimeout(1500);

  // Switch to register
  await page.evaluate(() => {
    const overlay = document.querySelector('.modal-overlay');
    if (!overlay) return;
    const buttons = overlay.querySelectorAll('button');
    if (buttons.length >= 2) buttons[1].click();
  });
  await page.waitForTimeout(1000);

  // Use native setter for value
  await page.evaluate(() => {
    const inputs = document.querySelectorAll('.modal-overlay input');
    console.log('MODAL INPUTS:', inputs.length);
    if (inputs.length >= 4) {
      const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(inputs[0], 'testwriter');
      inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
      nativeSetter.call(inputs[1], 'test12345');
      inputs[1].dispatchEvent(new Event('input', { bubbles: true }));
      nativeSetter.call(inputs[2], 'test12345');
      inputs[2].dispatchEvent(new Event('input', { bubbles: true }));
      nativeSetter.call(inputs[3], 'Test Writer');
      inputs[3].dispatchEvent(new Event('input', { bubbles: true }));
    }
  });

  // Find and click submit button
  const btnInfo = await page.evaluate(() => {
    const overlay = document.querySelector('.modal-overlay');
    if (!overlay) return 'NO OVERLAY';
    const buttons = overlay.querySelectorAll('button');
    const info = [];
    for (const b of buttons) {
      info.push({
        text: b.textContent?.trim(),
        type: b.type,
        disabled: b.disabled,
      });
    }
    // Click the last button that says "注册"
    for (const b of buttons) {
      if (b.textContent?.trim() === '注册') {
        b.click();
        return { clicked: true, buttons: info };
      }
    }
    return { clicked: false, buttons: info };
  });
  console.log('Submit button:', JSON.stringify(btnInfo));
  
  await page.waitForTimeout(5000);

  // Check results
  const state = await page.evaluate(() => {
    const r = {};
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      r[k] = localStorage.getItem(k)?.substring(0, 100);
    }
    return r;
  });
  console.log('localStorage:', JSON.stringify(state, null, 2));

  // Show console errors
  const errors = logs.filter(l => l.t === 'error' || l.t === 'FATAL');
  if (errors.length > 0) {
    console.log('\nConsole errors:');
    errors.forEach(e => console.log('  [' + e.t + ']', e.txt));
  }

  await browser.close();
})();
