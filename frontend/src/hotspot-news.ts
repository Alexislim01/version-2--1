/** External discovery only: results do not establish the cause of a detection. */
export function hotspotNewsUrl(place:string,date:string):string {
 const day=new Date(`${date}T00:00:00Z`);
 if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(day.getTime())||day.toISOString().slice(0,10)!==date)throw new Error('A valid detection date is required');
 const start=new Date(day.getTime()-3*86400000).toISOString().slice(0,10);
 const end=new Date(day.getTime()+4*86400000).toISOString().slice(0,10);
 const location=place.trim().slice(0,120).replace(/["\r\n]/g,' ');
 const query=`${location?`"${location}" `:''}(wildfire OR fire OR explosion OR haze) after:${start} before:${end}`;
 const url=new URL('https://www.google.com/search');
 url.searchParams.set('tbm','nws');url.searchParams.set('q',query);
 return url.toString();
}
