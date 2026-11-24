// PCM v1, bytegetreu; start_frame ist BigInt.
export const HEADER_SIZE = 32;
function check(h) {
    const limits = {protocol_version:[1,1], stream_id:[1,0xffffffff], epoch:[0,0xffffffff],
        seq:[0,0xffffffff], nframes:[256,2048], channels:[2,2], flags:[0,0], sample_rate:[8000,192000]};
    for (const [k,[lo,hi]] of Object.entries(limits))
        if (!Number.isInteger(h[k]) || h[k]<lo || h[k]>hi) throw new RangeError(k);
    if (typeof h.start_frame !== "bigint" || h.start_frame<0n ||
        h.start_frame+BigInt(h.nframes)>2n**64n) throw new RangeError("start_frame");
    return h;
}
export function pack(h,payload) {
    check(h);
    if (!(payload instanceof Uint8Array) || payload.byteLength!==h.nframes*8) throw new RangeError("payload");
    const out=new Uint8Array(HEADER_SIZE+payload.byteLength), v=new DataView(out.buffer);
    for (const [i,k] of ["protocol_version","stream_id","epoch","seq"].entries()) v.setUint32(i*4,h[k],true);
    v.setBigUint64(16,h.start_frame,true);
    v.setUint16(24,h.nframes,true); v.setUint8(26,h.channels); v.setUint8(27,h.flags);
    v.setUint32(28,h.sample_rate,true); out.set(payload,HEADER_SIZE); return out;
}
export function unpack(block) {
    if (!(block instanceof Uint8Array) || block.byteLength<HEADER_SIZE) throw new RangeError("header");
    const v=new DataView(block.buffer,block.byteOffset,block.byteLength);
    const h=check({protocol_version:v.getUint32(0,true),stream_id:v.getUint32(4,true),
        epoch:v.getUint32(8,true),seq:v.getUint32(12,true),start_frame:v.getBigUint64(16,true),
        nframes:v.getUint16(24,true),channels:v.getUint8(26),flags:v.getUint8(27),sample_rate:v.getUint32(28,true)});
    if (block.byteLength!==HEADER_SIZE+h.nframes*8) throw new RangeError("payload");
    return {header:h,payload:block.slice(HEADER_SIZE)};
}
