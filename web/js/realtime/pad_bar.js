import {PadScheduler, PAD_TYPES} from "./pad_scheduler.js";

const NOTES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
const FLATS = {"Db":"C#","Eb":"D#","Gb":"F#","Ab":"G#","Bb":"A#"};
export function keyCode(key, confidence) {
  if (!(confidence >= .5)) return 0;
  const match = /^([A-G][#b]?) (Dur|Moll|major|minor)$/.exec(key);
  if (!match) return 0;
  const note = NOTES.indexOf(FLATS[match[1]] || match[1]);
  return note < 0 ? 0 : 1 + note + (["Moll","minor"].includes(match[2]) ? 12 : 0);
}

export function padAvailable(capabilities) {
  return capabilities?.some(c=>c.id==="stable_audio" && c.available===true &&
    c.mock===false && c.mode==="lookahead") === true;
}

// Backend-Port: open() reserviert Lease und lädt/wärmt, generate() wartet auf
// Dateijob und dekodiertes Asset im Sitzungsformat, close() bricht auch offene
// Jobs ab. Audio-Port: now(), preview(buffer), stopPreview(), schedule(plan,
// buffer), reset(). Keine automatische Worker-Aktion im Konstruktor.
export class PadController {
  constructor({capabilities, backend, audio, grid, key, keyConfidence, sampleRate, p95Ms}) {
    this.backend=backend; this.audio=audio; this.grid=grid;
    this.key=keyCode(key,keyConfidence); this.rate=sampleRate;
    this.scheduler=new PadScheduler({grid,sampleRate,p95Ms,maxPending:1});
    this.enabled=padAvailable(capabilities) && !!this.scheduler.grid && !!backend && !!audio;
    this.state=this.enabled?"closed":"disabled";
    this.reason=!padAvailable(capabilities)?"Stable Audio nicht installiert oder freigegeben":
      !this.scheduler.grid?"BeatGrid unsicher":"Pad-Pfad nicht verfügbar";
    this.epoch=0; this.job=null; this.buffer=null; this.opening=null;
  }
  async open(userAction=false) {
    if(!this.enabled || userAction!==true || this.state!=="closed" || this.opening) return false;
    const epoch=++this.epoch;
    this.state="loading";
    try {
      this.opening=Promise.resolve(this.backend.open());
      await this.opening;
      if(epoch!==this.epoch)return false;
      this.state="ready";return true;
    } catch(e) {
      if(epoch===this.epoch)await this.close();
      throw e;
    } finally {this.opening=null;}
  }
  async request({type,bars,seed,strength=1}) {
    if(this.state!=="ready")return {status:"dry",reason:"Pads nicht bereit"};
    const epoch=this.epoch, now=this.audio.now();
    // Zieltempo aus Taktlänge (auch bei Tempo-Wechseln), Tonart nur bei Konfidenz.
    const job=this.scheduler.request({type,bars,seed,strength,prompt:"Musikalischer Kontext"},now);
    if(job.status==="dry")return job;
    const duration=job.durationFrames/this.rate, bpm=bars*240/duration;
    if(duration<.25 || duration>30 || bpm<1 || bpm>1000){
      this.scheduler.cancel(job.id);return {status:"dry",reason:"Cliplänge außerhalb der Modellgrenze"};
    }
    this.job=job.id;this.state="rendering";
    try {
      const result=await this.backend.generate({pad_type:PAD_TYPES.indexOf(type),bars,seed,strength,
        duration,bpm,key:this.key});
      if(epoch!==this.epoch || this.job!==job.id)return {status:"dry",reason:"Job abgebrochen"};
      const b=result?.buffer;
      if(!b || !/^[0-9a-f]{32}$/.test(result.assetId) || b.numberOfChannels!==2){
        this.discard();return {status:"dry",reason:"Asset ungültig"};
      }
      const ready=this.scheduler.ready(job.id,{frames:b.length,sampleRate:b.sampleRate,assetId:result.assetId},this.audio.now());
      if(ready.status!=="ready"){this.discard();return ready;}
      this.buffer=b;this.state="candidate";return ready;
    } catch(e) {
      if(epoch===this.epoch){await this.close();}
      throw e;
    }
  }
  preview() {
    if(this.state!=="candidate" || !this.scheduler.preview(this.job))return false;
    this.audio.preview(this.buffer);return true;
  }
  take() {
    if(this.state!=="candidate")return {status:"dry",reason:"Kein Kandidat"};
    this.audio.stopPreview();
    const plan=this.scheduler.take(this.job,this.audio.now());
    const buffer=this.buffer;
    this.job=null;this.buffer=null;this.state="ready";
    if(plan.status==="scheduled" && this.audio.schedule(plan,buffer)!==true)
      return {status:"dry",reason:"Audio-Zeitachse oder Einsatz belegt"};
    return plan;
  }
  discard() {
    if(this.state!=="candidate" && this.state!=="rendering")return;
    this.audio.stopPreview();this.scheduler.cancel(this.job);
    this.job=null;this.buffer=null;
    // Rendern nicht parallel fortsetzen: Schließen bricht den Worker ab.
    if(this.state==="rendering")return this.close();
    this.state="ready";
  }
  async close() {
    if(this.state==="disabled" || this.state==="closed" || this.state==="closing")return;
    ++this.epoch;this.state="closing";this.scheduler.reset();this.job=null;this.buffer=null;
    try {
      this.audio.reset();
    } finally {
      try {await this.backend.close();}
      finally {this.state="closed";}
    }
  }
}

// Eigene DOM-Leiste; nur sichere textContent-Zuweisungen. Keine Listener auf
// gemeinsamen Dateien; Shell besitzt Mount/Destroy und ruft destroy bei Seek.
export function mountPadBar(root, controller, {document=root.ownerDocument, seed=()=>0}={}) {
  const section=document.createElement("section"), status=document.createElement("p");
  const title=document.createElement("h3");title.textContent="Performance Pads – Lookahead";
  const bars=document.createElement("select");bars.setAttribute("aria-label","Takte");
  for(const n of [1,2,4,8]){const o=document.createElement("option");o.value=String(n);o.textContent=String(n)+" Takte";bars.append(o);}
  let destroyed=false, busy=false, message="";
  const listeners=[];
  const button=(label,fn)=>{
    const b=document.createElement("button");b.type="button";b.textContent=label;
    const handler=async()=>{if(busy||destroyed)return;busy=true;message="";paint();
      try{const result=await fn();message=result?.reason || result?.warning || "";}
      catch(e){message="Pad-Aktion fehlgeschlagen";}
      finally{busy=false;if(!destroyed)paint();}};
    b.addEventListener("click",handler);listeners.push([b,handler]);return b;
  };
  const open=button("Pads öffnen",()=>controller.open(true));
  const pads=PAD_TYPES.map(type=>button(type,()=>controller.request({type,bars:Number(bars.value),seed:seed(),strength:.7})));
  const preview=button("Vorhören",()=>controller.preview()),take=button("Einsetzen",()=>controller.take()),
    discard=button("Verwerfen",()=>controller.discard());
  const close=button("Pads schließen",()=>controller.close());
  function paint(){
    const s=controller.state;
    status.textContent=s==="disabled"?controller.reason:({closed:"Geschlossen",loading:"Laden / Aufwärmen",ready:"Bereit",rendering:"Erzeugung",candidate:"Kandidat bereit",closing:"Entladen"}[s]||s)+(message?" – "+message:"");
    open.disabled=busy||s!=="closed";bars.disabled=busy||s!=="ready";
    for(const b of pads)b.disabled=busy||s!=="ready";
    for(const b of [preview,take,discard])b.disabled=busy||s!=="candidate";
    close.disabled=busy||!["ready","candidate"].includes(s);
  }
  section.append(title,status,open,bars,...pads,preview,take,discard,close);root.append(section);paint();
  return {async destroy(){destroyed=true;for(const [b,h] of listeners)b.removeEventListener("click",h);
    section.remove();await controller.close();}};
}
