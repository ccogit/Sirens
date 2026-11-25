import test from "node:test";
import assert from "node:assert/strict";
import {RenderPath} from "../../web/js/realtime/worklet_processor.js";
test("WP30: vorbereitete Ringgeneration hält Wet-Mix; Altpfad hat Lücken",()=>{
 for(const prepared of [false,true]){
  const p=new RenderPath(0,1,8192),length=192000,block=new Float32Array(4096).fill(.25);
  p.target=1;p.reset(1,0);
  for(let epoch=1;epoch<=101;epoch++){
   const start=(epoch-1)*length;
   for(let i=0;i<length;i++){
    if(i%2048===0 && (prepared||epoch===1||i>=2400)){
     if(!(prepared&&epoch>1&&i<4096))p.write(epoch,start+i,block.subarray(0,2*Math.min(2048,length-i)));
    }
    if(i===length-4096 && prepared && epoch<101){
     p.prepare(epoch+1,start+length);
     assert.ok(p.write(epoch+1,start+length,block));
     assert.ok(p.write(epoch+1,start+length+2048,block));
    }
    p.sample(0,0);
   }
   if(epoch<101)p.switchLoop(epoch+1,start+length);
  }
  if(prepared)assert.equal(p.unexpectedUnderruns,0);
  else assert.ok(p.unexpectedUnderruns>0);
 }
});
test("WP30: Seek und alte Epoch",()=>{
 const p=new RenderPath(0,1,4);
 p.target=1;p.reset(2,10,14);p.sample(0,0);
 assert.equal(p.expectedUnderruns,1);
 assert.equal(p.write(1,11,new Float32Array(2)),false);
 assert.equal(p.write(2,11,new Float32Array(2)),true);
 p.sample(0,0);p.sample(0,0);
 assert.equal(p.unexpectedUnderruns,1);
});
