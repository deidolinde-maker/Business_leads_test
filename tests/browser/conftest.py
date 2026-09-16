import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest


HTML = '''<!doctype html><html><meta charset="utf-8"><body>
<header><span id="autocomplete_city_name" data-item="77">Москва</span></header>
<form id="lead">
  <button type="button" id="choose-region">Регион</button>
  <span id="autocomplete_city_name" class="autocomplete-city-name" data-item="CITY_ID">CITY_NAME</span>
  <input id="office" type="checkbox" style="position:absolute;opacity:0"><label for="office">В офис</label>
  <input id="address" required><input id="phone" required>
  <input id="consent" type="checkbox" required><label for="consent">Согласие</label>
  <button id="submit" type="submit">Отправить</button>
</form>
<div id="region-dialog" hidden>
  <input id="city-input" class="popup-select-city__input" placeholder=" ">
  <a class="region_item region_link" href="/other" id="999">Самарская область</a>
  <a class="region_item region_link" href="/samara" id="36401">Самара</a>
</div>
<div id="thanks" hidden>Спасибо</div>
<script>
const form=document.querySelector('#lead');
const indicator=form.querySelector('#autocomplete_city_name');
const fault=new URLSearchParams(location.search).get('fault');
document.querySelector('#choose-region').onclick=()=>document.querySelector('#region-dialog').hidden=false;
document.querySelector('#office').onchange=()=>{
  if(fault==='city-reset') {indicator.dataset.item='77';indicator.textContent='Москва';}
};
form.onsubmit=async event=>{
  event.preventDefault();
  const businessControl=document.querySelector('#office');
  const isBusiness=businessControl instanceof HTMLSelectElement
    ? businessControl.value==='\u0414\u043b\u044f \u0431\u0438\u0437\u043d\u0435\u0441\u0430'
    : businessControl.checked;
  const payload={form:'lead-fixture', business:isBusiness,
            region:indicator.dataset.item==='36401'?'samara-fixture':'moscow-fixture'};
  if(fault==='payload')payload.region='moscow-fixture';
  if(fault==='ordinary')payload.business=false;
  if(fault==='false-thanks'){document.querySelector('#thanks').hidden=false;return;}
  try {
    const response=await fetch('/leads', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(fault==='duplicate')await fetch('/leads', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(response.ok)document.querySelector('#thanks').hidden=false;
  } catch(e) {document.querySelector('#thanks').hidden=false;}
};
</script></body></html>'''


@pytest.fixture
def local_site():
    state = {"received": [], "gets": [], "reject": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            state["gets"].append(self.path)
            path = urlsplit(self.path).path
            city = "Москва" if path == "/plain/business" else "Самара"
            html = HTML.replace("CITY_ID", "77" if city == "Москва" else "36401").replace("CITY_NAME", city)
            if 'fault=wrong-choice' in self.path:
                html = html.replace('id="36401">Самара', 'id="36500">Самара')
            if 'fault=radio' in self.path:
                html = html.replace('<input id="office" type="checkbox" style="position:absolute;opacity:0">',
                                    '<input id="home" type="radio" name="Place" checked><label for="home">Home</label>'
                                    '<input id="office" type="radio" name="Place">')
            if 'fault=select' in self.path:
                html = html.replace(
                    '<input id="office" type="checkbox" style="position:absolute;opacity:0"><label for="office">В офис</label>',
                    '<select id="office"><option value="В квартиру">В квартиру</option>'
                    '<option value="Для бизнеса">Для бизнеса</option></select>',
                )
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            payload = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            state["received"].append(json.loads(payload))
            reply = {"status": "rejected" if state["reject"] else "accepted"}
            if state["reject"]:
                reply["invalid_fields"] = [{"field": "Phone", "message": "sensitive test data must not be exported"}]
            body = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", state
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
