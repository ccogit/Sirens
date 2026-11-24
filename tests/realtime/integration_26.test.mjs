import test from "node:test";
import assert from "node:assert/strict";
import {createRtApi} from "../../web/js/realtime/api.js";
import {createSessionController} from "../../web/js/realtime/shell.js";

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
