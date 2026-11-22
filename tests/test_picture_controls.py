"""Exercise the Pictures panel with the actual plugin and deferred saves."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = r'''
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const vm = require("node:vm");
const state = {picturesFrom:{jid:"job", cid:"clip"}};
const image = {name:"logo.png", x:.5, y:.5, w:.34, rot:0, alpha:1};
const requests = [];
const fields = new Map();
let page, plugin;
const modal = { open:true, close(){ this.open=false; } };
const events = {};
const canvas = {
  dataset:{}, children:[], querySelectorAll(){ return this.children.slice(); },
  appendChild(el){ this.children.push(el); },
  addEventListener(type, fn){ events[type] = fn; },
};
const deletedTemplate = "removed-layout";
let savedTemplate = deletedTemplate;
const P = {
  css(){}, page(id, def){ page=def; }, add(id, def){ plugin=def; },
  state:()=>state, toast(){},
  api: async (url)=>url.endsWith("/overlay") ? {clip:{items:[{...image}], template:savedTemplate}} : {images:[], templates:[]},
  send(url, body){ const snapshot=JSON.parse(JSON.stringify(body)); return new Promise(resolve=>requests.push({snapshot, resolve})); },
};
const document = {
  getElementById(id){ return fields.get(id) || null; },
  addEventListener(){},
  createElement(){
    return {style:{}, dataset:{}, setAttribute(){}, append(){}, appendChild(){},
      remove(){ canvas.children.splice(canvas.children.indexOf(this),1); }};
  },
};
const context = {window:{PeakCut:P}, document, setTimeout, clearTimeout, Date, D:{jid:"job",cid:"clip"}, go(){}};
vm.runInNewContext(readFileSync(process.argv[1],"utf8"), context);
const html=page.view();
const frame = {getAttribute(){return this.src;}};
const slider = {value:"", getAttribute:()=>"w"};
fields.set("clipdlg",modal);
fields.set("pics_canvas",canvas);
fields.set("pics_frame",frame);
fields.set("pics_size",slider);
const turn = () => new Promise(resolve=>setImmediate(resolve));
(async()=>{
  const fails=[];
  async function check(label, fn) { try { await fn(); console.log("ok   "+label); } catch(e){ fails.push(label); console.error("FAIL "+label+"   "+e.message); } }
  await check("opening the picture editor closes the clip modal",()=>{
    plugin.act.openpics(); assert.equal(modal.open,false,"the previous modal still blocks the picture editor");
  });
  await page.load();
  plugin.after.drawSettings();
  await check("the main controls do not require numbers",()=>{
    const simple=html.slice(0, html.indexOf("<details"));
    assert.match(simple,/id="pics_size"[^>]*type="range"/);
    assert.match(simple,/id="pics_angle"[^>]*type="range"/);
    assert.match(simple,/data-act="pics_center"/);
    assert.doesNotMatch(simple,/type="number"/);
  });
  await check("the frame request excludes existing overlays",()=>{
    assert.match(frame.src,/[?&]base=true(?:&|$)/);
  });
  await check("the size slider updates the canvas and sends the latest value after a pending save",async()=>{
    assert.ok(events.input && events.change,"sliders have no live event wiring");
    slider.id="pics_size";
    slider.value="50";
    events.input({target:slider});
    assert.equal(canvas.children[0].style.width,"50%");
    events.change({target:slider});
    assert.equal(requests.length,1);
    slider.value="72";
    events.input({target:slider});
    events.change({target:slider});
    assert.equal(requests.length,1,"two saves can race");
    assert.equal(requests[0].snapshot.template,deletedTemplate);
    savedTemplate = "";
    requests[0].resolve({clip:{items:requests[0].snapshot.items, template:savedTemplate}});
    await turn();
    assert.equal(canvas.children[0].style.width,"72%","a stale save replaced the current preview");
    assert.equal(requests.length,2);
    assert.equal(requests[1].snapshot.items[0].w,.72);
    assert.equal(requests[1].snapshot.template,savedTemplate,"a cleared template was sent again");
    requests[1].resolve({clip:{items:requests[1].snapshot.items, template:savedTemplate}});
  });
  if(fails.length) process.exitCode=1;
})().catch(e=>{ console.error(e); process.exitCode=1; });
'''

if __name__ == "__main__":
    raise SystemExit(subprocess.run(
        ["node", "-e", SCRIPT, str(ROOT / "web" / "feat" / "pictures.js")], cwd=ROOT
    ).returncode)
