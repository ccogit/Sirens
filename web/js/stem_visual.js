// Sirens Warp Stage: shaderbasierte 3D-Bühne, direkt gekoppelt an den gemischten Stem-Ausgang.
// Rendering erfolgt nur im sichtbaren Spiel, ohne externe Assets oder zusätzliche GPU-KI.
import { STEM_VERTEX, STEM_FRAGMENT } from "./stem_visual_shader.js";

export const RENDER_PROFILE = Object.freeze({
  eco:   { fps: 15, scale: .65, steps: 34, maxWidth: 1000, maxHeight: 700 },
  live:  { fps: 45, scale: 1.05, steps: 76, maxWidth: 2200, maxHeight: 1400 },
  ultra: { fps: 60, scale: 1.85, steps: 160, maxWidth: 3840, maxHeight: 2160 },
});

export function renderProfil(modus, produktion, bewegungReduziert = false) {
  if (bewegungReduziert || produktion) return RENDER_PROFILE.eco;
  return RENDER_PROFILE[modus] || RENDER_PROFILE.live;
}

export function frequenzBaender(frequenzen, sampleRate = 44100, fftSize = 2048) {
  // Drei getrennte Energiebänder: 28–160 Hz, 160–2200 Hz, 2200–11000 Hz.
  const band = (von, bis) => {
    const lo = Math.max(1, Math.floor(von / (sampleRate / fftSize)));
    const hi = Math.min(frequenzen.length, Math.ceil(bis / (sampleRate / fftSize)));
    let sum = 0;
    for (let i = lo; i < hi; i++) sum += (frequenzen[i] || 0) / 255;
    return Math.min(1, sum / Math.max(1, hi - lo) * 1.6);
  };
  return [band(28, 160), band(160, 2200), band(2200, 11000)];
}

function shader(gl, typ, text) {
  const s = gl.createShader(typ);
  gl.shaderSource(s, text);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    const fehler = gl.getShaderInfoLog(s);
    gl.deleteShader(s);
    throw new Error("Shader-Fehler: " + fehler);
  }
  return s;
}

function gpuStart(canvas) {
  const gl = canvas.getContext("webgl2", {
    alpha: false, antialias: false, depth: false, stencil: false,
    preserveDrawingBuffer: false, powerPreference: "high-performance",
  });
  if (!gl) return null;
  const programm = gl.createProgram();
  let vs, fs;
  try {
    vs = shader(gl, gl.VERTEX_SHADER, STEM_VERTEX);
    fs = shader(gl, gl.FRAGMENT_SHADER, STEM_FRAGMENT);
    gl.attachShader(programm, vs);
    gl.attachShader(programm, fs);
    gl.linkProgram(programm);
    if (!gl.getProgramParameter(programm, gl.LINK_STATUS)) {
      throw new Error("Shader-Link: " + gl.getProgramInfoLog(programm));
    }
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    return {gl, programm, vao, uniform: Object.fromEntries(
      ["u_resolution", "u_time", "u_audio", "u_beat", "u_scene", "u_steps"]
        .map(name => [name, gl.getUniformLocation(programm, name)]))};
  } finally {
    if (vs) gl.deleteShader(vs);
    if (fs) gl.deleteShader(fs);
    if (!gl.getProgramParameter(programm, gl.LINK_STATUS)) gl.deleteProgram(programm);
  }
}

function fallbackMalen(canvas, now, baender) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = canvas.width, h = canvas.height;
  const verlauf = ctx.createRadialGradient(w*.5,h*.5,10,w*.5,h*.5,w*.7);
  verlauf.addColorStop(0,"#223e78"); verlauf.addColorStop(.5,"#100d38"); verlauf.addColorStop(1,"#020817");
  ctx.fillStyle = verlauf;
  ctx.fillRect(0, 0, w, h);
  const [bass,mid,hoch] = baender;
  const groesse = Math.min(w,h);
  for (let i=0;i<26;i++) {
    const radius=groesse*(.055+i*.019)*(1+bass*.18);
    ctx.strokeStyle = "hsla(" + (180+i*8+now*.008) + ",100%,70%," + (.12+.5*(1-i/26)) + ")";
    ctx.lineWidth = 1+mid*2;
    ctx.beginPath();
    ctx.ellipse(w/2,h/2,radius,radius*(.75+hoch*.14),now*.00007+i*.1,0,Math.PI*2);
    ctx.stroke();
  }
}

export function warpStage(canvas, getAnalyser, isProducing, isActive, options, onStatus = () => {}) {
  const reduziert = Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  const beginn = performance.now();
  let active=true, raf=0, letzteZeit=0, gemessen=0, bilder=0, fps=0;
  let bassAlt=0, beat=0, daten=new Uint8Array(1024), gpu=null, fehlermeldung="";
  const verloren = e => { e.preventDefault(); gpu=null; fehlermeldung="GPU-Kontext verloren"; };
  const wieder = () => { gpu=null; fehlermeldung=""; };
  canvas.addEventListener("webglcontextlost", verloren);
  canvas.addEventListener("webglcontextrestored", wieder);

  function frame(now) {
    if (!active) return;
    raf=requestAnimationFrame(frame);
    if (document.hidden || !isActive() || canvas.clientWidth < 1) return;
    const produktiv = Boolean(isProducing());
    const profil = renderProfil(options.modus, produktiv, reduziert);
    if (now-letzteZeit < 1000/profil.fps) return;
    letzteZeit=now;
    if (!gpu && !fehlermeldung) {
      try { gpu=gpuStart(canvas); }
      catch(err) { fehlermeldung=err.message || "WebGL2 nicht verfügbar"; }
    }
    const dpr = Math.min(2.5, window.devicePixelRatio || 1);
    const scale = Math.min(1.5, Math.max(.5, Number(options.dichte) || 1));
    const w=Math.max(1,Math.min(profil.maxWidth,Math.round(canvas.clientWidth * dpr * profil.scale * scale)));
    const h=Math.max(1,Math.min(profil.maxHeight,Math.round(canvas.clientHeight * dpr * profil.scale * scale)));
    if (canvas.width !== w || canvas.height !== h) {canvas.width=w;canvas.height=h;}
    const analyser=getAnalyser();
    let bands=[0,0,0], laufend=Boolean(analyser);
    if (analyser) {
      if (daten.length !== analyser.frequencyBinCount) daten=new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(daten);
      bands=frequenzBaender(daten,analyser.context?.sampleRate || 44100,analyser.fftSize || 2048);
    } else {
      const t=now*.001;
      // Demo-Animation ohne vorgetäuschte Audiomesswerte.
      bands=[.17+.08*Math.sin(t*.83),.12+.07*Math.sin(t*1.13),.08+.06*Math.sin(t*1.91)];
    }
    const neuerBeat=Math.max(0,(bands[0]-bassAlt)*3.8);
    beat=Math.max(neuerBeat,beat*.83);
    bassAlt=bassAlt*.7+bands[0]*.3;
    const t=(now-beginn)/1000;
    if (gpu) {
      const {gl,programm,uniform,vao}=gpu;
      gl.viewport(0,0,w,h);
      gl.useProgram(programm);
      gl.bindVertexArray(vao);
      gl.uniform2f(uniform.u_resolution,w,h);
      gl.uniform1f(uniform.u_time,reduziert?0:t);
      gl.uniform3f(uniform.u_audio,...bands);
      gl.uniform1f(uniform.u_beat,beat);
      gl.uniform1i(uniform.u_scene,options.szene || 0);
      gl.uniform1i(uniform.u_steps,profil.steps);
      gl.drawArrays(gl.TRIANGLES,0,3);
    } else fallbackMalen(canvas,now,bands);
    bilder++;
    if (now-gemessen>1200) {
      fps=Math.round(bilder*1000/Math.max(1,now-gemessen));
      onStatus({
        fps,w,h,steps:profil.steps,eco:produktiv,renderer:gpu?"WebGL2 · GPU":"Canvas 2D",
        demo:!laufend,fehler:fehlermeldung,
      });
      gemessen=now;bilder=0;
    }
  }
  raf=requestAnimationFrame(frame);
  return () => {
    active=false;
    cancelAnimationFrame(raf);
    canvas.removeEventListener("webglcontextlost",verloren);
    canvas.removeEventListener("webglcontextrestored",wieder);
    if (gpu) {
      gpu.gl.deleteVertexArray(gpu.vao);
      gpu.gl.deleteProgram(gpu.programm);
    }
  };
}
