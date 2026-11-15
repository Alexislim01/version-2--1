import { useEffect, useState, type CSSProperties } from 'react';
import { CalendarDays, ChevronLeft, ChevronRight, Info, X } from 'lucide-react';
import type { Day } from './engine';
export type Metric='count'|'frp'|'anomaly';
export const colors=['#293437','#51483b','#806044','#b47c4e','#dc9b61','#f2c291'];
export const metricValue=(d:Day,metric:Metric)=>metric==='count'?d.harmonized_count:metric==='frp'?d.harmonized_frp:d.anomaly;
export function dayColor(d:Day,metric:Metric,max:number){const v=metricValue(d,metric);return v===null?'#1a2326':v===0?colors[0]:metric==='anomaly'&&v<0?'#496f80':colors[Math.max(1,Math.min(5,Math.ceil(Math.max(0,v)/Math.max(1,max)*5)))];}
type CalendarProps={days:Day[];metric:Metric;setMetric:(m:Metric)=>void;onSelect:(d:string|null)=>void;selectedDate:string|null;compact?:boolean};
export default function Calendar({days,metric,setMetric,onSelect,selectedDate,compact=false}:CalendarProps){
  const [hover,setHover]=useState<Day|null>(null),[tipPos,setTipPos]=useState({x:0,y:0});
  const years=[...new Set(days.map(d=>d.date.slice(0,4)))].sort().reverse();
  const values=days.map(d=>metricValue(d,metric)).filter((v):v is number=>v!==null&&v>0).sort((a,b)=>a-b);const max=values[Math.floor(values.length*.95)]||1;
  function selectRelative(delta:number){const i=days.findIndex(d=>d.date===selectedDate);onSelect(days[Math.max(0,Math.min(days.length-1,(i<0?0:i)+delta))]?.date||null);}
  if(compact)return <MonthCalendar days={days} metric={metric} setMetric={setMetric} onSelect={onSelect} selectedDate={selectedDate}/>;
  return <section className="panel calendar-panel" id="calendar"><div className="panel-heading"><div><h2><CalendarDays size={17}/> Burning activity calendar</h2><p>Each column is a day. Select a day to show its detections on the map.</p></div><div className="segmented" aria-label="Calendar metric">{(['count','frp','anomaly'] as Metric[]).map(m=><button key={m} aria-pressed={metric===m} onClick={()=>setMetric(m)}>{m==='count'?'Fire activity':m==='frp'?'Radiative power':'Unusual activity'}</button>)}</div></div>
    <div className="calendar-scroll"><div className="calendar-inner"><div className="month-labels"><span/>{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].map(m=><span key={m}>{m}</span>)}</div>
    {years.map(year=><div className="calendar-year" key={year}><span className="year-label">{year}</span><div className="calendar-cells" role="group" aria-label={`${year} daily burning activity`}>
      {Array.from({length:366},(_,i)=>{const date=new Date(Date.UTC(2000,0,1+i)).toISOString().slice(4,10),key=year+date;const d=days.find(day=>day.date===key);if(!d)return <span key={key} className="calendar-day outside"/>;const v=metricValue(d,metric);return <button key={key} className={`calendar-day ${selectedDate===key?'selected':''} ${v===null?'missing':''}`} style={{background:dayColor(d,metric,max)}} tabIndex={selectedDate===key||(!selectedDate&&key===days[0]?.date)?0:-1} aria-label={`${key}: ${v===null?'No coverage':v.toFixed(1)+' '+(metric==='frp'?'MW':metric==='anomaly'?'z-score':'MODIS-equivalent fires')}, ${d.source}`} aria-pressed={selectedDate===key}
        onClick={()=>onSelect(selectedDate===key?null:key)} onFocus={()=>setHover(d)} onBlur={()=>setHover(null)} onMouseEnter={e=>{setHover(d);setTipPos({x:Math.min(e.clientX,window.innerWidth-260),y:e.clientY});}} onMouseLeave={()=>setHover(null)} onKeyDown={e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();const delta=e.key==='ArrowLeft'?-1:e.key==='ArrowRight'?1:e.key==='ArrowUp'?-365:365;const next=days[Math.max(0,Math.min(days.length-1,days.indexOf(d)+delta))];onSelect(next.date);document.querySelector<HTMLButtonElement>(`[aria-label^="${next.date}:"]`)?.focus();}}}/>;})}
    </div></div>)}
    </div></div>
    <div className="calendar-footer"><span><Info size={13}/> {metric==='anomaly'?'Compared with other years · 95th percentile threshold':'Adjusted to the MODIS scale · select a day to filter the map'}</span><div className="legend"><span>{metric==='anomaly'?'Negative':'Less'}</span>{metric==='anomaly'&&<i style={{background:'#496f80'}}/>}{colors.map(c=><i key={c} style={{background:c}}/>)}<span>More</span><i className="missing-key"/><span>No coverage</span></div></div>
    {selectedDate&&<div className="selected-day"><CalendarDays size={14}/><strong>{new Date(selectedDate+'T00:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'})}</strong><span>{days.find(d=>d.date===selectedDate)?.source}</span><button aria-label="Previous day" onClick={()=>selectRelative(-1)}><ChevronLeft size={15}/></button><button aria-label="Next day" onClick={()=>selectRelative(1)}><ChevronRight size={15}/></button><button aria-label="Clear day selection" onClick={()=>onSelect(null)}><X size={15}/></button></div>}
    {hover&&<div className="calendar-tooltip" role="tooltip" style={{left:tipPos.x,top:Math.max(80,tipPos.y-120)}}><strong>{hover.date}</strong><span>{metricValue(hover,metric)?.toFixed(2)??'No coverage'} {metric==='frp'?'MW':metric==='anomaly'?'z-score':'MODIS-equivalent'}</span><span>{hover.percentile===null?'Baseline unavailable':`${hover.percentile.toFixed(0)}th percentile`} · {hover.source}</span></div>}
  </section>;
}

function MonthCalendar({days,metric,setMetric,onSelect,selectedDate}:CalendarProps){
  const latestYear=days.at(-1)?.date.slice(0,4);
  const latestDays=days.filter(d=>d.date.startsWith(latestYear||''));
  const peak=latestDays.reduce<Day|null>((best,day)=>(day.harmonized_count||0)>(best?.harmonized_count||0)?day:best,latestDays[0]||null);
  const defaultMonth=(selectedDate||peak?.date||days.at(-1)?.date||'2023-01-01').slice(0,7);
  const [month,setMonth]=useState(defaultMonth);
  const firstMonth=days[0]?.date.slice(0,7)||defaultMonth,lastMonth=days.at(-1)?.date.slice(0,7)||defaultMonth;
  useEffect(()=>{if(selectedDate)setMonth(selectedDate.slice(0,7));},[selectedDate]);
  useEffect(()=>{if(month<firstMonth||month>lastMonth)setMonth(defaultMonth);},[firstMonth,lastMonth,defaultMonth,month]);
  const years=[...new Set(days.map(day=>day.date.slice(0,4)))].sort().reverse();
  const lookup=new Map(days.map(d=>[d.date,d]));
  const [year,monthNumber]=month.split('-').map(Number);
  const offset=(new Date(Date.UTC(year,monthNumber-1,1)).getUTCDay()+6)%7;
  const monthDays=new Date(Date.UTC(year,monthNumber,0)).getUTCDate();
  const rows=Math.ceil((offset+monthDays)/7);
  const values=days.map(d=>metricValue(d,metric)).filter((v):v is number=>v!==null&&v>0).sort((a,b)=>a-b);
  const maximum=values[Math.floor(values.length*.95)]||1;
  const selected=selectedDate?lookup.get(selectedDate):undefined;
  const monthLabel=new Date(Date.UTC(year,monthNumber-1,1)).toLocaleDateString('en-GB',{month:'long',year:'numeric',timeZone:'UTC'});
  function changeMonth(next:string){setMonth(next<firstMonth?firstMonth:next>lastMonth?lastMonth:next);}
  function stepMonth(delta:number){changeMonth(new Date(Date.UTC(year,monthNumber-1+delta,1)).toISOString().slice(0,7));}
  function selectRelative(delta:number){const index=days.findIndex(d=>d.date===selectedDate);onSelect(days[Math.max(0,Math.min(days.length-1,(index<0?0:index)+delta))]?.date||null);}
  return <section className="compact-calendar" id="calendar" aria-label="Monthly fire activity calendar">
    <div className="compact-section-heading"><h3>Activity calendar</h3><p>Select a day to see its fire detections on the map.</p></div>
    <label className="compact-metric-label" htmlFor="calendar-metric">Show activity by</label><select id="calendar-metric" value={metric} onChange={e=>setMetric(e.target.value as Metric)}><option value="count">Fire activity</option><option value="frp">Radiative power</option><option value="anomaly">Unusual activity</option></select>
    <div className="month-navigation"><button aria-label="Previous month" disabled={month<=firstMonth} onClick={()=>stepMonth(-1)}><ChevronLeft size={17}/></button><select aria-label="Calendar month" value={monthNumber} onChange={e=>changeMonth(`${year}-${e.target.value.padStart(2,'0')}`)}>{Array.from({length:12},(_,i)=><option key={i} value={i+1} disabled={`${year}-${String(i+1).padStart(2,'0')}`<firstMonth||`${year}-${String(i+1).padStart(2,'0')}`>lastMonth}>{new Date(Date.UTC(2000,i,1)).toLocaleDateString('en',{month:'short',timeZone:'UTC'})}</option>)}</select><select aria-label="Calendar year" value={year} onChange={e=>changeMonth(`${e.target.value}-${String(monthNumber).padStart(2,'0')}`)}>{years.map(y=><option value={y} key={y}>{y}</option>)}</select><button aria-label="Next month" disabled={month>=lastMonth} onClick={()=>stepMonth(1)}><ChevronRight size={17}/></button></div>
    <div className="month-weekdays" aria-hidden="true">{['M','T','W','T','F','S','S'].map((day,i)=><span key={i}>{day}</span>)}</div>
    <div className="month-grid" role="group" aria-label={monthLabel}>{Array.from({length:rows*7},(_,i)=>{
      const day=i-offset+1,date=`${month}-${String(day).padStart(2,'0')}`,record=day>=1&&day<=monthDays?lookup.get(date):undefined;
      if(day<1||day>monthDays)return <span className="month-day outside" key={i}/>;
      const value=record?metricValue(record,metric):null;
      return <button key={date} className={`month-day ${selectedDate===date?'selected':''} ${value===null?'missing':''}`} disabled={!record} aria-label={`${date}: ${value===null?'No coverage':value.toFixed(1)+(metric==='frp'?' MW':metric==='anomaly'?' z-score':' MODIS-equivalent fires')}`} aria-pressed={selectedDate===date} style={{'--day-color':record?dayColor(record,metric,maximum):'#1a2326'} as React.CSSProperties} title={`${date}: ${value===null?'No coverage':value.toFixed(2)}${record?' · '+record.source:''}`} onClick={()=>onSelect(selectedDate===date?null:date)} onKeyDown={e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const delta=e.key==='ArrowLeft'?-1:e.key==='ArrowRight'?1:e.key==='ArrowUp'?-7:7;const index=days.indexOf(record!);const next=days[Math.max(0,Math.min(days.length-1,index+delta))];onSelect(next.date);requestAnimationFrame(()=>document.querySelector<HTMLButtonElement>(`.month-day[aria-label^="${next.date}:"]`)?.focus());}}><span>{day}</span><i/></button>;
    })}</div>
    <div className="compact-calendar-legend"><span>Less</span>{colors.map(color=><i key={color} style={{background:color}}/>)}<span>More</span></div><p className="calendar-coverage-key"><span/>Striped cells: no coverage</p>
    {selected?<div className="calendar-day-details"><div className="day-details-heading"><CalendarDays size={15}/><strong>{new Date(selected.date+'T00:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'})}</strong><button aria-label="Clear day selection" onClick={()=>onSelect(null)}><X size={15}/></button></div><div className="day-details-value">{metricValue(selected,metric)===null?'No coverage':metricValue(selected,metric)!.toLocaleString('en',{maximumFractionDigits:2})}<span>{metric==='frp'?'MW':metric==='anomaly'?'z-score':'MODIS equivalents'}</span></div><p>{selected.source} · {selected.percentile===null?'Baseline unavailable':`${Math.round(selected.percentile)}th percentile`}</p><div className="day-details-navigation"><button aria-label="Previous day" onClick={()=>selectRelative(-1)}><ChevronLeft size={14}/>Previous day</button><button aria-label="Next day" onClick={()=>selectRelative(1)}>Next day<ChevronRight size={14}/></button></div></div>:<div className="calendar-select-hint"><Info size={16}/><p>Choose any date above. The map updates while the calendar stays beside it.</p></div>}
    <p className="compact-method-note">{metric==='anomaly'?'Compared with the same season in other selected years.':'Fire activity is adjusted to the MODIS scale for comparison.'}</p>
  </section>;
}
