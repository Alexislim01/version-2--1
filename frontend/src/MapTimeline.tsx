import {useEffect,useState,type CSSProperties} from 'react';
import {ChevronLeft,ChevronRight,Pause,Play,RotateCcw} from 'lucide-react';
import './map-timeline.css';

type TimelineStep={key:string;label:string;detail:string};
export default function MapTimeline({steps,selected,onSelect,onClear,scopeKey,unit}:{steps:TimelineStep[];selected:string|null;onSelect:(key:string)=>void;onClear?:()=>void;scopeKey:string;unit:string}){
 const [playing,setPlaying]=useState(false),[speed,setSpeed]=useState(1);
 const found=steps.findIndex(step=>step.key===selected),index=Math.max(0,found),current=steps[index],disabled=steps.length<2;
 useEffect(()=>setPlaying(false),[scopeKey]);
 useEffect(()=>{
  if(!playing)return;
  if(disabled||found<0||index===steps.length-1){setPlaying(false);return;}
  const timer=setTimeout(()=>onSelect(steps[index+1].key),800/speed);
  return()=>clearTimeout(timer);
 },[playing,speed,index,found,steps,onSelect,disabled]);
 function choose(next:number){setPlaying(false);if(steps[next])onSelect(steps[next].key);}
 function toggle(){if(playing){setPlaying(false);return;}if(disabled)return;if(found<0||index===steps.length-1)onSelect(steps[0].key);setPlaying(true);}
 return <section className="map-timeline" aria-label="Fire activity timeline">
  <div className="timeline-heading"><div><strong>{found>=0?current.label:steps.length?'All selected dates':'No dates available'}</strong><span>{found>=0?current.detail:`${steps.length.toLocaleString('en-US')} ${unit} in selected range`}</span></div>{onClear&&<button type="button" className="timeline-reset" disabled={found<0} onClick={()=>{setPlaying(false);onClear();}}><RotateCcw size={12}/>All dates</button>}</div>
  <div className="timeline-controls">
   <button type="button" aria-label={`Previous ${unit==='months'?'month':'day'}`} disabled={!steps.length||index===0&&found>=0} onClick={()=>choose(found<0?0:index-1)}><ChevronLeft size={17}/></button>
   <button type="button" className="timeline-play" aria-label={playing?'Pause timeline':'Play timeline'} disabled={disabled} onClick={toggle}>{playing?<Pause size={14}/>:<Play size={14}/>}<span>{playing?'Pause':'Play'}</span></button>
   <button type="button" aria-label={`Next ${unit==='months'?'month':'day'}`} disabled={!steps.length||found>=0&&index===steps.length-1} onClick={()=>choose(found<0?0:index+1)}><ChevronRight size={17}/></button>
   <div className="timeline-track"><input aria-label="Timeline position" aria-valuetext={current?.label||'No dates available'} type="range" min="0" max={Math.max(0,steps.length-1)} step="1" value={index} disabled={disabled} style={{'--timeline-progress':`${steps.length>1?index/(steps.length-1)*100:0}%`} as CSSProperties} onChange={event=>choose(+event.target.value)}/><div className="timeline-endpoints" aria-hidden="true"><span>{steps[0]?.label||'—'}</span><span>{steps.at(-1)?.label||'—'}</span></div></div>
   <select aria-label="Playback speed" value={speed} onChange={event=>setSpeed(+event.target.value)}>{[.5,1,2,4].map(value=><option key={value} value={value}>{value}×</option>)}</select>
  </div>
 </section>;
}
