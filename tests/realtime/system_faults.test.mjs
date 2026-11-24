import test from "node:test";
import assert from "node:assert/strict";
import {AudioCore} from "../../web/js/realtime/audio_core.js";
import {RenderPath} from "../../web/js/realtime/worklet_processor.js";

test("Verbindungsabbruch: kein neuer Wet-Block, Dry bleibt erhalten",()=>{
    // Nachgestellter Socket; der echte Renderpfad erhält keine weiteren Blöcke.
    const original=globalThis.WebSocket;
    class Socket {
        constructor(){this.closed=false;}
        close(){this.closed=true;}
    }
    globalThis.WebSocket=Socket;
    try {
        const pushed=[];
        const core={socket:null,push:data=>pushed.push(data)};
        const socket=AudioCore.prototype.connect.call(core,"ws://127.0.0.1:12345/pcm","a".repeat(43));
        socket.onmessage({data:"erster Block"});
        assert.deepEqual(pushed,["erster Block"]);
        socket.close();
        const next=AudioCore.prototype.connect.call(core,"ws://127.0.0.1:12345/pcm","b".repeat(43));
        socket.onmessage({data:"veralteter Block"});
        assert.equal(pushed.length,1);
        assert.equal(core.socket,next);
        const p=new RenderPath(0,4);p.target=1;
        p.wet.write(0,0,new Float32Array(8).fill(.5));
        for(let i=0;i<4;i++)p.sample(.125,-.125);
        assert.equal(p.out[0],.5);
        for(let i=0;i<4;i++)p.sample(.125,-.125);
        assert.equal(p.out[0],.125);
        assert.equal(p.out[1],-.125);
        p.reset(1,100);
        assert.equal(p.wet.write(0,100,new Float32Array([.5,.5])),false);
    } finally {
        if(original===undefined)delete globalThis.WebSocket;
        else globalThis.WebSocket=original;
    }
});
