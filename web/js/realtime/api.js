import { createMockApi } from "./mock_api.js";

const prefix = "/api/rt/v1/";
const isObject = v => v !== null && typeof v === "object" && !Array.isArray(v);
const id = value => typeof value === "string" && /^[0-9a-f]{32}$/.test(value);
const invalid = () => Object.assign(new Error("Unlesbare API-Antwort"), {status:502});
function validate(path, body) {
  if (!isObject(body)) throw invalid();
  if (path === "capabilities" && (body.protocol_version !== 1 || !Array.isArray(body.capabilities) ||
      !body.capabilities.every(c => isObject(c) && typeof c.id === "string" && typeof c.available === "boolean" &&
        typeof c.mock === "boolean" && ["streaming","lookahead","offline"].includes(c.mode)))) throw invalid();
  if (path === "gpu" && typeof body.available !== "boolean") throw invalid();
  if (/^sessions(?:\/[a-f0-9]{32}(?:\/(?:commands|close))?)?$/.test(path) && (!id(body.id) || !Number.isInteger(body.epoch) ||
      !["created","loading","ready","playing","paused","stopping","closed","error"].includes(body.state))) throw invalid();
  return body;
}
export function createRtApi({mock=false, fetcher=globalThis.fetch}={}) {
  const local = mock ? createMockApi() : null;
  async function request(method,path,body,signal) {
    let result;
    if (local) result = await local(method,prefix+path,body);
    else {
      const response = await fetcher(prefix+path,{method,signal:signal??AbortSignal.timeout(15000),headers:body===undefined?{}:{"Content-Type":"application/json"},
        body:body===undefined?undefined:JSON.stringify(body)});
      let data;
      try { data = await response.json(); } catch { data = null; }
      result = {status:response.status,body:data};
    }
    if (result.status < 200 || result.status >= 300) throw Object.assign(
      new Error(result.body?.meldung || "HTTP " + result.status), {status:result.status,error:result.body?.error});
    return validate(path,result.body);
  }
  const sessionPath = session => { if (!id(session)) throw new Error("Ungültige Sitzungs-ID"); return "sessions/"+session; };
  async function binary(method,path,body) {
    const response=await fetcher(prefix+path,{method,body,
      headers:body===undefined?{}:{"Content-Type":"application/octet-stream"},
      signal:AbortSignal.timeout(5000)});
    if(!response.ok)throw Object.assign(new Error("RT-Übertragung abgelehnt"),{status:response.status});
    return method==="GET"?response.arrayBuffer():response.json();
  }
  return {
    capabilities: signal => request("GET","capabilities",undefined,signal),
    gpu: signal => request("GET","gpu",undefined,signal),
    create: (capability_id,sample_rate=48000) => request("POST","sessions",{capability_id,sample_rate}),
    command: (session,command,args={}) => request("POST",sessionPath(session.id)+"/commands",
      {command,args,epoch:session.epoch,seq:session.seq===null?0:session.seq+1}),
    close: session => request("POST",sessionPath(session.id)+"/close",{}),
    session: session => request("GET",sessionPath(session.id)),
    asset: aid => request("GET","assets/"+aid),
    resolve: pfad => request("POST","assets/resolve",{pfad}),
    beatgrid: aid => request("GET","assets/"+aid+"/beatgrid"),
    transport: session => request("POST",sessionPath(session.id)+"/transport",{}),
    dry: session => binary("GET",sessionPath(session.id)+"/dry"),
    render: (session,block) => request("POST",sessionPath(session.id)+"/render",block),
    record: (session,name,rate) => request("POST",sessionPath(session.id)+"/recordings",{name,sample_rate:rate}),
    recordBlock: (session,rid,start,bytes) => binary("PUT",sessionPath(session.id)+"/recordings/"+rid+"/blocks/"+start,bytes),
    recordClose: (session,rid) => request("POST",sessionPath(session.id)+"/recordings/"+rid+"/close",{}),
    exportSession: (session,data) => request("POST",sessionPath(session.id)+"/exports",data),
  };
}
// WP01 stellt nur einen synthetischen Asset-Bezeichner zur Verfügung.
export const MOCK_ASSET = "33333333333333333333333333333333";
