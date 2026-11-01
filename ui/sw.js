// Plakzicht Mail als app installeren (Chrome/Edge/Safari, ook op de telefoon). Er wordt bewust niets bewaard:
// mail komt altijd vers van de server. Meldingen op de telefoon lopen via deze service worker.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => { /* niets onderscheppen: gewoon het netwerk */ });
self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    const c = list[0];
    if (c) { c.postMessage({ t: 'note', mail: e.notification.data }); return c.focus(); }
    return self.clients.openWindow('/index.html');
  }));
});
