import {inShape, type Observation, type Shape} from './engine.ts';
import {inBBox} from './selection.ts';

export type Layer = 'modis'|'viirs'|'synthetic';
export type FinalPoint = Observation & {scan:number;track:number;bright_ti5:number;is_synthetic:boolean;sim_source:string;sim_parent_modis:string;sim_run:number;layer:Layer};
export type CalendarMonth = {year:number;month:number;value:number;source:string;median:number;anomaly_pct:number|null;frp?:number;points?:number};
export type Download = {name:string;group:string;url:string;bytes:number;sha256:string};
export type FinalManifest = {schema:number;country:string;method:string;scale:string;generated:string;columns:string[];calendar:CalendarMonth[];shards:{year:number;url:string;counts:Record<Layer,number>}[];reports:string;downloads:Download[];inputs:{file:string;bytes:number;sha256:string}[];notes:string[]};
export type ReportRow = Record<string,string|number|boolean|null>;
export type FinalReports = Record<'loyo'|'simulation'|'handover'|'summary',Record<string,ReportRow[]>>;
export type Area = {id:string;label:string;bbox:number[];shape?:Shape};
export const areas:Area[] = [
 {id:'national',label:'Malaysia',bbox:[99,0,120,8]},
 {id:'peninsular',label:'Peninsular Malaysia',bbox:[99,0,105,8]},
 {id:'borneo',label:'Malaysian Borneo',bbox:[108,0,120,8]},
];
export const monthKey=(year:number,month:number)=>`${year}-${String(month).padStart(2,'0')}`;
export const monthName=(key:string)=>new Date(key+'-01T00:00:00Z').toLocaleDateString('en-GB',{month:'long',year:'numeric',timeZone:'UTC'});
export const fmt=(n:number|null|undefined,digits=0)=>n==null||!Number.isFinite(n)?'—':n.toLocaleString('en-GB',{maximumFractionDigits:digits});
export const methodNames:Record<string,string>={raw:'No conversion',daynight_k:'Day/night multiplier',strat_k:'Stratified multiplier',fusion:'Fusion (original)',fusion_G1:'Fusion G1',fusion_G2:'Fusion G2',fusion_G3:'Fusion G3'};
export const sourceName=(source:string)=>({estimated:'Fusion G1 estimate',observed:'Observed S-NPP',observed_partial:'Partial S-NPP coverage',simulated:'Synthetic run 1'}[source]||source);
export const layerName:Record<Layer,string>={modis:'Observed Aqua MODIS',viirs:'Observed S-NPP VIIRS',synthetic:'Synthetic VIIRS (run 1)'};

export function decodeFinal(rows:(string|number|boolean|null)[][],layer:Layer):FinalPoint[]{
 return rows.map(r=>({latitude:Number(r[0]),longitude:Number(r[1]),acq_date:String(r[2]),acq_time:String(r[3]).padStart(4,'0'),satellite:String(r[4]),instrument:String(r[5]),confidence:String(r[6]),frp:Number(r[7]),daynight:String(r[8]),brightness:Number(r[9]),scan:Number(r[10]),track:Number(r[11]),bright_ti5:Number(r[12]),is_synthetic:r[13]===true,sim_source:String(r[14]),sim_parent_modis:String(r[15]),sim_run:Number(r[16]),layer}));
}
export const pointInArea=(p:FinalPoint,area:Area)=>area.id==='national'||inBBox(p.longitude,p.latitude,area.bbox)&&inShape(p,area.shape);
const median=(values:number[])=>{const v=[...values].sort((a,b)=>a-b),i=Math.floor(v.length/2);return v.length?(v.length%2?v[i]:(v[i-1]+v[i])/2):0;};

/** Keep the delivered national model expectations separate from a stochastic point realization. */
export function finalCalendar(manifest:FinalManifest,points:FinalPoint[],area:Area,daynight:string):CalendarMonth[]{
 const sums=new Map<string,{count:number;frp:number}>();
 for(const point of points){
  const early=point.acq_date<'2012-01-01';
  if((early?point.layer!=='synthetic':point.layer!=='viirs')||!pointInArea(point,area)||(daynight!=='all'&&point.daynight!==daynight))continue;
  const key=point.acq_date.slice(0,7),v=sums.get(key)||{count:0,frp:0};v.count++;v.frp+=point.frp;sums.set(key,v);
 }
 const national=area.id==='national'&&daynight==='all';
 const calendar=manifest.calendar.map(row=>{const sum=sums.get(monthKey(row.year,row.month))||{count:0,frp:0};return {...row,value:national?row.value:sum.count,points:sum.count,frp:sum.frp,source:row.source==='estimated'&&!national?'simulated':row.source};});
 if(national)return calendar;
 const baseline=new Map<number,number>();
 for(let month=1;month<=12;month++)baseline.set(month,median(calendar.filter(row=>row.month===month&&row.source!=='observed_partial').map(row=>row.value)));
 return calendar.map(row=>{const normal=baseline.get(row.month)!;return {...row,median:normal,anomaly_pct:normal>0?(row.value-normal)/normal*100:null};});
}

export function pointCSV(points:FinalPoint[]){
 const columns=['latitude','longitude','brightness','bright_ti4','scan','track','acq_date','acq_time','satellite','instrument','confidence','version','bright_t31','bright_ti5','frp','daynight','type','is_synthetic','sim_source','sim_parent_modis','sim_run'];
 const escape=(value:unknown)=>{const s=String(value??'');return /[",\n\r]/.test(s)?'"'+s.replaceAll('"','""')+'"':s;};
 const rows=points.map(p=>({latitude:p.latitude,longitude:p.longitude,brightness:p.layer==='modis'?p.brightness:'',bright_ti4:p.layer!=='modis'?p.brightness:'',scan:p.scan,track:p.track,acq_date:p.acq_date,acq_time:p.acq_time,satellite:p.satellite,instrument:p.instrument,confidence:p.confidence,version:p.is_synthetic?'SIM1.0':'',bright_t31:p.layer==='modis'?p.bright_ti5:'',bright_ti5:p.layer!=='modis'?p.bright_ti5:'',frp:p.frp,daynight:p.daynight,type:0,is_synthetic:p.is_synthetic,sim_source:p.sim_source,sim_parent_modis:p.sim_parent_modis,sim_run:p.is_synthetic?p.sim_run:''}));
 return columns.join(',')+'\n'+rows.map(row=>columns.map(key=>escape(row[key as keyof typeof row])).join(',')).join('\n');
}

export function saveDownload(content:string|Blob,name:string,type='text/csv'){
 const url=URL.createObjectURL(content instanceof Blob?content:new Blob([content],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export async function fetchJSON<T>(url:string,signal?:AbortSignal):Promise<T>{
 const response=await fetch(url,{signal});
 if(!response.ok)throw Error(`Could not load ${url.split('/').at(-1)} (${response.status}).`);
 const type=response.headers.get('content-type')||'';
 if(!type.includes('json'))throw Error('The scientific data service is unavailable at this address.');
 return response.json();
}

export function calendarCSV(rows:CalendarMonth[]){
 const keys=['year','month','value','source','median','anomaly_pct','points','frp'] as const;
 return keys.join(',')+'\n'+rows.map(row=>keys.map(key=>row[key]??'').join(',')).join('\n');
}
