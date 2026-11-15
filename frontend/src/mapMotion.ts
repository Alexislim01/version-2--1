import L from 'leaflet';

/** Fractional zoom with one shared destination for buttons, wheel, and keyboard. */
export function createMapMotion(map:L.Map, isDrawing:()=>boolean) {
  const element=map.getContainer();
  const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
  let destination:number|null=null;
  let wheelFrame=0;
  let wheelDelta=0;
  let wheelAnchor:L.Point|undefined;
  const limit=(zoom:number)=>Math.max(map.getMinZoom(),Math.min(map.getMaxZoom(),zoom));
  const clearDestination=()=>{destination=null;};

  function zoomBy(delta:number,anchor?:L.Point) {
    const zoom=limit((destination??map.getZoom())+delta);
    if(Math.abs(zoom-map.getZoom())<.0001)return;
    const middle=map.getSize().divideBy(2);
    const offset=(anchor??middle).subtract(middle).multiplyBy(1-1/map.getZoomScale(zoom));
    const center=map.containerPointToLatLng(middle.add(offset));
    destination=zoom;
    map.flyTo(center,zoom,{animate:!reducedMotion.matches,duration:.65});
  }

  function onWheel(event:WheelEvent) {
    event.preventDefault();
    // Normalize mouse notches, trackpads, and line/page-mode wheel events.
    const pixels=event.deltaY*(event.deltaMode===1?16:event.deltaMode===2?map.getSize().y:1);
    wheelDelta+=Math.max(-.5,Math.min(.5,-pixels/480));
    wheelAnchor=map.mouseEventToContainerPoint(event);
    if(wheelFrame)return;
    wheelFrame=requestAnimationFrame(()=>{
      wheelFrame=0;
      const delta=wheelDelta;
      wheelDelta=0;
      if(delta)zoomBy(delta,wheelAnchor);
    });
  }

  function onKey(event:KeyboardEvent) {
    if(event.ctrlKey||event.metaKey||event.altKey)return;
    if(!['+','=','-','_'].includes(event.key))return;
    event.preventDefault();
    event.stopPropagation();
    zoomBy(event.key==='-'||event.key==='_'?-.5:.5);
  }

  function onDoubleClick(event:L.LeafletMouseEvent) {
    if(isDrawing())return;
    L.DomEvent.preventDefault(event.originalEvent);
    zoomBy(event.originalEvent.shiftKey?-.5:.5,event.containerPoint);
  }

  function fitBounds(bounds:L.LatLngBoundsExpression,animate=true) {
    cancelAnimationFrame(wheelFrame);
    wheelFrame=0;wheelDelta=0;destination=null;
    map.flyToBounds(bounds,{padding:[18,18],animate:animate&&!reducedMotion.matches,duration:.9});
  }

  element.addEventListener('wheel',onWheel,{passive:false});
  element.addEventListener('keydown',onKey);
  map.on('dblclick',onDoubleClick);
  map.on('moveend dragstart',clearDestination);

  return {
    zoomBy,
    fitBounds,
    destroy(){
      cancelAnimationFrame(wheelFrame);
      element.removeEventListener('wheel',onWheel);
      element.removeEventListener('keydown',onKey);
      map.off('dblclick',onDoubleClick);
      map.off('moveend dragstart',clearDestination);
      map.stop();
    },
  };
}
