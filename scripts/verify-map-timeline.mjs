import {chromium,expect} from '@playwright/test';
import {options} from './browser-options.mjs';
const browser=await chromium.launch(options);
try{
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 await page.goto((process.env.BASE_URL||'http://127.0.0.1:5173')+'?dates='+encodeURIComponent(JSON.stringify([['2019-01-01','2019-01-03'],['2019-02-01','2019-02-02']])));
 const timeline=page.getByRole('region',{name:'Fire activity timeline'}),slider=timeline.getByRole('slider',{name:'Timeline position'});
 await expect(timeline).toBeVisible({timeout:60000});
 await expect(slider).toHaveAttribute('max','4');
 await expect(timeline).toContainText('All selected dates');
 await timeline.getByRole('button',{name:'Next day',exact:true}).click();
 await expect(slider).toHaveValue('0');await expect(page.locator('.map-day-selection')).toContainText('1 Jan 2019');
 await slider.focus();await page.keyboard.press('ArrowRight');
 await expect(slider).toHaveValue('1');await expect(page.locator('.map-day-selection')).toContainText('2 Jan 2019');
 await timeline.getByRole('button',{name:'Previous day',exact:true}).click();
 await timeline.getByRole('combobox',{name:'Playback speed'}).selectOption('4');
 await timeline.getByRole('button',{name:'Play timeline',exact:true}).click();
 await expect(slider).toHaveValue('4');
 await expect(timeline.getByRole('button',{name:'Play timeline',exact:true})).toBeVisible();
 await expect(page.locator('.map-day-selection')).toContainText('2 Feb 2019');
 await timeline.getByRole('button',{name:'Play timeline',exact:true}).click();
 await timeline.getByRole('button',{name:'Pause timeline',exact:true}).click();
 const paused=await slider.inputValue();await page.waitForTimeout(400);await expect(slider).toHaveValue(paused);
 await timeline.getByRole('button',{name:'All dates',exact:true}).click();
 await expect(page.locator('.map-day-selection')).toHaveCount(0);
 for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
  await page.setViewportSize(viewport);await timeline.scrollIntoViewIfNeeded();
  const bar=await timeline.boundingBox();expect(bar.x).toBeGreaterThanOrEqual(0);expect(bar.x+bar.width).toBeLessThanOrEqual(viewport.width);
  for(const selector of ['.map-bottom','.map-draw-tools']){const box=await page.locator(selector).boundingBox();expect(box.y+box.height).toBeLessThanOrEqual(bar.y);}
 }
 await page.setViewportSize({width:1440,height:900});
 await page.getByRole('button',{name:'Historical record',exact:true}).click();
 await expect(timeline).toBeVisible({timeout:90000});
 await expect(slider).toHaveAttribute('max','215');
 const historical=await slider.inputValue();await timeline.getByRole('button',{name:'Next month',exact:true}).click();
 await expect(slider).toHaveValue(String(+historical+1));
 await expect(page.locator('[data-historical-month][aria-pressed=true]')).toHaveAttribute('data-historical-month','2003-04');
 await timeline.getByRole('combobox',{name:'Playback speed'}).selectOption('4');
 await timeline.getByRole('button',{name:'Play timeline',exact:true}).click();await expect(slider).not.toHaveValue(String(+historical+1));
 await timeline.getByRole('button',{name:'Pause timeline',exact:true}).click();
 for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
  await page.setViewportSize(viewport);await timeline.scrollIntoViewIfNeeded();
  const bar=await timeline.boundingBox();expect(bar.x).toBeGreaterThanOrEqual(0);expect(bar.x+bar.width).toBeLessThanOrEqual(viewport.width);
  for(const selector of ['.final-map-legend','.map-bottom','.map-draw-tools']){const box=await page.locator(selector).boundingBox();expect(box.y+box.height).toBeLessThanOrEqual(bar.y);}
 }
 console.log('PASS: explorer disjoint-date scrub/keyboard/steps/play/pause/end/speed/reset; historical month/calendar synchronization and playback; desktop/mobile bounds and map control separation');
}finally{await browser.close();}
