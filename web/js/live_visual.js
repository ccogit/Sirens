// GPU-Visuals via WebGL2, mit Canvas-2D-Fallback und echten Analyzer-Daten.
// Auflösung und FPS sind gedeckelt, damit Claude und die Musikerzeugung Vorrang haben.
const VERTEX = "#version 300 es\nin vec2 position;\nvoid main() { gl_Position = vec4(position, 0.0, 1.0); }";
const FRAGMENT = [
  "#version 300 es",
  "precision highp float;",
  "uniform vec2 resolution;",
  "uniform float time;",
  "uniform vec3 bands;",
  "out vec4 pixel;",
  "float hash(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }",
  "void main() {",
  "  vec2 uv = (gl_FragCoord.xy - 0.5 * resolution) / resolution.y;",
  "  float r = length(uv), a = atan(uv.y,uv.x);",
  "  float bass = bands.x, mid = bands.y, high = bands.z;",
  "  vec3 col = vec3(0.007,0.014,0.045) + 0.032 * vec3(0.04,0.12,0.40) / (r+0.14);",
  "  float wave = sin(a*7.0 - time*0.6 + sin(a*3.0+time)*0.6);",
  "  for (int i=0;i<25;i++) {",
  "    float f = float(i);",
  "    float radius = 0.105 + f*0.020 + bass*0.055 * sin(a*4.0+time*1.2+f*0.22);",
  "    radius += (0.006 + mid*0.013) * sin(a*(7.0+mod(f,5.0))+time*(0.9+high)+f*0.7);",
  "    float edge = abs(r-radius);",
  "    float glow = 0.0015 / (edge+0.006) * (0.4+0.6*sin(f*0.14+time*0.12)*sin(f*0.14+time*0.12));",
  "    vec3 tint = mix(vec3(0.05,0.55,0.96),vec3(0.94,0.12,0.72),sin(f*0.13+time*0.18)*0.5+0.5);",
  "    col += tint * glow * (1.0-smoothstep(0.28,0.94,r));",
  "  }",
  "  float core = 0.021 / (r+0.027) * (0.3+bass*0.8);",
  "  col += vec3(0.04,0.36,0.65) * core;",
  "  vec2 cell = floor((uv+time*vec2(0.002,0.001))*155.0);",
  "  float star = step(0.9965,hash(cell))*pow(max(0.0,1.0-length(fract(uv*155.0)-0.5)*1.8),7.0);",
  "  col += vec3(0.24,0.59,0.97)*star*(0.5+high);",
  "  col *= (1.0-smoothstep(0.18,1.08,r));",
  "  pixel = vec4(pow(clamp(col,0.0,1.0),vec3(0.84)),1.0);",
  "}"
].join("\n");

function gpuEinrichten(canvas) {
  const gl = canvas.getContext("webgl2", { alpha: false, antialias: false, powerPreference: "high-performance" });
  if (!gl) return null;
  const shader = (type, source) => {
    const s = gl.createShader(type);
    gl.shaderSource(s, source);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  };
  try {
    const program = gl.createProgram();
    gl.attachShader(program, shader(gl.VERTEX_SHADER, VERTEX));
    gl.attachShader(program, shader(gl.FRAGMENT_SHADER, FRAGMENT));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,1,1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, "position");
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    return { gl, program, buffer, resolution: gl.getUniformLocation(program, "resolution"),
      time: gl.getUniformLocation(program, "time"), bands: gl.getUniformLocation(program, "bands") };
  } catch {
    return null;
  }
}

export function visualisieren(canvas, hud, getAnalyser, getModus, isProducing = () => false) {
  const gpu = gpuEinrichten(canvas);
  const ctx = hud.getContext("2d");
  const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  let frame = 0, letzter = 0, gestartet = performance.now(), aktiv = true;
  let freq = new Uint8Array(1024), wave = new Uint8Array(2048);

  function groesse(el) {
    const ratio = Math.min(window.devicePixelRatio || 1, isProducing() ? 1 : 1.5);
    const width = Math.min(isProducing() ? 1000 : 1600, Math.max(1, Math.round(el.clientWidth * ratio)));
    const height = Math.min(isProducing() ? 600 : 1000, Math.max(1, Math.round(el.clientHeight * ratio)));
    if (el.width !== width || el.height !== height) { el.width = width; el.height = height; }
  }

  function daten(t) {
    const analyser = getAnalyser();
    if (analyser) {
      if (freq.length !== analyser.frequencyBinCount) freq = new Uint8Array(analyser.frequencyBinCount);
      if (wave.length !== analyser.fftSize) wave = new Uint8Array(analyser.fftSize);
      analyser.getByteFrequencyData(freq);
      analyser.getByteTimeDomainData(wave);
    } else {
      // Dekorative Demo, bis Ton vorhanden ist; keine vorgetäuschten Song-Messwerte.
      for (let i = 0; i < freq.length; i++) freq[i] = Math.max(0,
        110 * Math.abs(Math.sin(i*0.12+t*1.6))*Math.exp(-i/175));
      for (let i = 0; i < wave.length; i++) wave[i] = 128 + 48*Math.sin(i*0.036+t*3)*Math.sin(i*0.005+t);
    }
  }

  function balken() {
    const w = hud.width, h = hud.height, count = 72, bw = w/count;
    ctx.fillStyle = "#060e24";
    ctx.fillRect(0, 0, w, h);
    for (let i=0; i<count; i++) {
      const v = freq[Math.floor(i/count*freq.length*0.68)]/255;
      const bh = Math.max(2, v*v*h*1.5);
      ctx.fillStyle = "hsl(" + (185+i*2.2) + " 95% " + (45+i*0.18) + "%)";
      ctx.fillRect(i*bw+1, h-bh, Math.max(1,bw-2), bh);
    }
  }

  function oszilloskop() {
    const w = hud.width, h = hud.height;
    ctx.fillStyle = "#060e24";
    ctx.fillRect(0,0,w,h);
    ctx.strokeStyle = "rgba(75,187,239,.14)";
    ctx.lineWidth = 1;
    for (let i=1; i<8; i++) {
      ctx.beginPath(); ctx.moveTo(0,h*i/8); ctx.lineTo(w,h*i/8); ctx.stroke();
    }
    ctx.beginPath();
    ctx.lineWidth = Math.max(2,w/550);
    ctx.strokeStyle = "#4de6d5";
    for (let x=0; x<w; x++) {
      const value = wave[Math.floor(x/w*wave.length)]/255;
      const y = h*(0.5+(0.5-value)*0.75);
      if (x===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    }
    ctx.stroke();
  }

  function zeichnen(now) {
    if (!aktiv) return;
    frame = requestAnimationFrame(zeichnen);
    if (document.hidden || canvas.closest(".lab-toy")?.hidden || now - letzter < (reduced ? 100 : isProducing() ? 66 : 33)) return;
    letzter = now;
    const t = (now-gestartet)/1000;
    daten(t);
    const mode = getModus();
    const cosmic = mode === "cosmic" && Boolean(gpu);
    canvas.hidden = !cosmic;
    hud.hidden = cosmic;
    if (cosmic) {
      groesse(canvas);
      const avg = (a,b) => {
        let sum=0;
        for (let i=a; i<b; i++) sum += freq[i] || 0;
        return sum/Math.max(1,b-a)/255;
      };
      const {gl} = gpu;
      gl.viewport(0,0,canvas.width,canvas.height);
      gl.useProgram(gpu.program);
      gl.uniform2f(gpu.resolution,canvas.width,canvas.height);
      gl.uniform1f(gpu.time,reduced ? 0 : t);
      gl.uniform3f(gpu.bands,avg(1,20),avg(20,140),avg(140,400));
      gl.drawArrays(gl.TRIANGLE_STRIP,0,4);
    } else if (ctx) {
      groesse(hud);
      if (mode === "scope") oszilloskop(); else balken();
    }
  }
  frame = requestAnimationFrame(zeichnen);
  return () => {
    aktiv = false;
    cancelAnimationFrame(frame);
    if (gpu) {
      gpu.gl.deleteBuffer(gpu.buffer);
      gpu.gl.deleteProgram(gpu.program);
    }
  };
}
