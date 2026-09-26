// promo.html を seek(t) で 1 フレームずつ描画して PNG 連番に書き出す
// usage: node render.js <html> <outDir> [t1,t2,...]   (時刻リスト省略時は 30fps 全フレーム)
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const [html, out, list] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('file:///' + path.resolve(html).replace(/\\/g, '/') + '?render', { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => Promise.all([...document.images].map((i) => i.decode())));
  const dur = await page.evaluate(() => window.DURATION);
  const times = list ? list.split(',').map(Number) : Array.from({ length: dur * 30 }, (_, i) => i / 30);
  for (let i = 0; i < times.length; i++) {
    await page.evaluate((t) => window.seek(t), times[i]);
    const name = list ? `t_${times[i]}.png` : `frame_${String(i).padStart(4, '0')}.png`;
    await page.screenshot({ path: path.join(out, name) });
  }
  console.log('rendered', times.length);
  await browser.close();
})();
