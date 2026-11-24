import {AudioCore} from "./audio_core.js";

// Bestehender StemAudio bleibt unverändert. Vor dem Wechsel dessen
// Ausgabepfad beenden; dekodierte AudioBuffer bleiben verwendbar.
export async function takeOverStems(player,latencies=player.buffers.map(()=>0)) {
    if(!player.bereit) throw new Error("Stem-Player nicht bereit");
    const buffers=player.buffers.slice(), seconds=player.position();
    player.beenden();
    const core=await AudioCore.open(latencies);
    return {core,buffers,source:Math.round(seconds*core.rate),
        play(options={}){return core.play(buffers,{source:Math.round(seconds*core.rate),...options});},
        destroy(){return core.destroy();}};
}
