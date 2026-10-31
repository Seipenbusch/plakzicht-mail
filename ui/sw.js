// Plakzicht Mail als app installeren (Chrome/Edge). Er wordt bewust niets bewaard: mail komt altijd vers van de server.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => { /* niets onderscheppen: gewoon het netwerk */ });
