import assert from "node:assert/strict";
import { test } from "node:test";
import { productionAnsicht } from "../web/js/production.js";

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.pauses = 0; }
  append(item) { this.children.push(item); }
  setAttribute() {}
  removeAttribute(name) { delete this[name]; }
  pause() { this.pauses++; }
  load() {}
}
const document = { createElement: tag => new Element(tag) };
const flatten = el => [el, ...el.children.flatMap(flatten)];
const button = (session, label) => flatten(session.el).find(n => n.tag === "button" && n.textContent === label);
const audio = session => flatten(session.el).find(n => n.tag === "audio");
const run = {status: "succeeded", validated: true, run_id: "mock", audio_url: "/mock.wav"};

test("mount is inert, standard path without Live", async () => {
  let calls = 0;
  const session = productionAnsicht({ document, api: {mode:"mock", create: async () => {calls++; return run;}} });
  assert.equal(calls, 0);
  assert.equal(audio(session).autoplay, false);
  await button(session, "Song erstellen").onclick();
  assert.equal(calls, 1);
  assert.equal(audio(session).src, "/mock.wav");
  assert.equal(button(session, "In Ableton öffnen").hidden, true);
  session.destroy();
  assert.equal(audio(session).src, undefined);
});

test("late response ignored on destroy", async () => {
  let resolve, signal;
  const session = productionAnsicht({document, api:{mode:"mock", create: (_, s) => {signal=s; return new Promise(r => {resolve=r;});}}});
  const pending = button(session,"Song erstellen").onclick();
  session.destroy();
  assert.equal(signal.aborted, true);
  resolve(run);
  await pending;
  assert.equal(audio(session).src, undefined);
});

test("optional bundle and validated return", async () => {
  let valid = false;
  const session = productionAnsicht({document, api:{
    mode:"mock", create:async()=>run, exportAbleton:async()=>({validated:true, mode:"import_bundle",export_id:"e"}),
    checkReturn:async()=>({validated:valid,export_id:"e"}),
    importAbleton:async()=>({...run,run_id:"returned",audio_url:"/return.wav"})
  }});
  await button(session,"Song erstellen").onclick();
  await button(session,"In Ableton öffnen").onclick();
  await button(session,"Ableton-Eingang prüfen").onclick();
  assert.equal(button(session,"Ableton-Fassung übernehmen").hidden,true);
  valid = true;
  await button(session,"Ableton-Eingang prüfen").onclick();
  assert.equal(button(session,"Ableton-Fassung übernehmen").hidden,false);
  await button(session,"Ableton-Fassung übernehmen").onclick();
  assert.equal(audio(session).src,"/return.wav");
  session.destroy();
});
