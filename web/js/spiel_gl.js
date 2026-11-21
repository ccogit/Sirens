// Emblem der Spielwiese auf der Grafikkarte: das gespiegelte Spektral-Emblem aus dem Cover-Konzept, hier lebendig.
// Zwölf Achsen des Songs bestimmen Form und Farbe; das laufende Spektrum treibt die Säulen, eine Rückkopplung zieht Spuren.

const ECKEN = `#version 300 es
void main() { vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2); gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0); }`;

// Achsen in uA: 0 Energie, 1 Tanzbar, 2 Experiment, 3 Wärme, 4 Dunkel, 5 Psychedelik, 6 Organisch, 7 Elektronisch,
// 8 Melodie, 9 Groove, 10 Stimme, 11 Sampling (je 0…1)
const SZENE = `#version 300 es
precision highp float;
uniform vec2 uGroesse; uniform float uZeit; uniform float uA[12]; uniform float uBpm; uniform float uDur;
uniform vec3 uKraft; uniform vec3 uZeiger; uniform sampler2D uSpektrum; uniform sampler2D uVorher;
out vec4 aus;
float h1(float n) { return fract(sin(n * 127.1) * 43758.5453); }
vec3 hsl(float h, float s, float l) {
  vec3 k = mod(vec3(0.0, 8.0, 4.0) + fract(h) * 12.0, 12.0);
  return l - s * min(l, 1.0 - l) * max(min(min(k - 3.0, 9.0 - k), 1.0), -1.0);
}
float kasten(vec2 p, vec2 b, float r) { vec2 q = abs(p) - b + r; return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r; }
float licht(float d, float aa, float schein) { return smoothstep(aa, 0.0, d) + schein * exp(-max(d, 0.0) * 34.0); }
void main() {
  vec2 uv = gl_FragCoord.xy / uGroesse;
  vec2 p = (gl_FragCoord.xy - 0.5 * uGroesse) / (0.5 * uGroesse.y);
  float E = uA[0], D = uA[1], X = uA[2], W = uA[3], K = uA[4], P = uA[5], M = uA[8], G = uA[9], V = uA[10], S = uA[11];
  float org = uA[6] / (uA[6] + uA[7] + 0.001);
  float bass = uKraft.x, mitte = uKraft.y;
  float aa = 2.5 / uGroesse.y;

  // Farben: Farbton aus Wärme und Tongeschlecht (über Violett, nie über Grün), Sättigung aus Energie, Helligkeit aus Dunkelheit
  float ton = (220.0 + 160.0 * W + (uDur > 0.5 ? 12.0 : -12.0)) / 360.0;
  float satt = min(0.92, 0.38 + 0.45 * E + 0.2 * P);
  float hell = 0.66 - 0.26 * K;
  vec3 haupt = hsl(ton, satt, hell);
  vec3 akzent = hsl(ton + (25.0 + 140.0 * P) / 360.0, satt, hell + 0.06);
  vec3 tinte = vec3(0.93, 0.94, 1.0);
  vec3 c = vec3(0.0);

  // Ringe hinter dem Emblem (Psychedelik): bis zu fünf, gestrichelt, sie atmen mit dem Bass
  float r = length(p), winkel = atan(p.y, p.x);
  for (int i = 0; i < 5; i++) {
    if (float(i) >= floor(P * 5.0 + 0.5)) break;
    float fi = float(i);
    float d = abs(r - (0.42 + 0.19 * fi + 0.06 * bass * sin(uZeit * 1.7 + fi))) - 0.004;
    float strich = step(0.35, fract(winkel * (6.0 + fi * 2.0) / 6.2832 + uZeit * 0.06 * (mod(fi, 2.0) * 2.0 - 1.0)));
    c += akzent * strich * licht(d, aa, 0.3) * 0.75;
  }

  // Säulen: Zahl und Höhe aus Energie, Hüllkurve aus Melodie, Segmente aus Tanzbarkeit und Groove, Lücken und Schieflage aus Experiment
  float seite = sign(p.x);
  vec2 q = p;
  if (seite > 0.0) { q.y -= X * 0.12 * sin(uZeit * 0.4); q.y /= (1.0 - 0.18 * X); }
  float spalten = floor(mix(4.0, 11.0, E) + 0.5);
  float spann = mix(0.62, 1.25, E);
  float breite = spann / spalten;
  float nr = floor(abs(q.x) / breite);
  if (nr < spalten) {
    float t = (nr + 0.5) / spalten;
    float spektrum = texture(uSpektrum, vec2(pow(t, 1.5) * 0.7 + 0.01, 0.5)).r;
    float hoch = mix(0.35 + 0.65 * h1(nr + 3.0), exp(-t * t * 3.0), M) * mix(0.35, 0.62, E) * (0.5 + 1.0 * spektrum);
    float dx = abs(q.x) - (nr + 0.5) * breite + org * 0.012 * sin(q.y * 14.0 + uZeit * 1.6 + nr);
    float y = abs(q.y) + (h1(nr * 7.3) - 0.5) * (1.0 - D) * breite * 0.9;
    float lang = breite * 0.95;
    float n = floor(y / (2.0 * lang));
    float f = y - n * 2.0 * lang;
    float erster = lang * (1.0 + 0.33 * G);                       // Groove: lang und kurz wechseln sich ab
    float zweites = step(erster, f);
    float laenge = mix(erster, 2.0 * lang - erster, zweites);
    float fy = f - zweites * erster - laenge * 0.5;
    float kennung = n * 2.0 + zweites + nr * 31.0 + (seite > 0.0 && X > 0.5 ? 17.0 : 0.0);
    vec2 halb = vec2(breite * 0.3, max(laenge * 0.5 - breite * 0.09, 0.004));
    float d = kasten(vec2(dx, fy), halb, org * min(halb.x, halb.y));
    float da = step(abs(q.y), hoch) * step(0.3 * X, h1(kennung + 5.0));
    c += (h1(kennung + 9.0) < G * 0.5 ? akzent : haupt) * da * licht(d, aa, 0.3 + 0.6 * bass);
  }

  // Rückgrat mit Perlen (Tempo): eine Perle je 16 Schläge pro Minute und Seite, sie springen mit dem Bass
  c += tinte * step(abs(p.x), spann * 1.08) * smoothstep(aa, 0.0, abs(p.y) - 0.004) * 0.8;
  float perlen = max(2.0, floor(uBpm / 16.0 + 0.5));
  float schritt = spann * 1.08 / perlen;
  float pn = floor(abs(p.x) / schritt);
  if (pn < perlen) {
    float dp = length(vec2(abs(p.x) - (pn + 0.5) * schritt, p.y)) - 0.022 * (1.0 - 0.6 * pn / perlen) * (1.0 + 0.9 * bass);
    c += tinte * licht(dp, aa, 0.45);
  }

  // Stimmlinie durch die Mitte (Stimme) und Echos des Kerns darüber und darunter (Sampling)
  float vx = p.x - org * 0.01 * sin(p.y * 11.0 + uZeit * 2.0) * (0.5 + mitte);
  float dv = max(abs(vx) - mix(0.003, 0.016, V), abs(p.y) - mix(0.25, 0.95, V) * (0.85 + 0.3 * mitte));
  c += tinte * licht(dv, aa, 0.3 * V);
  for (int i = 0; i < 4; i++) {
    if (float(i) >= floor(S * 4.0 + 0.5)) break;
    float fi = float(i);
    float kx = clamp(floor(abs(p.x) / 0.045 + 0.5), 0.0, 2.0);
    float de = kasten(vec2(abs(p.x) - kx * 0.045, abs(p.y) - 0.7 - 0.085 * fi), vec2(0.012, 0.03 * (1.0 - kx * 0.3)) * (1.0 - 0.15 * fi), org * 0.01);
    c += haupt * (1.0 - 0.2 * fi) * licht(de, aa, 0.3);
  }

  // Zeiger auf der Fläche
  if (uZeiger.z > 0.5) {
    float dz = length(p - vec2((uZeiger.x * 2.0 - 1.0) * uGroesse.x / uGroesse.y, uZeiger.y * 2.0 - 1.0));
    c += akzent * 0.6 * exp(-dz * 9.0) + tinte * smoothstep(0.016, 0.011, dz);
  }

  // Rückkopplung: das vorige Bild, leicht gezoomt und gedreht; Psychedelik und Sampling ziehen die Spuren länger
  vec2 z = uv - 0.5;
  float dreh = 0.004 * (X - 0.3) + 0.012 * P * sin(uZeit * 0.3);
  z = mat2(cos(dreh), -sin(dreh), sin(dreh), cos(dreh)) * z * (1.0 - 0.012 - 0.04 * bass * (0.3 + P));
  vec3 vorher = texture(uVorher, z + 0.5).rgb;
  vorher = mix(vorher, vorher.gbr, 0.05 * P) * mix(0.8, 0.94, max(P, 0.75 * S)) * (1.0 - 0.3 * length(z));  // zum Rand hin verblassen, sonst wird alles weiß
  aus = vec4(max(c, vorher), 1.0);
}`;

const ZEIGEN = `#version 300 es
precision highp float;
uniform vec2 uGroesse; uniform float uBass; uniform sampler2D uBild;
out vec4 aus;
void main() {
  vec2 uv = gl_FragCoord.xy / uGroesse;
  vec2 d = (uv - 0.5) * (0.004 + 0.012 * uBass);                         // Farbsäume, stärker bei Bass
  vec3 f = vec3(texture(uBild, uv + d).r, texture(uBild, uv).g, texture(uBild, uv - d).b);
  f += vec3(0.03, 0.045, 0.1) * (1.0 - length(uv - 0.5));                 // dunkelblauer Grund
  aus = vec4(pow(f, vec3(0.9)) * (1.0 - 0.9 * dot(uv - 0.5, uv - 0.5)), 1.0);
}`;

function programm(gl, quelle) {
  const bauen = (art, text) => {
    const s = gl.createShader(art);
    gl.shaderSource(s, text); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  };
  const p = gl.createProgram();
  gl.attachShader(p, bauen(gl.VERTEX_SHADER, ECKEN)); gl.attachShader(p, bauen(gl.FRAGMENT_SHADER, quelle));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  return p;
}

function textur(gl, filter = gl.LINEAR) {
  const t = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, t);
  for (const [name, wert] of [[gl.TEXTURE_MIN_FILTER, filter], [gl.TEXTURE_MAG_FILTER, filter], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, name, wert);
  return t;
}

// Liefert { malen(zustand) } oder null, wenn der Browser kein WebGL 2 hat oder die Shader nicht übersetzen.
// zustand: { zeit (s), achsen (12 Werte 0–10), bpm, dur, kraft [Bass, Mitten, Höhen], spektrum (Uint8Array) | null, zeiger {x, y} | null }
export function emblemBild(leinwand) {
  const gl = leinwand.getContext("webgl2", { antialias: false, alpha: false, powerPreference: "high-performance" });
  if (!gl) return null;
  let szene; let zeigen;
  try { szene = programm(gl, SZENE); zeigen = programm(gl, ZEIGEN); } catch { return null; }
  const ort = (p, name) => gl.getUniformLocation(p, name);
  const spektrum = textur(gl);
  const ruhe = new Uint8Array(256);
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  let bilder = null; // zwei Bilder im Wechsel: aus dem einen lesen, ins andere malen
  let breite = 0; let hoehe = 0; let wechsel = 0;

  function anpassen() {
    const [w, h] = [Math.round(leinwand.clientWidth * Math.min(2, devicePixelRatio)), Math.round(leinwand.clientHeight * Math.min(2, devicePixelRatio))];
    if (!w || !h || (w === breite && h === hoehe)) return Boolean(bilder);
    [breite, hoehe] = [w, h];
    leinwand.width = w; leinwand.height = h;
    for (const b of bilder || []) { gl.deleteTexture(b.t); gl.deleteFramebuffer(b.f); }
    bilder = [0, 1].map(() => {
      const t = textur(gl);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      const f = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, f);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
      return { t, f };
    });
    return true;
  }

  return {
    malen(z) {
      if (gl.isContextLost() || !anpassen()) return;
      const [von, nach] = [bilder[wechsel], bilder[1 - wechsel]];
      wechsel = 1 - wechsel;
      let daten = z.spektrum;
      if (!daten) { // ohne Ton: eine ruhige Dünung, damit das Emblem atmet
        for (let i = 0; i < 256; i += 1) ruhe[i] = 70 + 50 * Math.sin(z.zeit * 0.9 + i * 0.09) * Math.exp(-i / 180);
        daten = ruhe;
      }
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, spektrum);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, 256, 1, 0, gl.RED, gl.UNSIGNED_BYTE, daten.subarray(0, 256));
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, von.t);
      gl.bindFramebuffer(gl.FRAMEBUFFER, nach.f);
      gl.viewport(0, 0, breite, hoehe);
      gl.useProgram(szene);
      gl.uniform2f(ort(szene, "uGroesse"), breite, hoehe);
      gl.uniform1f(ort(szene, "uZeit"), z.zeit);
      gl.uniform1fv(ort(szene, "uA"), Float32Array.from(z.achsen, (w) => w / 10));
      gl.uniform1f(ort(szene, "uBpm"), z.bpm);
      gl.uniform1f(ort(szene, "uDur"), z.dur ? 1 : 0);
      gl.uniform3f(ort(szene, "uKraft"), ...z.kraft);
      gl.uniform3f(ort(szene, "uZeiger"), z.zeiger?.x ?? 0, z.zeiger?.y ?? 0, z.zeiger ? 1 : 0);
      gl.uniform1i(ort(szene, "uSpektrum"), 0);
      gl.uniform1i(ort(szene, "uVorher"), 1);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.useProgram(zeigen);
      gl.bindTexture(gl.TEXTURE_2D, nach.t);
      gl.uniform2f(ort(zeigen, "uGroesse"), breite, hoehe);
      gl.uniform1f(ort(zeigen, "uBass"), z.kraft[0]);
      gl.uniform1i(ort(zeigen, "uBild"), 1);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    },
  };
}
