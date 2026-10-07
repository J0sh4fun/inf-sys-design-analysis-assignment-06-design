const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
(async () => {
 const browser = await chromium.launch({channel:'msedge',headless:true});
 const page = await browser.newPage({viewport:{width:1440,height:1000}});
 // Deterministic speech events test the UI pipeline, not a physical microphone.
 await page.addInitScript(() => {
   window.SpeechRecognition = class {
     start(){ window.testRecognition=this; this.onstart?.(); }
     stop(){ this.onend?.(); }
     abort(){}
   };
 });
 const errors=[]; page.on('pageerror', e=>errors.push(e.message));
 const check=(yes,msg)=>{if(!yes)throw Error(msg);};
 await page.goto(process.env.WEB_BASE_URL || 'http://127.0.0.1:8011');
 await page.waitForFunction(()=>document.querySelectorAll('.card').length===40);
 await page.locator('.card img').first().waitFor();
 await page.screenshot({path:'outputs/web/unified/desktop.png',fullPage:true});
 await page.locator('#search-input').fill('giày đen');
 await page.locator('#search-input').press('Enter');
 await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Đã tìm thấy'));
 check((await page.locator('.card h3').first().textContent()).includes('Metro'),'Vietnamese text top result');
 check((await page.locator('.score').first().textContent()).includes('2.0000'),'text score');
 const viNames=await page.locator('.card h3').allTextContents();
 await page.locator('#search-input').fill('black shoes'); await page.locator('#search-input').press('Enter');
 await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Đã tìm thấy'));
 check(JSON.stringify(viNames)===JSON.stringify(await page.locator('.card h3').allTextContents()),'English parity');
 await page.locator('#voice-button').click();
 await page.evaluate(() => { const r=[{transcript:'tìm cho tôi giày chạy bộ'}]; r.isFinal=true; window.testRecognition.onresult({results:[r]}); window.testRecognition.onend(); });
 await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Đã tìm thấy'));
 check((await page.locator('.card h3').first().textContent()).includes('Sprint'),'voice top result');
 check((await page.locator('#diagnostic-content').textContent()).includes('voice'),'voice mode');
 await page.screenshot({path:'outputs/web/unified/voice.png',fullPage:true});
 await page.locator('#image-button').click(); await page.locator('.sample').nth(1).click(); await page.locator('#image-search').click();
 await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Đã tìm thấy'));
 check((await page.locator('.card h3').first().textContent()).includes('Trail'),'image top result');
 check((await page.locator('.score').first().textContent()).includes('1.0000'),'image score');
 await page.locator('summary').click(); await page.screenshot({path:'outputs/web/unified/image.png',fullPage:true});
 await page.locator('#image-button').click(); await page.locator('#image-upload').setInputFiles('datasets/images/product_02.png');
 await page.locator('#image-search').click(); await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Đã tìm thấy'));
 check((await page.locator('.score').first().textContent()).includes('1.0000'),'uploaded image score');
 check((await page.locator('#results-context').textContent()).includes('product_02.png'),'uploaded image filename');
 check((await page.locator('#results-context').textContent()).includes('CLIP ViT-B/32'),'CLIP model label');
 await page.screenshot({path:'outputs/web/unified/upload.png',fullPage:true});
 await page.locator('.details-button').first().click(); check(await page.locator('#product-dialog').isVisible(),'detail modal'); await page.keyboard.press('Escape');
 await page.locator('#search-input').fill('zzzzzz'); await page.locator('#search-input').press('Enter');
 await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Đã tìm thấy'));
 check(await page.locator('.empty').isVisible(),'no results');
 await page.locator('#search-input').fill(''); await page.locator('#search-input').press('Enter'); check((await page.locator('#status').textContent()).includes('Hãy nhập'),'empty validation');
 await page.setViewportSize({width:390,height:844}); await page.locator('#all-products').click();
 await page.waitForFunction(()=>document.querySelectorAll('.card').length===40);
 await page.screenshot({path:'outputs/web/unified/mobile.png',fullPage:true});
 check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile overflow');
 await page.locator('#image-button').click(); await page.screenshot({path:'outputs/web/unified/mobile-image.png'});
 check(await page.evaluate(()=>document.querySelector('#image-dialog').scrollWidth<=document.querySelector('#image-dialog').clientWidth),'modal overflow');
 await page.keyboard.press('Escape');
 const images=await page.locator('.card img').evaluateAll(async imgs=>{imgs.forEach(img=>{img.loading='eager';}); await Promise.all(imgs.map(img=>img.decode().catch(()=>{}))); return imgs.map(img=>({src:img.src,valid:img.naturalWidth>128}));});
 check(images.every(i=>i.valid),'catalog real images loaded'); check(!errors.length,errors.join(';'));
 fs.writeFileSync('outputs/web/unified/browser-checks.json',JSON.stringify({passed:true,checks:['catalog 40 products','Vietnamese and English parity','voice transcript and score','sample image inference and score','arbitrary image upload inference','detail Escape','no results','empty input','390px layout','mobile image modal','no JS errors'],images},null,2));
 console.log('All browser checks passed'); await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
