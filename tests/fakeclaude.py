import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_POST(self):
        n=int(self.headers.get('Content-Length') or 0); j=json.loads(self.rfile.read(n))
        if self.headers.get('x-api-key')!='sk-ant-test':
            self.send_response(401); self.end_headers(); self.wfile.write(b'{"error":{"message":"invalid x-api-key"}}'); return
        p=j['messages'][0]['content']
        if 'Zeg: werkt' in p: t='werkt'
        elif 'Vat deze e-mail' in p: t='- Klant vraagt of de levertijd korter kan\n- Ze openen over drie weken\n- Offerte OFF-2026-121'
        elif 'Schrijf een antwoord' in p: t='Beste Koffiebar Bonen,\n\nDank voor uw bericht. We kijken of de levertijd korter kan en laten het u morgen weten.\n\nMet vriendelijke groet,\nMedewerker A'
        elif 'Vertaal' in p: t='Hi,\n\nThanks for the quote. Can the delivery time be shorter? We open in three weeks.'
        elif 'passende labels' in p: t='{"labels": ["Nieuwe aanvragen"], "map": "Archief", "reden": "Het gaat om een offerte."}'
        elif 'offerte-aanvraag' in p: t='{"Klant/bedrijf": "Koffiebar Bonen", "E-mail": "hallo@koffiebarbonen.nl", "Product": "Etiketten", "Gewenste leverdatum": "binnen drie weken"}'
        else: t='Verbeterde tekst.'
        out=json.dumps({"content":[{"type":"text","text":t}],"usage":{"input_tokens":len(p)//4,"output_tokens":len(t)//4}}).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(out))); self.end_headers(); self.wfile.write(out)
import sys
ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1]) if len(sys.argv) > 1 else 8791), H).serve_forever()
