import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {pack,unpack,HEADER_SIZE} from '../../web/js/realtime/pcm.js';
import {createMockApi} from '../../web/js/realtime/mock_api.js';

const read = name => readFileSync(new URL('../../docs/realtime/examples/'+name,import.meta.url),'utf8');
const fixture = name => new Uint8Array(Buffer.from(read(name).trim(),'hex'));
test('PCM: Referenzbytes in beiden Richtungen, BigInt und Payload',()=>{
    assert.equal(HEADER_SIZE,32);
    for (const [name,stream,seq,start,rate,samples] of [
        ['pcm-python.hex',7,3,9007199254740993n,48000,[0.5,-0.25]],
        ['pcm-js.hex',8,4,9007199254740994n,44100,[-0.25,0.5]]]) {
        const header={protocol_version:1,stream_id:stream,epoch:2,seq,start_frame:start,nframes:256,channels:2,flags:0,sample_rate:rate};
        const payload=new Uint8Array(2048), view=new DataView(payload.buffer);
        for(let i=0;i<256;i++){view.setFloat32(i*8,samples[0],true);view.setFloat32(i*8+4,samples[1],true);}
        const block=fixture(name);
        assert.deepEqual(pack(header,payload),block);
        assert.deepEqual(unpack(block),{header:{...header,seek:false},payload});
        assert.deepEqual(pack(...Object.values(unpack(block))),block);
    }
});
test('PCM: ungültiger Kopf und Länge',()=>{
    const block=fixture('pcm-python.hex');
    for (const [offset,value] of [[0,2],[26,1],[25,9],[27,2]]) {
        const bad=block.slice();bad[offset]=value;
        assert.throws(()=>unpack(bad),RangeError);
    }
    for (const bad of [block.slice(0,31),block.slice(0,-1)]) assert.throws(()=>unpack(bad),RangeError);
});
test('UI-Mock: Capability, Sitzung, Jobs, Assets und Epoch',async()=>{
    const api=createMockApi(), prefix='/api/rt/v1/', examples=JSON.parse(read('json.json'));
    assert.deepEqual((await api('GET',prefix+'capabilities')).body,examples.schemas.capabilities.valid);
    assert.deepEqual((await api('GET',prefix+'gpu')).body,examples.schemas.telemetry.valid);
    const created=await api('POST',prefix+'sessions',{capability_id:'mock',sample_rate:48000});
    assert.equal(created.status,201);
    const path=prefix+'sessions/'+created.body.id;
    const asset=examples.schemas.asset.valid;
    assert.deepEqual((await api('GET',prefix+'assets/'+asset.id)).body,asset);
    const command=(name,seq,args={},epoch=0)=>api('POST',path+'/commands',{command:name,seq,args,epoch});
    const loaded=await command('load',0,{asset_id:asset.id});
    assert.equal(loaded.body.state,'ready');
    assert.equal((await api('GET',prefix+'jobs/'+loaded.body.job_id)).body.state,'ready');
    assert.equal((await command('play',1)).body.state,'playing');
    assert.equal((await command('seek',2,{source_frame:12})).body.epoch,1);
    assert.equal((await command('pause',3)).body.error,'stale_epoch');
    assert.equal((await api('POST',path+'/close',{})).body.state,'closed');
});
