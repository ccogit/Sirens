// WebGL2 GLSL: 3D-Raymarching mit prozeduralem Licht, Fraktalfaltung und Neon-Korridor.
// Keine Assets, Texturen oder Netzwerkanfragen. Quality wird zur Laufzeit begrenzt.
export const STEM_VERTEX = `#version 300 es
precision highp float;
void main() {
  vec2 p = vec2[3](vec2(-1.,-1.),vec2(3.,-1.),vec2(-1.,3.))[gl_VertexID];
  gl_Position = vec4(p,0.,1.);
}`;

export const STEM_FRAGMENT = `#version 300 es
precision highp float;
out vec4 fragColor;
uniform vec2 u_resolution;
uniform float u_time;
uniform vec3 u_audio;
uniform float u_beat;
uniform int u_scene;
uniform int u_steps;

#define PI 3.14159265359
mat2 rot(float a) {float c=cos(a),s=sin(a);return mat2(c,-s,s,c);}
float hash(vec3 p) {p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
vec3 palette(float x) {
  float shift=float(u_scene)*.14;
  return .52+.48*cos(6.28318*(vec3(.12,.4,.72)+x*vec3(.82,.55,.73)+shift));
}
float smin(float a, float b, float k) {
  float h=max(k-abs(a-b),0.)/k;
  return min(a,b)-h*h*k*.25;
}
// Korridor aus Torus-Ringen, kaleidoskopischen Stegen und einem vibrierenden Plasmakern.
vec2 distanceField(vec3 p) {
  float t=u_time, bass=u_audio.x, mid=u_audio.y;
  p.xy*=rot(p.z*.115+t*.13);
  float slice=mod(p.z+2.5,5.)-2.5;
  float angle=atan(p.y,p.x), radius=length(p.xy);
  float petals=cos(angle*(u_scene==1?8.:6.) + p.z*.65+t*.35);
  float ring=length(vec2(radius-(2.35+.24*bass),slice))-.11;
  float portal=abs(radius-(3.4+.23*petals+.18*sin(p.z*2.+t)))-.055;
  float spoke=abs(sin(angle*8.+p.z*.9))*radius-.045;
  float spokeSlice=abs(slice)-.12;
  float struts=max(spoke,spokeSlice);
  float shape=min(ring,smin(portal,struts,.25));
  float id=0.;
  vec3 k=p;
  k.z=mod(k.z+1.4,2.8)-1.4;
  for (int i=0;i<5;i++) {
    k.xy=abs(k.xy);
    k.xy=rot(.64+.09*float(i)+mid*.28)*k.xy;
    k=k*1.23-.48;
  }
  float sculpture=length(k.xy)-(.28+.12*sin(p.z*3.+t+mid*3.));
  sculpture=abs(sculpture)*.29+.15*abs(k.z)-.095;
  if (u_scene==1) {
    shape=min(shape,sculpture);
    id=1.;
  } else if (u_scene==2) {
    float spiral=abs(sin(angle*11.+p.z*1.8+t*.65))*radius-.065;
    shape=min(shape,max(spiral,abs(radius-2.0)-.11));
    shape=min(shape,sculpture*.7);
    id=2.;
  }
  return vec2(shape,id);
}
float clouds(vec3 p) {
  float s=0.,amp=.55;
  for(int i=0;i<4;i++) {
    s+=amp*sin(p.x*1.3+sin(p.z+u_time*.17))
          *cos(p.y*1.6-p.z*.73+u_time*.21);
    p=p.yzx*1.87; amp*=.49;
  }
  return s;
}
void main() {
  vec2 uv=(gl_FragCoord.xy-.5*u_resolution)/u_resolution.y;
  float t=u_time, bass=u_audio.x, mid=u_audio.y, treble=u_audio.z;
  float speed=1.35+.92*bass+u_beat*.65;
  float travel=t*speed;
  vec3 ro=vec3(.17*sin(t*.33),.12*cos(t*.22),travel);
  vec3 ta=vec3(.23*sin(t*.41),.2*cos(t*.37),travel+3.5);
  vec3 ww=normalize(ta-ro);
  vec3 uu=normalize(cross(ww,vec3(0.,1.,0.)));
  vec3 vv=normalize(cross(uu,ww));
  vec3 rd=normalize(uv.x*uu+uv.y*vv+1.65*ww);
  rd.xy=rot(.16*sin(t*.19)+.1*mid)*rd.xy;
  float dst=0.,hit=0.,tag=0.;
  vec3 glow=vec3(0.);
  vec3 p=ro;
  for(int i=0;i<192;i++) {
    if(i>=u_steps) break;
    p=ro+rd*dst;
    vec2 field=distanceField(p);
    float d=field.x;
    float light=exp(-9.0*abs(d))*(.009+.007*bass)/(1.+dst*.095);
    vec3 plasma=palette(p.z*.045+atan(p.y,p.x)*.24+t*.06+mid*.18);
    glow+=plasma*light*(1.2+2.5*u_beat);
    if(d<.002) {hit=1.;tag=field.y;break;}
    dst+=clamp(d*.67,.012,.48);
    if(dst>65.) break;
  }
  vec3 col=vec3(.002,.005,.021);
  float fog=exp(-dst*.022);
  if(hit>.5) {
    vec2 normalD=vec2(.007,0.);
    vec3 n=normalize(vec3(
      distanceField(p+normalD.xyy).x-distanceField(p-normalD.xyy).x,
      distanceField(p+normalD.yxy).x-distanceField(p-normalD.yxy).x,
      distanceField(p+normalD.yyx).x-distanceField(p-normalD.yyx).x));
    float diffuse=max(.05,dot(n,normalize(vec3(-.5,.6,-.75))));
    float edge=pow(1.-abs(dot(n,rd)),2.8);
    vec3 material=palette(p.z*.06+atan(p.y,p.x)*.18+t*.05+tag*.15);
    col=mix(col,material*(.35+1.4*diffuse+2.2*edge+u_beat*.6),fog);
  }
  // Zarte volumetrische Nebelwolken und Stern-Partikel, ohne Texturzugriffe.
  float neb=clouds(ro+rd*8.+vec3(0.,0.,t*.2));
  vec3 backdrop=palette(uv.x*.22+uv.y*.16+t*.015+.25);
  col+=backdrop*(.018+.028*neb*neb)*(1.+treble);
  vec3 stars=floor(rd*225.);
  float sparkle=step(.9955,hash(stars))*pow(max(0.,sin(t*2.+hash(stars)*40.)),4.);
  col+=vec3(.5,.8,1.)*sparkle*.38*(1.-smoothstep(.3,1.7,length(uv)));
  col+=glow*2.8;
  // Cinematic vignette, HDR curve, tonemapping and light grain.
  col=1.-exp(-max(col,0.)*1.35);
  col*=1.-.3*smoothstep(.15,1.15,length(uv));
  col=pow(max(col,0.),vec3(.86));
  col+=hash(vec3(gl_FragCoord.xy,t))*.006;
  fragColor=vec4(clamp(col,0.,1.),1.);
}`;
