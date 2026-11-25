import test from "node:test";
import assert from "node:assert/strict";
import {createAudioSessionController} from "../../web/js/realtime/shell.js";
import {createRtApi} from "../../web/js/realtime/api.js";

function fixture(){
  const mock=createRtApi({mock:true});
  let renders=0,destroys=0,closes=0,statusChanges=0,release,entered;
  const rendering=new Promise(resolve=>{entered=resolve;});
  const callbacks=new Set();
  const timerHost={
    setInterval(fn){callbacks.add(fn);return fn;},
    clearInterval(fn){callbacks.delete(fn);}
  };
  const core={
    rate:48000,clock:{epoch:1},transports:[{lookahead:16384}],
    context:{createBuffer:(_channels,length)=>({length,getChannelData:()=>new Float32Array(length)})},
    frame:()=>0,param:()=>{},
    play:(_buffers,{frame})=>({epoch:1,frame}),
    connect:()=>({addEventListener:(name,fn)=>{if(name==="open")queueMicrotask(fn);}}),
    destroy:async()=>{destroys++;}
  };
  const api={...mock,
    asset:async id=>({id,nframes:192000,sample_rate:48000}),
    dry:async()=>new ArrayBuffer(192000*8),
    beatgrid:async()=>{throw new Error("kein Grid");},
    transport:async()=>({port:12345,token:"test"}),
    render:async()=>{
      renders++;
      await new Promise(resolve=>{release=resolve;entered();});
      throw new Error("Verspätete Renderantwort");
    },
    close:async s=>{closes++;return mock.close(s);}
  };
  const controller=createAudioSessionController(api,()=>({path:"fixture"}),{
    openCore:async()=>core,timerHost,onStatus:()=>{statusChanges++;}
  });
  return {controller,rendering,callbacks,finish:()=>release(),
    counts:()=>({renders,destroys,closes,statusChanges})};
}

for(const action of ["reset","destroy"]){
  test("Pumpe: "+action+" löscht Intervall sofort und wartet laufenden Renderauftrag ab",{timeout:3000},async()=>{
    const f=fixture(), c=f.controller;
    await c.run(send=>send("play"));
    await f.rendering;
    assert.equal(f.callbacks.size,1);
    const oldTick=[...f.callbacks][0];
    let completed=false;
    const stopping=c[action]().then(()=>{completed=true;});
    try{
      assert.equal(f.callbacks.size,0);
      oldTick(); // Bereits zur Ausführung vorgemerkter Timer darf nichts mehr starten.
      await Promise.resolve();
      assert.equal(completed,false);
      assert.equal(f.counts().renders,1);
    }finally{
      f.finish();
      await stopping;
      await c.destroy();
    }
    oldTick();
    await Promise.resolve();
    assert.deepEqual(f.counts(),{renders:1,destroys:1,closes:1,statusChanges:0});
    assert.equal(c.state,"created");
    assert.equal(c.detail.fault,null);
    assert.equal(f.callbacks.size,0);
  });
}
