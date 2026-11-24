// Auto-DJ transport: Übergänge auf musikalisch geschätzten Phrasen.
// Browser-Media-Elemente haben Jitter; Timing ist nicht samplegenau.
import { LiveAudio } from "./live_audio.js";
import { findeUebergang, naechsterTakt, waehleNaechsten, tempoAngleichung, setEnergieZiel, syncFehler, syncRate } from "./auto_logic.js";

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

// Seek muss abgeschlossen sein, bevor das zweite Deck hörbar wird.
function wartenAufSeek(audio, timeout=2000) {
  if(!audio.seeking) return Promise.resolve();
  return new Promise((resolve,reject)=>{
    const fertig=()=>{
      clearTimeout(timer);
      audio.removeEventListener("seeked",fertig);
      resolve();
    };
    const timer=setTimeout(()=>{
      audio.removeEventListener("seeked",fertig);
      reject(new Error("Beat-Cue konnte nicht rechtzeitig positioniert werden."));
    },timeout);
    audio.addEventListener("seeked",fertig);
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
    this.currentRate=1;
    this.currentNormal=null;
    this.mixEnd=null;
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
    const result=await this.cache.get(song.pfad);
    song.beat=result;
    return result;
  }

  setPool(songs) { this.pool=songs.slice(); }
  async laden(slot,song) {
    this.engine.laden(slot,this.api.audioUrl(song.pfad));
    const a=this.engine.decks[slot];
    await wartenAufAudio(a);
    return a;
  }
  reportSong(song,info) {
    this.cb.song?.(song,info,(this.currentNormal||info.bpm)*this.currentRate);
    this.cb.history?.(this.history.map((p)=>({...p})));
  }

  async starten(songs,{bars=8,tolerance=.19,randomness=true,story="welle"}={}) {
    this.stop();
    this.pool=songs.slice();
    this.bars=Number(bars)||8;
    this.tolerance=Number(tolerance)||.19;
    this.randomness=Boolean(randomness);
    this.story=story;
    if (this.pool.length<2) throw new Error("Bitte mindestens zwei Songs für das Set auswählen.");
    const token=this.session;
    await this.engine.aktivieren();
    if(this.session!==token) return false;
    this.say("Analysiere die ersten Tracks und suche eine passende Startposition …");
    let picked=null, info=null;
    const versucht=new Set();
    while (versucht.size<this.pool.length && versucht.size<8) {
      const offen=this.pool.filter(s=>!versucht.has(s.pfad));
      const song=this.randomness?waehleNaechsten(offen,[...versucht]):
        offen.sort((a,b)=>b.rating-a.rating||a.text.localeCompare(b.text,"de"))[0];
      if (!song||versucht.has(song.pfad)) break;
      versucht.add(song.pfad);
      try { info=await this.info(song); picked=song; break; }
      catch { /* defekte oder unrhythmische Datei überspringen */ }
      if (this.session!==token) return;
    }
    if(this.session!==token) return false;
    if(!picked) throw new Error("Keine analysierbaren Songs gefunden. ffmpeg und Musikdateien prüfen.");
    const audio=await this.laden(0,picked);
    if(this.session!==token) return false;
    this.slot=0;
    this.current={song:picked,info};
    this.currentNormal=info.bpm;
    this.currentRate=1;
    this.history.push(picked);
    this.engine.setCrossfade(0);
    audio.playbackRate=1;
    audio.preservesPitch=true;
    // Der erste Song startet am Anfang: der Hörer erlebt den Aufbau.
    audio.currentTime=0;
    await audio.play();
    if(this.session!==token) { audio.pause(); return false; }
    this.running=true;
    this.reportSong(picked,info);
    this.cb.plan?.(null);
    this.say("Set läuft · ich suche den dramaturgisch passenden nächsten Song …");
    this.timer=setInterval(()=>this.takt(),35);
    this.vorbereiten(token);
    return true;
  }

  async vorbereiten(token=this.session) {
    if (!this.running||this.next||this.preparing||this.session!==token) return;
    this.preparing=true;
    const {song:aktuell,info:infoA}=this.current;
    const zielEnergie=setEnergieZiel(this.story,this.history.length);
    const jetzt=this.engine.decks[this.slot].currentTime;
    const pool=this.pool.filter(s=>s.pfad!==aktuell.pfad);
    const versucht=new Set();
    const kandidaten=[];
    // Ein kleines exploratives Sample statt hundert gleichzeitig laufender ffmpeg-Prozesse.
    while(versucht.size<pool.length && kandidaten.length<6) {
      const offen=pool.filter(s=>!versucht.has(s.pfad));
      const sample=this.randomness ?
        waehleNaechsten(offen,this.history.map(s=>s.pfad),this.currentNormal*this.currentRate,Math.random,aktuell) :
        offen.sort((a,b)=>b.rating-a.rating||a.text.localeCompare(b.text,"de"))[0];
      if(!sample||versucht.has(sample.pfad)) break;
      versucht.add(sample.pfad);
      kandidaten.push(sample);
    }
    try {
      let beste=null;
      let reserve=null, syncReserve=null;
      // Maximal zwei Analyseaufträge gleichzeitig: Claude bleibt priorisiert.
      for(let i=0;i<kandidaten.length;i+=2) {
        const batch=await Promise.allSettled(kandidaten.slice(i,i+2).map(async song =>
          ({song, info:await this.info(song)})));
        if(this.session!==token||!this.running) return;
        for(const answer of batch) {
          if(answer.status!=="fulfilled") continue;
          const {song,info}=answer.value;
          reserve||={song,info};
          const match=tempoAngleichung(info.bpm,this.currentNormal*this.currentRate);
          if(match && Math.abs(1-match.rate)<=this.tolerance &&
             (!syncReserve||match.abweichung<syncReserve.match.abweichung)) syncReserve={song,info,match};
          const cue= findeUebergang(infoA,info,
            this.engine.decks[this.slot].currentTime+this.currentRate,this.bars,this.tolerance,zielEnergie,this.currentRate,this.currentNormal);
          if (!cue) continue;
          const taste=cue.score+(this.randomness?(Math.random()-.5)*.09:0);
          if(!beste||taste>beste.taste) beste={song,info,cue,taste};
        }
        if(beste) break;  // erst möglichst wenig Rechenzeit
      }
      if(!beste && reserve) {
        const {song,info}=syncReserve||reserve;
        const quelle=this.engine.decks[this.slot];
        const effektiv=this.currentNormal*this.currentRate;
        const startB=info.cues_in?.[0]?.zeit ?? info.bar0 ?? 0;
        const match=syncReserve?.match;
        const dauer=4*240/effektiv;
        const startA=naechsterTakt(quelle.currentTime+.5*this.currentRate,
          {bpm:infoA.bpm,beat0:infoA.bar0??infoA.beat0??0});
        const sync=Boolean(match && startA+dauer*this.currentRate<quelle.duration-.15 &&
          startB+dauer*match.rate<info.duration-.15);
        // Ohne Tempo-Match kein langer Crossfade mit gegeneinander laufenden Kicks.
        const cue={startA:sync?startA:Math.max(quelle.currentTime,quelle.duration-.1),
          startB,rateB:sync?match.rate:1,normalB:sync?match.normalized:info.bpm,
          bpm:sync?effektiv:info.bpm,bars:sync?4:0,dauer:sync?dauer:0,
          rateA:this.currentRate,normalA:this.currentNormal,sync,score:0,
          ausgang:sync?"Taktsynchroner Ersatzübergang":"Direktwechsel (kein sicherer Tempo-Match)",
          eingang:"Einstieg",energieA:0,energieB:0,confidence:0};
        beste={song,info,cue,taste:0};
        this.say(sync?"Keine sichere Phrase – taktsynchroner Ersatzübergang.":"Kein sicherer Tempo-Match – Direktwechsel ohne lange Überblendung.");
      }
      if(!beste) {
        this.say("Keine analysierbaren Kandidaten: Wiederhole die Suche in Kürze.");
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
      beste.zielEnergie=zielEnergie;
      this.next=beste;
      this.cb.plan?.(beste);
      this.say(beste.cue.sync?"Nächster Song vorbereitet · synchroner Übergang geplant.":"Nächster Song vorbereitet · Direktwechsel ohne Tempo-Match.");
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
    const cue=pending.cue;
    this.mix=true;
    this.mixEnd=null;
    const alt=this.slot, neu=1-alt;
    const a=this.engine.decks[alt], b=this.engine.decks[neu];
    const ziel=()=>Math.min(Math.max(0,b.duration-.05),
      Math.max(0,cue.startB+Math.max(0,a.currentTime-cue.startA)*cue.rateB/cue.rateA));
    try {
      b.preservesPitch=true;
      b.playbackRate=cue.rateB;
      b.currentTime=cue.sync?ziel():cue.startB;
      await wartenAufSeek(b);
      if(token!==this.session) return;
      await b.play();
      if(token!==this.session) return;
      // play()/Decoder können später starten als der Timer. Noch stumm nachziehen.
      if(cue.sync && Math.abs(syncFehler(a.currentTime,b.currentTime,cue))>.035 && !a.ended) {
        b.currentTime=ziel();
        await wartenAufSeek(b);
        if(token!==this.session) return;
      }
      const rest=cue.dauer-Math.max(0,a.currentTime-cue.startA)/cue.rateA;
      if(!cue.sync||a.ended||rest<.15) {
        this.uebernehmen();
        return;
      }
      b.playbackRate=syncRate(a.currentTime,b.currentTime,cue);
      this.engine.autoCrossfade(alt,rest);
      this.mixEnd=this.engine.ctx.currentTime+.03+rest;
      this.cb.transition?.(pending);
      this.say("LIVE-MIX · "+cue.bpm.toFixed(2)+" BPM · Beat-Sync aktiv");
    } catch(err) {
      if(token!==this.session) return;
      b.pause();
      this.mix=false;
      this.mixEnd=null;
      this.next=null;
      this.say("Übergang konnte nicht gestartet werden: "+(err.message||err));
      this.vorbereiten(token);
    }
  }

  uebernehmen() {
    const neu=this.next;
    if(!neu) return;
    this.engine.decks[this.slot].pause();
    this.slot=1-this.slot;
    this.current={song:neu.song,info:neu.info};
    // Halb-/Doppeltempo und nominelle Rate bleiben auch für Track C erhalten.
    this.currentNormal=neu.cue.normalB??neu.info.bpm;
    this.currentRate=neu.cue.rateB;
    this.engine.decks[this.slot].playbackRate=this.currentRate;
    this.next=null;
    this.mix=false;
    this.mixEnd=null;
    this.history.push(neu.song);
    this.history=this.history.slice(-40);
    this.engine.setCrossfade(this.slot===0?0:100);
    this.reportSong(neu.song,neu.info);
    this.cb.plan?.(null);
    this.say("Neuer Song übernommen · "+(this.currentNormal*this.currentRate).toFixed(2)+" BPM · nächster Übergang wird gesucht …");
    this.vorbereiten();
  }

  takt() {
    if(!this.running||!this.current) return;
    const a=this.engine.decks[this.slot];
    if(this.mix && this.next) {
      // Solange play()/seek noch laufen, darf das neue Deck nicht übernommen werden.
      if(this.mixEnd!==null) {
        const b=this.engine.decks[1-this.slot];
        if(a.ended||this.engine.ctx.currentTime>=this.mixEnd) this.uebernehmen();
        else if(!a.seeking&&!b.seeking&&!a.paused&&!b.paused)
          b.playbackRate=syncRate(a.currentTime,b.currentTime,this.next.cue);
      }
    } else if(this.next && (a.currentTime>=this.next.cue.startA||a.ended)) {
      this.wechsel();
    } else if(a.ended) {
      this.say("Track beendet, nächster Übergang wird vorbereitet …");
      this.vorbereiten();
    }
    const aktiv=this.engine.decks[this.slot];
    this.cb.progress?.(aktiv.currentTime,aktiv.duration,this.next?.cue||null);
  }

  naechsterTakt() {
    if(!this.next||!this.current||this.mix) return;
    const audio=this.engine.decks[this.slot];
    const cue=this.next.cue;
    cue.startA=naechsterTakt(audio.currentTime+.5*this.currentRate,
      {bpm:this.current.info.bpm,beat0:this.current.info.bar0??this.current.info.beat0??0});
    if(cue.sync && cue.startA+cue.dauer*this.currentRate>=audio.duration)
      cue.dauer=Math.max(0,(audio.duration-cue.startA-.15)/this.currentRate);
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
    this.currentRate=1;
    this.currentNormal=null;
    this.mixEnd=null;
    for(const audio of this.engine.decks) audio.pause();
    this.engine.setCrossfade(0);
    this.cb.plan?.(null);
  }

  destroy() { this.stop(); this.engine.beenden(); }
}
