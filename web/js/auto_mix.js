// Auto-DJ transport: Übergänge auf musikalisch geschätzten Phrasen.
// Browser-Media-Elemente haben Jitter; Timing ist nicht samplegenau.
import { LiveAudio } from "./live_audio.js";
import { findeUebergang, naechsterTakt, waehleNaechsten } from "./auto_logic.js";

function wartenAufAudio(audio, timeout=15000) {
  if (audio.readyState >= 1 && Number.isFinite(audio.duration)) return Promise.resolve();
  return new Promise((resolve,reject) => {
    const aufraeumen = () => {
      clearTimeout(timer);
      audio.removeEventListener("loadedmetadata",ok);
      audio.removeEventListener("error",fehler);
    };
    const ok = () => { aufraeumen(); resolve(); };
    const fehler = () => { aufraeumen(); reject(new Error("Song kann nicht geladen werden.")); };
    const timer = setTimeout(() => { aufraeumen(); reject(new Error("Audiovorladen dauert zu lange.")); },timeout);
    audio.addEventListener("loadedmetadata",ok);
    audio.addEventListener("error",fehler);
  });
}

export class AutoMixer {
  constructor(api, callbacks={}) {
    this.api=api;
    this.cb=callbacks;
    this.engine=new LiveAudio();
    this.cache=new Map();
    this.pool=[];
    this.history=[];
    this.session=0;
    this.running=false;
    this.mix=false;
    this.bars=8;
    this.tolerance=.19;
    this.slot=0;
    this.current=null;
    this.next=null;
    this.timer=null;
  }

  say(message) { this.cb.status?.(message); }
  async info(song) {
    if (!this.cache.has(song.pfad)) {
      const request=this.api.beat(song.pfad).catch(err => {
        this.cache.delete(song.pfad);
        throw err;
      });
      this.cache.set(song.pfad,request);
    }
    return this.cache.get(song.pfad);
  }

  setPool(songs) { this.pool=songs.slice(); }
  async laden(slot,song) {
    this.engine.laden(slot,this.api.audioUrl(song.pfad));
    const a=this.engine.decks[slot];
    await wartenAufAudio(a);
    return a;
  }
  reportSong(song,info) {
    this.cb.song?.(song,info);
    this.cb.history?.(this.history.map((p)=>({...p})));
  }

  async starten(songs,{bars=8,tolerance=.19}={}) {
    this.stop();
    this.pool=songs.slice();
    this.bars=Number(bars)||8;
    this.tolerance=Number(tolerance)||.19;
    if (this.pool.length<2) throw new Error("Bitte mindestens zwei Songs für das Set auswählen.");
    const token=this.session;
    await this.engine.aktivieren();
    this.say("Analysiere die ersten Tracks und suche eine passende Startposition …");
    let picked=null, info=null;
    const versucht=new Set();
    while (versucht.size<this.pool.length && versucht.size<8) {
      const song=waehleNaechsten(this.pool,[...versucht]);
      if (!song||versucht.has(song.pfad)) break;
      versucht.add(song.pfad);
      try { info=await this.info(song); picked=song; break; }
      catch { /* defekte oder unrhythmische Datei überspringen */ }
      if (this.session!==token) return;
    }
    if (!picked || this.session!==token) throw new Error("Keine analysierbaren Songs gefunden. ffmpeg und Musikdateien prüfen.");
    const audio=await this.laden(0,picked);
    if(this.session!==token) return;
    this.slot=0;
    this.current={song:picked,info};
    this.history.push(picked);
    this.engine.setCrossfade(0);
    audio.playbackRate=1;
    audio.preservesPitch=true;
    // Der erste Song startet am Anfang: der Hörer erlebt den Aufbau.
    audio.currentTime=0;
    await audio.play();
    if(this.session!==token) { audio.pause(); return; }
    this.running=true;
    this.reportSong(picked,info);
    this.cb.plan?.(null);
    this.say("Set läuft · ich suche den dramaturgisch passenden nächsten Song …");
    this.timer=setInterval(()=>this.takt(),35);
    this.vorbereiten(token);
  }

  async vorbereiten(token=this.session) {
    if (!this.running||this.next||this.preparing||this.session!==token) return;
    this.preparing=true;
    const {song:aktuell,info:infoA}=this.current;
    const jetzt=this.engine.decks[this.slot].currentTime;
    const pool=this.pool.filter(s=>s.pfad!==aktuell.pfad);
    const versucht=new Set();
    const kandidaten=[];
    // Ein kleines exploratives Sample statt hundert gleichzeitig laufender ffmpeg-Prozesse.
    while(versucht.size<pool.length && kandidaten.length<6) {
      const sample=waehleNaechsten(pool,
        [...this.history.map(s=>s.pfad),...versucht],infoA.bpm);
      if(!sample||versucht.has(sample.pfad)) break;
      versucht.add(sample.pfad);
      kandidaten.push(sample);
    }
    try {
      let beste=null;
      // Maximal zwei Analyseaufträge gleichzeitig: Claude bleibt priorisiert.
      for(let i=0;i<kandidaten.length;i+=2) {
        const batch=await Promise.allSettled(kandidaten.slice(i,i+2).map(async song =>
          ({song, info:await this.info(song)})));
        if(this.session!==token||!this.running) return;
        for(const answer of batch) {
          if(answer.status!=="fulfilled") continue;
          const {song,info}=answer.value;
          const cue= findeUebergang(infoA,info,
            this.engine.decks[this.slot].currentTime+1,this.bars,this.tolerance);
          if (!cue) continue;
          const taste=cue.score+(Math.random()-.5)*.09; // bewusst etwas Varianz
          if(!beste||taste>beste.taste) beste={song,info,cue,taste};
        }
        if(beste) break;  // erst möglichst wenig Rechenzeit
      }
      if(!beste) {
        this.say("Noch kein geeigneter Cue: weitere Songs/Tempos testen oder Toleranz erhöhen.");
        // Ein neues Kandidaten-Sample nach einem kurzen Abstand probieren.
        this.preparing=false;
        this.retry=setTimeout(()=>this.vorbereiten(token),4500);
        return;
      }
      const zielSlot=1-this.slot;
      await this.laden(zielSlot,beste.song);
      if(this.session!==token||!this.running) return;
      const audio=this.engine.decks[zielSlot];
      audio.preservesPitch=true;              // Tempoangleichung möglichst ohne Tonhöhenänderung
      audio.playbackRate=beste.cue.rateB;
      audio.currentTime=beste.cue.startB;
      this.next=beste;
      this.cb.plan?.(beste);
      this.say("Nächster Song vorbereitet · Übergang an der musikalischen Phrasengrenze geplant.");
    } catch(err) {
      if(this.session===token) this.say("Vorladen fehlgeschlagen: "+(err.meldung||err.message||err));
    } finally {
      this.preparing=false;
    }
  }

  async wechsel() {
    const pending=this.next;
    if(!pending||this.mix||!this.running) return;
    const token=this.session;
    this.mix=true;
    const alt=this.slot, neu=1-alt;
    const a=this.engine.decks[alt], b=this.engine.decks[neu];
    try {
      // Kleine Timer-Verspätungen werden durch eine Cue-Korrektur kompensiert.
      const offset=Math.max(0,a.currentTime-pending.cue.startA);
      b.currentTime=Math.min(Math.max(0,b.duration-.2),
        pending.cue.startB+offset*pending.cue.rateB);
      await b.play();
      if(token!==this.session) { b.pause(); return; }
      this.engine.autoCrossfade(alt,Math.max(0.25,pending.cue.dauer-offset));
      this.cb.transition?.(pending);
      this.say("LIVE-MIX · "+pending.cue.ausgang+" → "+pending.cue.eingang);
    } catch(err) {
      this.mix=false;
      this.next=null;
      this.say("Übergang konnte nicht gestartet werden: "+(err.message||err));
      this.vorbereiten(token);
    }
  }

  takt() {
    if(!this.running||!this.current) return;
    const a=this.engine.decks[this.slot];
    if(this.mix && this.next) {
      if(a.currentTime >= this.next.cue.startA+this.next.cue.dauer-.06 || a.ended) {
        a.pause();
        this.slot=1-this.slot;
        const neu=this.next;
        this.current={song:neu.song,info:neu.info};
        this.next=null;
        this.mix=false;
        this.history.push(neu.song);
        this.history=this.history.slice(-40);
        this.engine.setCrossfade(this.slot===0?0:100);
        this.reportSong(neu.song,neu.info);
        this.cb.plan?.(null);
        this.say("Neuer Song übernommen · nächster Übergang wird gesucht …");
        this.vorbereiten();
      }
    } else if(this.next && a.currentTime >= this.next.cue.startA-.05) {
      this.wechsel();
    } else if(a.ended) {
      if(this.next) this.wechsel();
      else { this.say("Track beendet, nächster Übergang wird vorbereitet …"); this.vorbereiten(); }
    }
    this.cb.progress?.(a.currentTime,a.duration,this.next?.cue||null);
  }

  naechsterTakt() {
    if(!this.next||!this.current||this.mix) return;
    const audio=this.engine.decks[this.slot];
    const cue=this.next.cue;
    cue.startA=naechsterTakt(audio.currentTime+.5,
      {bpm:this.current.info.bpm,beat0:this.current.info.bar0||0});
    if(cue.startA+cue.dauer>=audio.duration) cue.dauer=Math.max(1,audio.duration-cue.startA-.5);
    this.cb.plan?.(this.next);
    this.say("Manueller Befehl: Mix auf dem nächsten Takt.");
  }

  stop() {
    this.session++;
    this.running=false;
    this.mix=false;
    this.preparing=false;
    clearInterval(this.timer); this.timer=null;
    clearTimeout(this.retry); this.retry=null;
    this.next=null;
    this.current=null;
    for(const audio of this.engine.decks) audio.pause();
    this.engine.setCrossfade(0);
    this.cb.plan?.(null);
  }

  destroy() { this.stop(); this.engine.beenden(); }
}
