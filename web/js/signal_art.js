// Pure, deterministic SVG studies. No audio, shader, external asset or animation loop.
const NS = "http://www.w3.org/2000/svg";
function node(tag, attrs, text) {
  const el = document.createElementNS(NS, tag);
  for (const [k,v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  if (text != null) el.textContent = text;
  return el;
}
const path = (pts) => pts.map(([x,y],i) => (i ? "L" : "M")+x.toFixed(1)+" "+y.toFixed(1)).join(" ");
const pts = (n, fn) => Array.from({length:n},(_,i)=>fn(i));
const noise = i => .5+.5*Math.sin(i*127.1+311.7);
function line(g,d,c,opacity=1,width=1.5) {
  g.append(node("path",{d,fill:"none",stroke:c,"stroke-opacity":opacity,"stroke-width":width}));
}
function text(g,x,y,value,c,anchor="end") {
  g.append(node("text",{x,y,fill:c,"font-size":11,"letter-spacing":2,"text-anchor":anchor},value));
}
function base(c) {
  const svg=node("svg",{viewBox:"0 0 1000 400",preserveAspectRatio:"xMidYMid slice","aria-hidden":"true",focusable:"false"});
  const g=node("g",{"font-family":"monospace"});
  svg.append(g);
  g.append(node("rect",{width:1000,height:400,fill:"#101511"}));
  for(let x=0;x<=1000;x+=40) line(g,"M"+x+" 0V400","#aab5a1",.085,.7);
  for(let y=0;y<=400;y+=40) line(g,"M0 "+y+"H1000","#aab5a1",.085,.7);
  for(let r=240;r>20;r-=20) g.append(node("ellipse",{cx:735,cy:200,rx:r*1.2,ry:r*.8,fill:c,"fill-opacity":.012}));
  line(g,"M968 365h16v-16M968 35h16v16M365 365h-16v-16M365 35h-16v16",c,.4);
  return {svg,g};
}
export function deckArt(c,v) {
  const {svg,g}=base(c);
  for(let k=0;k<2;k++) {
    const x=560+k*265, power=k?v:1-v;
    for(let r=24;r<=118;r+=9) g.append(node("circle",{cx:x,cy:198,r,fill:"none",stroke:c,"stroke-opacity":.13+power*.55}));
    g.append(node("circle",{cx:x,cy:198,r:118,fill:"none",stroke:c,"stroke-width":2,"stroke-opacity":.3+power*.7}));
    g.append(node("circle",{cx:x,cy:198,r:18,fill:c,"fill-opacity":.12+power*.3,stroke:c}));
    line(g,"M"+x+" 80v38",c,1,3);text(g,x,346,"DECK "+(k?"B":"A"),c,"middle");
  }
  line(g,"M550 373H825",c,.5,2);g.append(node("rect",{x:550+v*275-9,y:366,width:18,height:14,fill:c,rx:2}));
  return svg;
}
export function morphArt(c,v) {
  const {svg,g}=base(c);
  for(let j=0;j<26;j++) {
    const d=path(pts(181,i=>{const a=i/180*Math.PI*2,r=(30+j*5.3)*(1+v*.32*Math.sin(a*6+j*.16)+.06*Math.cos(a*11-j*.3));return [720+Math.cos(a)*r*1.17,200+Math.sin(a)*r];}));
    line(g,d+"Z",j%4===0?"#f0dbff":c,.19+j*.024,.8);
  }
  for(let j=0;j<12;j++){const a=j*Math.PI/6;line(g,"M720 200L"+(720+Math.cos(a)*185)+" "+(200+Math.sin(a)*185),c,.14);}
  return svg;
}
export function transitionArt(c,v) {
  const {svg,g}=base(c);
  for(let j=0;j<2;j++) {
    const y=112+j*150,col=j?"#d3a8ff":c;
    for(let i=0;i<110;i++){const x=375+i*5.5,h=8+noise(i+j*67)*68*(.25+.75*Math.sin(i*.05+j)**2);line(g,"M"+x+" "+(y-h/2)+"v"+h,col,.75,2);}
    line(g,"M375 "+y+"H980",col,.3);
  }
  const x=475+v*375;
  g.append(node("rect",{x:x-60,y:50,width:120,height:295,fill:c,"fill-opacity":.09,stroke:c,"stroke-opacity":.7}));
  line(g,"M390 105 Q"+(x-60)+" 100 "+x+" 205 T980 263",c,.9,2.5);
  line(g,"M390 265 Q"+(x-60)+" 265 "+x+" 190 T980 109","#d3a8ff",.9,2.5);
  text(g,x,37,"TRANSITION",c,"middle");
  return svg;
}
export function kickArt(c,v) {
  const {svg,g}=base(c);
  for(let j=0;j<2;j++){
    const y=123+j*152,col=j?c:"#b7bcae";
    line(g,path(pts(261,i=>{const phase=i%65;return [390+i*2.2,y+(j?49+v*20:49)*Math.exp(-phase/(j?14-v*7:14))*Math.sin(phase*(j?.85+v*.55:.85))];})),col,1,2);
    text(g,955,y-45,j?"NEW KICK":"ORIGINAL",col);
  }
  for(let x=425;x<900;x+=145)line(g,"M"+x+" 180v43m-8-8 8 8 8-8",c,.6,2);
  return svg;
}
export function stemArt(c,v) {
  const {svg,g}=base(c), colors=[c,"#b0d9a0","#a6baff","#cfaff4"];
  for(let j=0;j<4;j++){
    const y=77+j*80,col=colors[j];
    g.append(node("rect",{x:385,y:y-29,width:574,height:58,rx:3,fill:col,"fill-opacity":.045,stroke:col,"stroke-opacity":.2}));
    line(g,path(pts(161,i=>[390+i*3.55,y+Math.sin(i*1.77+j)*(Math.sin(i*.11+j*1.7)**2*.75+.25)*(8+18*Math.sin(i*.19+j)**2)])),col,.25+v*.7,1.6);
    text(g,940,y-12,["VOCALS","DRUMS","BASS","OTHER"][j],col);
  }
  for(let j=0;j<8;j++)line(g,path(pts(201,i=>{const a=i/200*Math.PI*2,r=98+j*5+(10+j)*Math.sin(a*5+j*.38)*v;return [733+Math.cos(a)*r,201+Math.sin(a)*r*.92];}))+"Z",c,.22+j*.055,.9);
  g.append(node("circle",{cx:733,cy:201,r:61,fill:"#101511","fill-opacity":.9,stroke:c,"stroke-opacity":.6}));
  text(g,733,197,"4 STEMS",c,"middle");text(g,733,216,"RECONSTRUCT","#b7c3ac","middle");
  return svg;
}
// Neutral fallback for tools that do not yet have a dedicated preview.
export function signalArt(c,v=.5) {
  const {svg,g}=base(c);
  for(let j=0;j<5;j++)line(g,path(pts(200,i=>[370+i*3.1,200+Math.sin(i*.12+j)*Math.sin(i*.034+j)*(30+v*90)])),c,.3+j*.13,1.3);
  return svg;
}
