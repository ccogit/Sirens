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
  if (path.startsWith("sessions") && (!id(body.id) || !Number.isInteger(body.epoch) ||
      !["created","loading","ready","playing","paused","stopping","closed","error"].includes(body.state))) throw invalid();
  return body;
}
export function createRtApi({mock=false, fetcher=globalThis.fetch}={}) {
  const local = mock ? createMockApi() : null;
  async function request(method,path,body,signal) {
    let result;
    if (local) result = await local(method,prefix+path,body);
    else {
      const response = await fetcher(prefix+path,{method,signal,headers:body===undefined?{}:{"Content-Type":"application/json"},
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
  return {
    capabilities: signal => request("GET","capabilities",undefined,signal),
    gpu: signal => request("GET","gpu",undefined,signal),
    create: (capability_id,sample_rate=48000) => request("POST","sessions",{capability_id,sample_rate}),
    command: (session,command,args={}) => request("POST",sessionPath(session.id)+"/commands",
      {command,args,epoch:session.epoch,seq:session.seq===null?0:session.seq+1}),
    close: session => request("POST",sessionPath(session.id)+"/close",{}),
  };
}
// WP01 stellt nur einen synthetischen Asset-Bezeichner zur Verfügung.
export const MOCK_ASSET = "33333333333333333333333333333333";
