const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1100,height:850}});
 await page.addInitScript(()=>{
   window.SpeechRecognition=class {
     start(){window.rec=this;this.onstart?.();}
     stop(){this.stopped=true;}
     abort(){this.aborted=true;}
   };
 });
 const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(r.url().includes('/api/search/voice'))requests.push(r.postDataJSON());});
 const check=(x,m)=>{if(!x)throw Error(m);};
 const start=()=>page.locator('#voice-button').click();
 const result=(text,final)=>page.evaluate(({text,final})=>{const r=[{transcript:text}];r.isFinal=final;window.rec.onresult({results:[r]});},{text,final});
 const end=()=>page.evaluate(()=>window.rec.onend());
 await page.goto(process.env.WEB_BASE_URL || 'http://127.0.0.1:8011');
 await page.waitForFunction(()=>document.querySelectorAll('.card').length===40);
 check(await page.evaluate(()=>!window.rec),'must not record on page load');
 await page.locator('#search-input').fill('original query'); await start();
 check(await page.evaluate(()=>window.rec.lang==='vi-VN' && !window.rec.continuous && window.rec.interimResults),'Vietnamese config');
 check(await page.locator('#search-input').getAttribute('readonly')!==null,'readonly during capture');
 await result('giày',false); check(!requests.length,'interim must not search');
 await page.screenshot({path:'outputs/web/unified/microphone-listening.png'});
 await result('giày đen',true); await end();
 await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Đã tìm thấy'));
 check(requests.length===1 && requests[0].transcript==='giày đen','final transcript submitted once');
 check((await page.locator('.card h3').first().textContent()).includes('Metro'),'voice result');
 await page.locator('#voice-language').selectOption('en-US'); await start();
 check(await page.evaluate(()=>window.rec.lang==='en-US'),'English config');
 await result('running shoes',true); await start();
 check(await page.evaluate(()=>window.rec.stopped),'second mic click must stop');
 await end(); await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Đã tìm thấy'));
 check(requests.length===2 && requests[1].transcript==='running shoes','stop preserves final transcript');
 for(const [error,expected] of [['not-allowed','bị từ chối'],['network','Internet'],['no-speech','Chưa nghe'],['audio-capture','Không truy cập']]){
   await start(); await result('wrong interim',false);
   await page.evaluate(error=>window.rec.onerror({error}),error);
   check((await page.locator('#status').textContent()).includes(expected),'error '+error);
   check(await page.locator('#search-input').inputValue()==='running shoes','restore original on error');
   check(await page.locator('#voice-button').getAttribute('aria-pressed')==='false','reset capture on error');
 }
 check(requests.length===2,'errors cannot submit stale text');
 await start(); await result('unfinished',false); await end();
 check(requests.length===2,'interim-only session cannot search');
 check(await page.locator('#search-input').inputValue()==='running shoes','restore on silence');
 await start(); await page.evaluate(()=>window.oldRec=window.rec); await page.locator('#image-button').click();
 check(await page.evaluate(()=>window.oldRec.aborted),'image transition cancels capture');
 await page.evaluate(()=>{const r=[{transcript:'late result'}];r.isFinal=true;window.oldRec.onresult({results:[r]});window.oldRec.onend();});
 check(requests.length===2,'late event cannot search'); await page.keyboard.press('Escape');
 await start(); await page.locator('#all-products').click();
 check(await page.evaluate(()=>window.rec.aborted),'catalog cancels capture');
 await page.waitForFunction(()=>document.querySelectorAll('.card').length===40);
 await page.evaluate(()=>{window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;}); await start();
 check((await page.locator('#status').textContent()).includes('chưa hỗ trợ'),'unsupported browser feedback');
 check(requests.length===2,'unsupported cannot search');
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'outputs/web/unified/microphone-mobile.png',fullPage:true});
 check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile overflow');
 check(!errors.length,errors.join(';'));
 fs.writeFileSync('outputs/web/unified/microphone-checks.json',JSON.stringify({passed:true,recognition:'injected test double; no physical microphone or speech service verified',checks:['no automatic capture','vi-VN/en-US','interim vs final','stop','permission/network/no speech/device errors','restore text','cancel on mode/catalog','ignore late events','unsupported browser','mobile layout'],voiceRequests:requests},null,2));
 await browser.close(); console.log('Microphone lifecycle checks passed (injected recognition events).');
})().catch(e=>{console.error(e);process.exit(1);});
