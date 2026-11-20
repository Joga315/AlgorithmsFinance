// Optional browser QA: Node 22+ and Chrome. No npm packages required.
// Run from the submission folder: node audit/check_dashboards.cjs
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '..');
process.chdir(root);

async function main() {
  const executable = [process.env.CHROME_PATH,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    '/usr/bin/google-chrome', '/usr/bin/chromium'].find(p => p && fs.existsSync(p));
  if (!executable) throw Error('Set CHROME_PATH to a Chrome/Chromium executable.');
  const browser = spawn(executable, ['--headless=new', '--disable-gpu',
    '--disable-background-networking', '--disable-component-update', '--disable-extensions',
    '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0',
    '--user-data-dir=' + path.resolve('results/browser-profile'), 'about:blank'],
    {windowsHide:true, stdio:['ignore','ignore','pipe']});
  let ws;
  const deadline = setTimeout(() => {browser.kill(); process.exit(1)}, 55000);
  try {
    const address = await new Promise((resolve,reject) => {
      let buffer = '';
      browser.stderr.on('data', chunk => {
        buffer += chunk;
        const match = buffer.match(/DevTools listening on (ws:\/\/[^\s]+)/);
        if (match) resolve(match[1]);
      });
      browser.on('error',reject);
      browser.on('exit',code => reject(Error('Browser exited '+code)));
    });
    ws = new WebSocket(address);
    await new Promise((resolve,reject) => {
      ws.addEventListener('open',resolve,{once:true});
      ws.addEventListener('error',reject,{once:true});
    });
    let id = 0;
    const pending = new Map(), errors = [];
    ws.addEventListener('message',event => {
      const message = JSON.parse(event.data);
      if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails);
      const p = pending.get(message.id);
      if (p) {
        pending.delete(message.id);
        message.error ? p.reject(Error(JSON.stringify(message.error))) : p.resolve(message.result);
      }
    });
    const send = (method,params={},sessionId) => new Promise((resolve,reject) => {
      const n = ++id; pending.set(n,{resolve,reject});
      ws.send(JSON.stringify({id:n,method,params,...(sessionId?{sessionId}:{})}));
    });
    const {targetId} = await send('Target.createTarget',{url:'about:blank'});
    const {sessionId} = await send('Target.attachToTarget',{targetId,flatten:true});
    const cdp = (method,params) => send(method,params,sessionId);
    await cdp('Runtime.enable'); await cdp('Page.enable');
    await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
    const evaluate = async expression => {
      const result = await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
      if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
      return result.result.value;
    };
    async function load(file,selector) {
      await cdp('Page.navigate',{url:pathToFileURL(path.resolve(file)).href});
      for (let i=0;i<100;i++) {
        if (await evaluate(`document.querySelectorAll(${JSON.stringify(selector)}).length>0`)) return;
        await new Promise(resolve=>setTimeout(resolve,100));
      }
      throw Error('Dashboard did not render: '+file);
    }

    await load('audit/astra/Submissions/YildirimEyupTolgahan/dashboard.html','#rows tr');
    const astra = await evaluate(`(() => {
      const dataset=JSON.parse(document.getElementById('data').textContent);
      const element=id=>document.getElementById(id); let checked=0;
      for (const q of ['1','100']) {
        element('q').value=q; element('q').dispatchEvent(new Event('change'));
        const rates=[...element('rate').options].map(o=>o.value);
        if (rates.length!==(q==='1'?2:3)) throw Error('Astra infeasible rates');
        for (const rate of rates) for (const phase of ['prepare','batch','total']) for (const version of ['both','original','revised']) {
          for (const [id,value] of [['rate',rate],['phase',phase],['version',version]]) element(id).value=value;
          element('version').dispatchEvent(new Event('change'));
          const expected=dataset.points.filter(p=>p.q===Number(q)&&p.hits===Number(q)*Number(rate)/100&&p.phase===phase&&(version==='both'||p.version===version));
          const rows=[...document.querySelectorAll('#rows tr')];
          if (rows.length!==expected.length||document.querySelectorAll('#plot circle').length!==expected.length||document.querySelectorAll('#plot polyline').length!==(version==='both'?6:3)) throw Error('Astra row/curve count');
          for(const tr of rows){const c=[...tr.cells].map(cell=>cell.textContent);const p=expected.find(p=>p.method+' / '+p.version===c[0]&&p.n===Number(c[1]));if(!p||c[2]!==p.us.toPrecision(4))throw Error('Astra table disagrees with data')}
          checked++;
        }
      }
      return {filter_combinations_checked:checked,table_values_verified:true};
    })()`);

    await load('results/dashboard.html','#summary tbody tr');
    const working = await evaluate(`(() => {
      const dataset=JSON.parse(document.getElementById('dataset').textContent);
      const element=id=>document.getElementById(id);let checked=0;
      if(!element('hits').value)throw Error('Empty default selection');
      for(const q of [...new Set(dataset.rows.map(r=>r.q))]){
        element('queries').value=q;element('queries').dispatchEvent(new Event('change'));
        const rates=[...element('hits').options].map(o=>o.value);
        if(rates.length!==(q===1?2:3))throw Error('Infeasible rates');
        for(const n of [...new Set(dataset.rows.map(r=>r.n))])for(const rate of rates)for(const policy of ['unique','duplicates'])for(const metric of ['preparation_ms','query_batch_ms','total_ms'])for(const compare of [false,true]){
          for(const [id,value]of [['size',n],['hits',rate],['policy',policy],['metric',metric]])element(id).value=value;
          element('compare').checked=compare;element('compare').dispatchEvent(new Event('change'));
          const expected=dataset.rows.filter(r=>r.n===n&&r.q===q&&r.requested_hit_rate===Number(rate)&&r.duplicate_policy===policy&&(compare||r.version==='revised'));
          const rows=[...document.querySelectorAll('#summary tbody tr')],bars=[...document.querySelectorAll('#ranking .bar-item')];
          const growth=dataset.rows.filter(r=>r.q===q&&r.requested_hit_rate===Number(rate)&&r.duplicate_policy===policy&&(compare||r.version==='revised'));
          if(rows.length!==expected.length||bars.length!==expected.length||document.querySelectorAll('#chart circle').length!==growth.length||document.querySelectorAll('#chart polyline').length!==(compare?6:3)||document.querySelectorAll('#raw tbody tr').length!==expected.length*5)throw Error('Row/curve count');
          for(const tr of rows){const c=[...tr.cells].map(cell=>cell.textContent);const r=expected.find(r=>r.method===tr.dataset.method&&r.version===tr.dataset.version);if(!r||c[1]!==time(r.preparation_ms)||c[2]!==time(r.query_batch_ms)||c[3]!==time(r.total_ms)||c[4]!==(r.peak_traced_bytes/1024).toLocaleString('de-DE',{maximumFractionDigits:2}))throw Error('Table/data mismatch')}
          for(const bar of bars){const r=expected.find(r=>r.method===bar.dataset.method&&r.version===bar.dataset.version);if(!r||Number(bar.dataset.ms)!==r[metric])throw Error('Bar/data mismatch')}
          const winner=expected.filter(r=>r.version==='revised').sort((a,b)=>a[metric]-b[metric])[0];
          if(element('winner-name').textContent!==names[winner.method]||element('winner-time').textContent!==time(winner[metric]))throw Error('Winner/data mismatch');
          for(const point of document.querySelectorAll('#chart circle'))if(!Number.isFinite(Number(point.getAttribute('cx')))||!Number.isFinite(Number(point.getAttribute('cy'))))throw Error('Invalid chart coordinate');
          checked++;
        }
      }
      for(const [id,value]of [['queries','100'],['size',String(Math.max(...dataset.rows.map(r=>r.n)))],['policy','unique'],['metric','query_batch_ms']])element(id).value=value;
      element('queries').dispatchEvent(new Event('change'));element('hits').value='0.5';element('compare').checked=false;element('compare').dispatchEvent(new Event('change'));
      if(dataset.reuse&&element('reuse-panel').hidden)throw Error('Reuse evidence hidden');
      return {filter_combinations_checked:checked,table_values_verified:true,ranking_and_winner_verified:true};
    })()`);
    if(errors.length)throw Error(JSON.stringify(errors));
    const {cssContentSize} = await cdp('Page.getLayoutMetrics');
    const screenshot = await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,
      clip:{x:0,y:0,width:1440,height:Math.min(2500,cssContentSize.height),scale:1}});
    fs.writeFileSync('results/dashboard-check.png',Buffer.from(screenshot.data,'base64'));
    await cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
    const mobile=await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})');
    if(mobile.scrollWidth>mobile.width)throw Error('Page overflows on mobile');
    const report = {astra,working,mobile,javascript_errors:errors,screenshot:'results/dashboard-check.png'};
    fs.writeFileSync('results/dashboard_browser_check.json',JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
    await send('Browser.close');
  } finally {
    clearTimeout(deadline); if(ws)ws.close(); browser.kill();
  }
}
main().catch(error=>{console.error(error.message);process.exitCode=1});
