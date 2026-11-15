import {useEffect,useState} from 'react';
import {Download,LoaderCircle,Play,Square,RefreshCw} from 'lucide-react';
import {fetchJSON,fmt} from './final-model';

type Capability={available:boolean;missing_dependencies:string[];active:string|null};
type Job={id:string;status:string;stage:string;log?:string;error?:string;bundle?:string;started:string;files?:{name:string;bytes:number;url:string}[];options:{country:string;profile:string;trees:number;tune:boolean}};
async function command<T>(url:string,body?:object):Promise<T>{
 const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
 const result=await response.json();
 if(!response.ok){const detail=result.detail;throw Error(typeof detail==='string'?detail:detail?.message||'The pipeline command failed.');}
 return result;
}

export default function FinalPipeline({onLoad}:{onLoad:(base:string)=>void}){
 const [capability,setCapability]=useState<Capability|null>(null),[offline,setOffline]=useState(false),[country,setCountry]=useState('Malaysia'),[profile,setProfile]=useState('full'),[trees,setTrees]=useState(200),[tune,setTune]=useState(false),[download,setDownload]=useState(false);
 const [jobId,setJobId]=useState(()=>localStorage.getItem('fireatlas-final-job')||''),[job,setJob]=useState<Job|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[revision,setRevision]=useState(0);
 useEffect(()=>{let active=true;setOffline(false);fetchJSON<Capability>('/api/final/status').then(c=>{if(active){setCapability(c);if(c.active&&!jobId)setJobId(c.active);}}).catch(()=>{if(active)setOffline(true);});return()=>{active=false;};},[revision]);
 useEffect(()=>{
  if(!jobId)return;
  localStorage.setItem('fireatlas-final-job',jobId);
  const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;
  const poll=async()=>{try{const latest=await fetchJSON<Job>('/api/final/jobs/'+jobId,abort.signal);if(abort.signal.aborted)return;setJob(latest);setError('');if(latest.status==='running')timer=setTimeout(poll,2500);else setRevision(n=>n+1);}catch(e){if(!abort.signal.aborted){setError((e as Error).message);timer=setTimeout(poll,5000);}}};
  void poll();return()=>{abort.abort();clearTimeout(timer);};
 },[jobId]);
 async function start(){setBusy(true);setError('');try{const next=await command<Job>('/api/final/jobs',{country,profile,trees,tune,download});setJob(next);setJobId(next.id);}catch(e){setError((e as Error).message);setRevision(n=>n+1);}finally{setBusy(false);}}
 async function cancel(){if(!job)return;setBusy(true);try{setJob(await command<Job>('/api/final/jobs/'+job.id+'/cancel'));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 const running=job?.status==='running';
 return <div className="final-report"><div className="final-report-heading"><span className="eyebrow">REPRODUCE WITH THE SUPPLIED PYTHON SYSTEM</span><h1>Run the harmonization pipeline</h1><p>Download, clean and grid, validate all seven methods, simulate VIIRS points, and build the burning calendar. Each run writes to its own folder and keeps the supplied FINAL results intact.</p></div>
  {offline?<div className="final-callout"><strong>The local Python service is not connected.</strong><p>Maps, calendars, reports and downloads work here. To run new calculations, start the complete local server described in the project README, then retry.</p><button className="secondary-button" onClick={()=>setRevision(n=>n+1)}><RefreshCw size={15}/>Retry connection</button></div>:capability&&!capability.available?<div className="final-callout"><strong>Scientific dependencies need installation.</strong><p>{capability.missing_dependencies.join(', ')||'Include the FINAL/code folder on the server.'}</p><code>python -m pip install -r requirements.txt</code><button className="secondary-button" onClick={()=>setRevision(n=>n+1)}>Retry connection</button></div>:null}
  <section className="final-card"><h2>Run settings</h2><div className="final-run-settings"><label>Country<select value={country} disabled={running||busy} onChange={e=>{setCountry(e.target.value);setDownload(e.target.value!=='Malaysia');}}><option>Malaysia</option><option>Indonesia</option></select></label><label>Workflow<select value={profile} disabled={running||busy} onChange={e=>setProfile(e.target.value)}><option value="full">Complete system</option><option value="validation">Features + all-method validation</option><option value="features">Clean + build features</option></select></label><label>Forest size<select value={trees} disabled={running||busy} onChange={e=>setTrees(Number(e.target.value))}><option value="200">200 trees (delivered setting)</option><option value="800">800 trees (larger check)</option></select></label></div>
  <label className="final-check"><input type="checkbox" checked={download} disabled={running||busy||country==='Indonesia'} onChange={e=>setDownload(e.target.checked)}/>Download / verify FIRMS inputs {country==='Malaysia'?'(optional; bundled files work offline)':'(required for Indonesia)'}</label>
  <label className="final-check"><input type="checkbox" checked={tune} disabled={running||busy||profile!=='full'} onChange={e=>setTune(e.target.checked)}/>Repeat the 36-setting simulation search on tuning years</label>
  <p className="final-note">Without the search, use K = 5, α = 0, jitter = 0.375 km. Complete runs can take several minutes. Search, 800 trees, and a larger country take longer. Scores may vary with the installed scientific-library versions; each run carries its own workbooks.</p>
  <button className="primary-button" disabled={!capability?.available||offline||running||busy||!!capability?.active} onClick={start}>{busy?<LoaderCircle size={16} className="spin"/>:<Play size={16}/>}Run {profile==='full'?'complete pipeline':profile==='validation'?'validation':'feature building'}</button>
  {capability?.active&&capability.active!==jobId&&<button className="secondary-button" onClick={()=>setJobId(capability.active!)}>View active run</button>}
  </section>
  {error&&<div className="final-callout" role="alert"><strong>Could not complete the request</strong><p>{error}</p><button className="secondary-button" onClick={()=>{setJobId('');setJob(null);localStorage.removeItem('fireatlas-final-job');setRevision(n=>n+1);setError('');}}>Clear saved run & reconnect</button></div>}
  {job&&<section className="final-card"><div className="final-card-heading"><div><span className="eyebrow">{job.options?.country} · {job.options?.trees} TREES</span><h2>{job.status==='running'?'Running: ':''}{job.stage}</h2><p role="status">Status: {job.status} · Started {new Date(job.started).toLocaleString()}</p></div>{running&&<button className="secondary-button" disabled={busy} onClick={cancel}><Square size={14}/>Cancel run</button>}</div>
  {job.error&&<p role="alert">{job.error}</p>}<pre className="final-run-log" aria-label="Scientific pipeline log" tabIndex={0}>{job.log||'Starting…'}</pre>
  {job.bundle&&job.status==='complete'&&<div className="final-callout"><strong>The new website record is ready.</strong><p>Load this run to use its calendar, points and accuracy reports in the historical workspace.</p><button className="primary-button" onClick={()=>onLoad(job.bundle!)}>Load this run into the website</button></div>}
  {!!job.files?.length&&<div className="final-download-list">{job.files.map(file=><div key={file.url}><a href={file.url} download><Download size={16}/><span>{file.name}<small>{fmt(file.bytes/1024,1)} KB</small></span></a></div>)}</div>}
  </section>}
 </div>;
}
