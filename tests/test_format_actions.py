"""Execute the caption catalogue's real save action without a browser."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
script = r'''
const fs=require('fs'), vm=require('vm'), assert=require('assert');
let page, plugin, sent=[], fail=false;
const brand={style:'bounce',font:'Bangers',hook_box:'112233',watermark:'unchanged'};
const P={css(){},add(n,d){plugin=d;},page(n,d){page=d;},toast(){},
  async api(path){if(path==='/api/brand')return {brand:{...brand}}; throw Error(path);},
  async send(path,body,method){if(fail)throw Error('offline'); sent.push({path,body,method}); return {brand:body.brand};},
  state(){return {};}};
const doc={getElementById(){return null;},querySelectorAll(){return [];},addEventListener(){}};
vm.runInNewContext(fs.readFileSync('web/feat/formats.js','utf8'),{window:{PeakCut:P},document:doc,
  setTimeout(){},clearTimeout(){},console,encodeURIComponent});
(async()=>{
const markup=page.view();
assert(markup.indexOf('id="fmt_looks"')<markup.indexOf('id="fmt_formats"'),'caption choices must be first');
assert(markup.indexOf('id="fmt_looks"')<markup.indexOf('id="fmt_formats"')&&/Not available yet/.test(markup),'clip types follow, and unavailable ones are said to be unavailable');
assert(!markup.includes('>Shapes<')&&!markup.includes('Check again'));
assert(plugin.act.fmtuse,'each look must offer a real save action');
const button={dataset:{style:'beast'},disabled:false,textContent:'Use as default'};
await plugin.act.fmtuse(button);
assert.strictEqual(sent.length,1);assert.strictEqual(sent[0].path,'/api/brand');
assert.strictEqual(sent[0].method,'PUT');
assert.deepStrictEqual(JSON.parse(JSON.stringify(sent[0].body.brand)),{...brand,style:'beast'},'keep every other brand field');
assert(!button.disabled,'save must release its button');
fail=true;await plugin.act.fmtuse(button);assert(!button.disabled,'failure must leave the button usable');
console.log('PASS caption choices lead, manual ideas are honest, default save preserves the brand, failure recovers');
})().catch(e=>{console.error(e);process.exit(1)});
'''
r = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True)
print(r.stdout, end='')
print(r.stderr, end='')
raise SystemExit(r.returncode)
