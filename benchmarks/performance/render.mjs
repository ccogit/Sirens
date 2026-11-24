// Nur synthetische Fixtures. Ausgabe ausschließlich in einem neuen Verzeichnis außerhalb des Repos.
import {mkdir,writeFile,realpath} from "node:fs/promises";
import {resolve,dirname,relative,isAbsolute,sep} from "node:path";
import {fileURLToPath} from "node:url";
import {demos,rate} from "../../tests/realtime/performance_fixtures.mjs";
const root=await realpath(fileURLToPath(new URL("../../",import.meta.url)));
if(process.argv.length!==3)throw new Error("Aufruf: node benchmarks/performance/render.mjs <neues externes Verzeichnis>");
const requested=resolve(process.argv[2]),parent=await realpath(dirname(requested)),dest=resolve(parent,requested.split(/[\\/]/).at(-1));
const rel=relative(root,dest);
if(rel===""||(!(rel===".."||rel.startsWith(".."+sep))&&!isAbsolute(rel)))throw new Error("Ausgabe muss außerhalb des Repositories liegen");
await mkdir(dest);
const results=[];
for(const [name,render] of Object.entries(demos)){
 const r=render(),n=r.track.length,b=Buffer.alloc(44+n*2);
 b.write("RIFF");b.writeUInt32LE(b.length-8,4);b.write("WAVEfmt ",8);
 b.writeUInt32LE(16,16);b.writeUInt16LE(1,20);b.writeUInt16LE(1,22);b.writeUInt32LE(rate,24);
 b.writeUInt32LE(rate*2,28);b.writeUInt16LE(2,32);b.writeUInt16LE(16,34);b.write("data",36);b.writeUInt32LE(n*2,40);
 let peak=0;
 for(let i=0;i<n;i++){peak=Math.max(peak,Math.abs(r.track[i]));b.writeInt16LE(Math.round(r.track[i]*32767),44+i*2);}
 await writeFile(resolve(dest,name+".wav"),b,{flag:"wx"});
 results.push({name,frames:n,peak,warnings:r.warnings,events:r.events});
}
await writeFile(resolve(dest,"render.json"),JSON.stringify({rate,results},null,2)+"\n",{flag:"wx"});
console.log(dest);
