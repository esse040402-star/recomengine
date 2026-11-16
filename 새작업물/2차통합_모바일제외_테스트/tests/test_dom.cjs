const {JSDOM,VirtualConsole}=require('jsdom');
const {spawn}=require('child_process');const {once}=require('events');
const assert=require('assert');
(async()=>{
 const server=spawn('python',[require('path').join(__dirname,'serve_dom.py')]);
 server.stderr.on('data',()=>{});
 const port=String((await once(server.stdout,'data'))[0]).trim();const base='http://127.0.0.1:'+port;
 const vc=new VirtualConsole();const errors=[];vc.on('jsdomError',e=>{if(e.type!=='css-parsing'){errors.push(e.message);console.log('DOMERROR',e.message,e.cause?.stack)}});
 let dom;const cookieJar=new (require('jsdom').CookieJar)();
 try{
 dom=await JSDOM.fromURL(base,{resources:'usable',runScripts:'dangerously',pretendToBeVisual:true,cookieJar,virtualConsole:vc,beforeParse(w){
 w.structuredClone=structuredClone;w.AbortController=AbortController;w.AbortSignal=AbortSignal;w.matchMedia=()=>({matches:true,addEventListener(){},removeEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=()=>{};w.ResizeObserver=class{observe(){}disconnect(){}};w.IntersectionObserver=class{observe(){}disconnect(){}};
 w.fetch=async(url,options={})=>{const target=new URL(url,base).href;const res=await fetch(target,{...options,headers:{...options.headers,Cookie:await cookieJar.getCookieString(target)}});for(const c of res.headers.getSetCookie())await cookieJar.setCookie(c,target);return res;};
 }});
 const w=dom.window,d=w.document;const wait=async(fn)=>{for(let n=0;n<150;n++){if(fn())return;await new Promise(r=>setTimeout(r,50))}throw Error('wait timed out: '+(d.querySelector('#account-error')?.textContent||d.querySelector('#toast-root')?.textContent||d.querySelector('#main')?.textContent));};
 await wait(()=>d.querySelector('[data-action=track]'));
 console.log('WELCOME READY');
 const click=s=>{const el=d.querySelector(s);assert(el,'missing '+s);el.click();};
 click('[data-action=account-signup]');await wait(()=>d.querySelector('#account-form'));
 d.querySelector('[name=name]').value='통합테스트';d.querySelector('[name=email]').value='ui@example.com';d.querySelector('[name=password]').value='test-password-123';click('[data-action=account-submit]');
 await wait(()=>!d.querySelector('#account-form'));assert(d.querySelector('[data-action=track]'),'signup must stay in welcome');console.log('SIGNUP STAYS WELCOME');
 click('[data-action=track][data-value=gamer]');await wait(()=>d.querySelector('.question-title'));
 for(let i=0;i<7;i++){await wait(()=>d.querySelector('.survey-count')?.textContent.trim().startsWith(String(i+1)));click('[data-action=answer]');click('[data-action=next]');}
 await wait(()=>d.querySelector('.quick-result'));console.log('QUICK SAVED');click('[data-action=go-profile]');await wait(()=>d.querySelector('.profile-cover'));
 click('[data-action=profile-tab][data-value=play-profile]');await wait(()=>d.querySelector('[data-action=personal-view]'));console.log('QUICK PROFILE VISIBLE');
 click('[data-action=personal-survey]');await wait(()=>d.querySelector('.question-title'));
 for(let i=0;i<30;i++){await wait(()=>d.querySelector('.survey-count')?.textContent.trim().startsWith(String(i+1)));click('[data-action=answer]');click('[data-action=next]');}
 await wait(()=>d.querySelectorAll('[data-action=personal-view]').length===2);console.log('PROFILE30 SAVED AND VISIBLE');
 const views=d.querySelectorAll('[data-action=personal-view]');views[1].click();await wait(()=>d.querySelector('.dialog-body .insights'));assert.equal(d.querySelectorAll('.dialog-body .insights article').length,30);console.log('ALL30 ANSWERS SHOWN');
 click('[data-action=close]');await new Promise(r=>setTimeout(r,400));click('[data-action=profile-tab][data-value=settings]');await wait(()=>d.querySelector('[data-action=account-logout]'));click('[data-action=account-logout]');await wait(()=>d.querySelector('[data-action=track]'));
 click('[data-action=account-login]');await wait(()=>d.querySelector('#account-form'));d.querySelector('[name=email]').value='ui@example.com';d.querySelector('[name=password]').value='test-password-123';click('[data-action=account-submit]');await wait(()=>!d.querySelector('#account-form'));
 w.location.hash='profile';await wait(()=>d.querySelector('[data-action=profile-tab]'));click('[data-action=profile-tab][data-value=play-profile]');await wait(()=>d.querySelectorAll('[data-action=personal-view]').length===2);console.log('LOGIN RESTORES PROFILES');
 assert.deepEqual(errors,[]);console.log('DOM E2E PASS');
 }finally{dom?.window.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});
