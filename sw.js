// خدمة عاملة بسيطة لتطبيق سوق 48
// الإستراتيجية: عند وجود إنترنت، يُجلب أحدث إصدار من كل ملف وتُحدَّث النسخة المخزّنة تلقائياً (حتى تصل آخر التعديلات دون أي إجراء يدوي).
// عند عدم وجود إنترنت، يُستخدم ما هو مخزَّن محلياً حتى يعمل التطبيق بالكامل بدون اتصال.

var CACHE_NAME = 'souq48-cache-v1';
var CORE_FILES = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', function(event){
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache){
      return cache.addAll(CORE_FILES).catch(function(){ /* تجاهل أي ملف يتعذّر تخزينه مبدئياً، لا يوقف التثبيت */ });
    })
  );
});

self.addEventListener('activate', function(event){
  event.waitUntil(
    caches.keys().then(function(names){
      return Promise.all(
        names.filter(function(n){ return n !== CACHE_NAME; }).map(function(n){ return caches.delete(n); })
      );
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(event){
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request).then(function(response){
      var copy = response.clone();
      caches.open(CACHE_NAME).then(function(cache){ cache.put(event.request, copy); });
      return response;
    }).catch(function(){
      return caches.match(event.request).then(function(cached){
        return cached || caches.match('./index.html');
      });
    })
  );
});
