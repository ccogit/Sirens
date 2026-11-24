import test from "node:test";
import assert from "node:assert/strict";
import {createRtApi} from "../../web/js/realtime/api.js";
import {createSessionController,createAudioSessionController} from "../../web/js/realtime/shell.js";

test("Mock-Sitzung: Laden, Abspielen, Gain-Pad, Bypass, Panic und Verlassen",async()=>{
  const mock=createRtApi({mock:true});
  const commands=[];
  let closes=0;
  const api={...mock,command:async(s,name,args)=>{
    const next=await mock.command(s,name,args);
    commands.push(name);
    return next;
  },close:async s=>{const next=await mock.close(s);closes++;return next;}};
  const controller=createSessionController(api);
  await controller.run(async command=>{
    await command("play");
    await command("set_param",{name:"gain",value:0.5});
    await command("bypass",{enabled:false});
  });
  assert.equal(controller.state,"playing");
  assert.deepEqual(commands,["load","play","set_param","bypass"]);
  await controller.reset();
  assert.equal(controller.state,"created");
  assert.equal(closes,1);
  await controller.destroy();
  assert.equal(closes,1);
  await controller.run(()=>assert.fail("Befehl nach Verlassen"));
});

test("Panic verwirft wartende Mock-Befehle und schließt die Sitzung",async()=>{
  const mock=createRtApi({mock:true});
  let resume, entered;
  const waiting=new Promise(resolve=>{entered=resolve;});
  const commands=[];
  const api={...mock,command:async(s,name,args)=>{
    commands.push(name);
    if(name==="play"){entered();await new Promise(resolve=>{resume=resolve;});}
    return mock.command(s,name,args);
  }};
  const c=createSessionController(api);
  const pending=c.run(async send=>{
    await send("play");
    await send("set_param",{name:"gain",value:1});
  });
  await waiting;
  const queued=c.run(()=>assert.fail("Wartender Befehl nach Panic"));
  const stopped=c.reset();
  resume();
  await Promise.all([pending,queued,stopped]);
  assert.deepEqual(commands,["load","play"]);
  assert.equal(c.state,"created");
  await c.destroy();
});

test("Panic während HTTP-Play startet keine lokale Audioausgabe",async()=>{
  const mock=createRtApi({mock:true});
  let resume, entered, plays=0, destroys=0, closes=0;
  const waiting=new Promise(resolve=>{entered=resolve;});
  const core={
    rate:48000,context:{createBuffer:(_channels,length)=>({length,getChannelData:()=>new Float32Array(length)})},
    frame:()=>0,param:()=>{},play:()=>{plays++;throw new Error("Spätes Play");},
    destroy:async()=>{destroys++;}
  };
  const api={...mock,asset:async id=>({id,nframes:256,sample_rate:48000}),
    dry:async()=>new ArrayBuffer(256*8),beatgrid:async()=>{throw new Error("kein Grid");},
    transport:async()=>{throw new Error("Dry-Fallback");},
    command:async(s,name,args)=>{
      if(name==="play"){entered();await new Promise(resolve=>{resume=resolve;});}
      return mock.command(s,name,args);
    },close:async s=>{closes++;return mock.close(s);}
  };
  const c=createAudioSessionController(api,()=>({path:"fixture"}),{openCore:async()=>core});
  const pending=c.run(send=>send("play"));
  await waiting;
  const stopped=c.reset();
  resume();
  await Promise.all([pending,stopped]);
  assert.equal(plays,0);
  assert.equal(destroys,1);
  assert.equal(closes,1);
  assert.equal(c.state,"created");
  await c.destroy();
});
