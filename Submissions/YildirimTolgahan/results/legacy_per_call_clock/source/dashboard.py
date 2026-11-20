"""Build a standalone interactive HTML dashboard from saved measurements."""
import argparse
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Search methods | Tolgahan Yildirim</title>
<style>
:root{font-family:system-ui,sans-serif;color:#20343c;background:#f2f5f3;font-size:15px}body{max-width:1250px;margin:40px auto;padding:0 22px}h1{font-size:clamp(28px,5vw,44px);letter-spacing:-1.5px;margin:5px 0 12px}h2{font-size:20px}header p{max-width:850px;line-height:1.65;color:#52646b}.eyebrow{font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#39745d}section,.filters{background:white;border:1px solid #dce4df;border-radius:12px;padding:22px;margin:20px 0}.filters{display:flex;gap:20px;flex-wrap:wrap}label{display:grid;gap:7px;font-size:13px;font-weight:600}select{padding:9px 12px;min-width:145px;border:1px solid #bccdc5;border-radius:6px;background:white;color:inherit}svg{width:100%;height:auto;min-width:480px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:12px;white-space:nowrap}th,td{text-align:right;padding:10px;border-bottom:1px solid #e3eae6}th:first-child,td:first-child{text-align:left}th{color:#52646b;font-weight:600}caption{text-align:left;margin-bottom:12px;color:#52646b}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;line-height:1.7}a{color:#176947}summary{cursor:pointer;font-weight:600}.note{font-size:13px;color:#52646b;line-height:1.7}.legend{display:flex;gap:20px;flex-wrap:wrap}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px}footer{margin:30px 0;color:#52646b;font-size:12px}#status{font-size:13px;color:#52646b}
</style></head><body>
<header><span class="eyebrow">Algorithms in Finance / Phase 1</span><h1>Search methods, measured.</h1>
<p>Linear search, binary search and hash-set membership on identical integer IDs and ordered queries. Compare the original and revised implementations, including preparation costs.</p></header>
<div class="filters"><label>Queries per batch<select id="queries"></select></label><label>Requested hit rate<select id="hits"></select></label><label>Input IDs<select id="policy"></select></label><label>Elapsed time<select id="metric"><option value="total_ms">Total</option><option value="preparation_ms">Preparation</option><option value="query_batch_ms">Query batch</option></select></label></div>
<p id="status" aria-live="polite"></p>
<section><h2>Elapsed time against input length</h2><div class="legend"><span><i class="dot" style="background:#176947"></i>Linear</span><span><i class="dot" style="background:#346dba"></i>Binary</span><span><i class="dot" style="background:#a25827"></i>Hash set</span><span>Dashed: original · Solid: revised</span></div><div class="scroll"><svg id="chart" viewBox="0 0 1000 380" role="img" aria-label="Elapsed time in milliseconds per complete batch, against input length"></svg></div><p class="note">Median of five repeats; short calls are aggregated. Each call prepares a fresh structure. Input lengths use logarithmic spacing; the elapsed-time axis is linear. Hover over a point for its value.</p></section>
<section><h2>Timing and memory</h2><div class="scroll"><table id="summary"></table></div><p class="note">All times are milliseconds per complete batch of the selected query count. Memory is a separate tracemalloc run: current and peak traced Python allocations, with preparation and returned output included; pre-existing input and queries excluded. 1 KiB = 1024 bytes. These values are neither process RSS nor mathematical auxiliary space. Median total may differ from the sum of component medians.</p></section>
<section><details><summary>Raw repeats for this selection</summary><p class="note">Each value is milliseconds per invocation, obtained by summing the timed calls and dividing by the call count. Validation occurs outside the clock readings.</p><div class="scroll"><table id="raw"></table></div></details></section>
<section><details><summary>Environment and measurement protocol</summary><pre id="environment"></pre></details></section>
<section><h2>Saved source data</h2><p><a download href="__JSON_LINK__">Measurements and environment (JSON)</a> · <a download href="summary.csv">Summary CSV</a> · <a download href="raw_repeats.csv">Raw repeats CSV</a></p><p class="note">This page embeds the saved measurements. Changing a filter never executes a benchmark. Regenerate the HTML after generating a new measurement file. CSV links expect the benchmark's companion files in the same directory as this HTML.</p></section>
<footer>Tolgahan Yildirim · Local measurements describe this machine and workload; they do not prove asymptotic bounds.</footer>
<script type="application/json" id="dataset">__DATA__</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('dataset').textContent);
const el=id=>document.getElementById(id), colors={linear:'#176947',binary:'#346dba',hash_set:'#a25827'};
const names={linear:'Linear',binary:'Binary',hash_set:'Hash set'};
const unique=key=>[...new Set(data.rows.map(r=>r[key]))].sort((a,b)=>typeof a==='number'?a-b:String(a).localeCompare(String(b)));
function options(id,key,label){for(const value of unique(key)){const option=document.createElement('option');option.value=value;option.textContent=label(value);el(id).append(option)}}
options('queries','q',String);options('hits','requested_hit_rate',v=>`${v*100}%`);options('policy','duplicate_policy',String);
el('queries').value=unique('q').includes(100)?'100':String(unique('q')[0]);
el('environment').textContent=JSON.stringify(data.metadata,null,2);
function table(id,head,rows,caption){const t=el(id);t.replaceChildren();const c=document.createElement('caption');c.textContent=caption;t.append(c);const h=t.createTHead().insertRow();head.forEach(value=>{const th=document.createElement('th');th.scope='col';th.textContent=value;h.append(th)});const b=t.createTBody();rows.forEach(row=>{const tr=b.insertRow();row.forEach(value=>{tr.insertCell().textContent=value})})}
function svg(tag,attrs,text){const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))node.setAttribute(k,v);if(text!==undefined)node.textContent=text;el('chart').append(node);return node}
function draw(rows,key){const chart=el('chart');chart.replaceChildren();const sizes=[...new Set(rows.map(r=>r.n))].sort((a,b)=>a-b);const lo=Math.log10(sizes[0]),hi=Math.log10(sizes.at(-1));const x=n=>90+(hi===lo?0.5:(Math.log10(n)-lo)/(hi-lo))*860;const max=Math.max(...rows.map(r=>r[key]))*1.12||1;const y=v=>310-v/max*260;
for(let i=0;i<=5;i++){const v=max*i/5;svg('line',{x1:90,x2:950,y1:y(v),y2:y(v),stroke:'#e0e8e3'});svg('text',{x:80,y:y(v)+4,'text-anchor':'end',fill:'#52646b','font-size':12},v.toPrecision(3))}
for(const n of sizes)svg('text',{x:x(n),y:338,'text-anchor':'middle',fill:'#52646b','font-size':12},n.toLocaleString());
svg('text',{x:520,y:370,'text-anchor':'middle',fill:'#52646b','font-size':13},'Input length n (logarithmic spacing)');svg('text',{x:90,y:23,fill:'#52646b','font-size':13},'Milliseconds per complete batch');
for(const method of ['linear','binary','hash_set'])for(const version of ['original','revised']){const group=rows.filter(r=>r.method===method&&r.version===version).sort((a,b)=>a.n-b.n);const points=group.map(r=>`${x(r.n)},${y(r[key])}`).join(' ');svg('polyline',{points,fill:'none',stroke:colors[method],'stroke-width':2.5,'stroke-dasharray':version==='original'?'7 5':'none'});for(const r of group){const node=svg('circle',{cx:x(r.n),cy:y(r[key]),r:version==='original'?6:3.5,fill:version==='original'?'white':colors[method],stroke:colors[method],'stroke-width':2});const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=`${names[method]} / ${version}: n=${r.n}, ${r[key].toPrecision(5)} ms`;node.append(title)}}}
const fmt=v=>Number(v).toFixed(6);
function update(){const rows=data.rows.filter(r=>r.q===Number(el('queries').value)&&r.requested_hit_rate===Number(el('hits').value)&&r.duplicate_policy===el('policy').value).sort((a,b)=>a.n-b.n||a.method.localeCompare(b.method)||a.version.localeCompare(b.version));
const rates=[...new Set(rows.map(r=>r.actual_hit_rate*100))];el('status').textContent=`${rows.length} measurements · achieved hit rate: ${rates.join(', ')}% · ${data.metadata.settings.repeats} repeats · q=1 cannot represent a 50% hit rate (rounded to one hit).`;
draw(rows,el('metric').value);table('summary',['Method / version','n','q','Actual hits','Prep (ms)','Batch (ms)','Total (ms)','Current (KiB)','Peak (KiB)'],rows.map(r=>[`${names[r.method]} / ${r.version}`,r.n,r.q,`${r.actual_hit_rate*100}%`,fmt(r.preparation_ms),fmt(r.query_batch_ms),fmt(r.total_ms),(r.current_traced_bytes/1024).toFixed(2),(r.peak_traced_bytes/1024).toFixed(2)]),'Same input and query order for every method and version.');
table('raw',['Method / version','n','Repeat','Calls','Prep (ms)','Batch (ms)','Total (ms)'],rows.flatMap(r=>r.raw_repeats.map(s=>[`${names[r.method]} / ${r.version}`,r.n,s.repeat,s.calls,fmt(s.preparation_ms),fmt(s.query_batch_ms),fmt(s.total_ms)])),'Raw repeats underlying the medians above.');}
document.querySelectorAll('select').forEach(select=>select.addEventListener('change',update));update();
</script></body></html>'''


def build(source, output):
    data = json.loads(source.read_text(encoding="utf-8"))
    if not data.get("rows"):
        raise ValueError("No saved measurements to display")
    payload = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c")
    import os
    link = Path(os.path.relpath(source, output.parent)).as_posix()
    page = TEMPLATE.replace("__DATA__", payload).replace("__JSON_LINK__", html.escape(link, quote=True))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    print(f"Dashboard: {output.resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE / "results" / "measurements.json")
    parser.add_argument("--output", type=Path, default=HERE / "results" / "dashboard.html")
    args = parser.parse_args()
    build(args.results, args.output)


if __name__ == "__main__":
    main()
