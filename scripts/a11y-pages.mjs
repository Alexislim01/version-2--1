import { chromium } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { writeFile } from 'node:fs/promises';
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Users/angel/AppData/Local/ms-playwright/chromium-1248/chrome-win64/chrome.exe'});
const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage(),results=[];
await page.emulateMedia({reducedMotion:'reduce'});
await page.goto('http://127.0.0.1:5178/');await page.getByRole('heading',{name:'Burning activity calendar'}).waitFor({timeout:60000});
for(const theme of ['dark','light']){
  if(theme==='light')await page.getByRole('button',{name:'Switch to light mode'}).click();
  for(const view of ['Fire explorer','Harmonization','Insights','Method & sources']){
    await page.getByRole('button',{name:view,exact:true}).click();
    const report=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    results.push({theme,view,violations:report.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,message:n.failureSummary}))}))});
  }
}
await writeFile('artifacts/a11y-pages.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results));await browser.close();
if(results.some(r=>r.violations.length))process.exitCode=1;
