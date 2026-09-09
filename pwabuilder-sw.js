// Service Worker ของ Bullion Ledger
// กลยุทธ์:
// - หน้าแอป (navigate requests) -> network-first: มีเน็ตได้เวอร์ชันล่าสุดเสมอ, ไม่มีเน็ต fallback เป็น cache
// - ราคาหุ้น/FX/ปฏิทินเศรษฐกิจ -> ไม่แตะ cache เลย ปล่อยตรงไปเน็ตเสมอ (ข้อมูลต้องสดเท่านั้น)
// - ไฟล์อื่น ๆ (ฟอนต์, Chart.js) -> stale-while-revalidate

const SW_VERSION = 'v2'; // เพิ่มเลขนี้เมื่ออยากล้าง cache เก่าทั้งหมดแบบตั้งใจ (ไม่บังคับต้องทำทุกครั้งที่แก้ index.html)
const CACHE_NAME = `bullion-ledger-${SW_VERSION}`;

// ไฟล์หลักของแอปที่ต้อง cache ไว้ตั้งแต่ตอนติดตั้ง (App Shell)
const APP_SHELL = [
  './',
  './index.html',
  './manifest.json'
];

// โดเมนที่ห้าม cache เด็ดขาด เพราะเป็นข้อมูลสด
const NEVER_CACHE_HOSTS = [
  'finnhub.io',
  'api.frankfurter.app',
  's3.tradingview.com',
  'tradingview-widget.com',
  'tradingview.com'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      // ใช้ allSettled กันไม่ให้ install ล้มทั้งหมด ถ้าไฟล์ใดไฟล์หนึ่งโหลดไม่ได้ (เช่นตอนไม่มีเน็ตตอนติดตั้งครั้งแรก)
      await Promise.allSettled(APP_SHELL.map((url) => cache.add(url)));
    })()
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      // ลบ cache เวอร์ชันเก่าทิ้งทุกครั้งที่มีเวอร์ชันใหม่ activate
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      );
      await self.clients.claim();
    })()
  );
});

// ให้หน้าเว็บสั่งให้ SW ใหม่ทำงานทันที (ใช้คู่กับระบบอัพเดตอัตโนมัติใน index.html)
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  let url;
  try { url = new URL(req.url); } catch (e) { return; }

  // ข้อมูลสด (ราคาหุ้น/FX/ปฏิทิน) -> ปล่อยผ่านตรงไปเน็ตเสมอ ไม่ยุ่งกับ cache
  if (NEVER_CACHE_HOSTS.some((h) => url.hostname.endsWith(h))) {
    return;
  }

  if (req.mode === 'navigate') {
    // หน้า HTML หลัก: network-first เพื่อให้ได้เวอร์ชันล่าสุดทันทีที่มีเน็ต
    event.respondWith(
      (async () => {
        try {
          const fresh = await fetch(req);
          const cache = await caches.open(CACHE_NAME);
          cache.put('./index.html', fresh.clone());
          return fresh;
        } catch (err) {
          const cache = await caches.open(CACHE_NAME);
          const cached = await cache.match('./index.html');
          return cached || Response.error();
        }
      })()
    );
    return;
  }

  // ไฟล์อื่น ๆ (CSS/JS/ฟอนต์): stale-while-revalidate
  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      const cached = await cache.match(req);
      const networkFetch = fetch(req)
        .then((resp) => {
          if (resp && resp.ok) cache.put(req, resp.clone());
          return resp;
        })
        .catch(() => null);
      return cached || (await networkFetch) || Response.error();
    })()
  );
});
