import type {Observation} from './engine.ts';
export const sensorColors={MODIS:'#32c5f4',VIIRS:'#ff914d',mixed:'#ffe08a',synthetic:'#c69aff'};
export function binHotspots(points:Observation[],grid:number,showGrid:boolean,selectedDate:string|null){
 const bins=new Map<string,{lat:number;lng:number;n:number;frp:number;sensors:Set<string>;synthetic:boolean;firstDate:string;lastDate:string}>();
 for(const point of points){
  if(selectedDate&&point.acq_date!==selectedDate)continue;
  const cell=showGrid?grid:.035;
  const key=`${Math.floor(point.latitude/cell)},${Math.floor(point.longitude/cell)},${point.is_synthetic?'synthetic':'observed'},${showGrid?'all':point.instrument}`;
  if(!bins.has(key))bins.set(key,{lat:point.latitude,lng:point.longitude,n:0,frp:0,sensors:new Set(),synthetic:!!point.is_synthetic,firstDate:point.acq_date,lastDate:point.acq_date});
  const bin=bins.get(key)!;bin.n++;bin.frp+=point.frp;bin.firstDate=point.acq_date<bin.firstDate?point.acq_date:bin.firstDate;bin.lastDate=point.acq_date>bin.lastDate?point.acq_date:bin.lastDate;bin.sensors.add(point.instrument);
 }
 return [...bins.values()];
}
