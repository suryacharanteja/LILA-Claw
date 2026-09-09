const assert = require('node:assert/strict');
const { test } = require('node:test');
const { webcrypto, generateKeyPairSync, createHmac, createHash, sign } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
function load(source) {
  const fixture = new Module(source, module);
  fixture.require = name => name.startsWith('.') ? load(path.resolve(path.dirname(source), name + '.ts')) : require(name);
  fixture._compile(ts.transpileModule(fs.readFileSync(source, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText, source);
  return fixture.exports;
}
const { ExtensionConnection } = load(path.resolve(__dirname, '../../extension/src/connection.ts'));
class Socket extends EventTarget {
  sent = []; closed = false;
  send(raw) { this.sent.push(JSON.parse(raw)); }
  close() { this.closed = true; }
  frame(type, payload) { this.dispatchEvent(new MessageEvent('message', { data: JSON.stringify({ type, payload }) })); }
}
async function setup() {
  const keys = generateKeyPairSync('ed25519');
  const credentialId = '00000000-0000-4000-8000-000000000001';
  const challenge = '00000000-0000-4000-8000-000000000002';
  const secret = Buffer.alloc(32, 2), nonce = Buffer.alloc(32, 1);
  const socket = new Socket();
  const client = new ExtensionConnection({ port: 43127, credentialId, credentialSecret: secret.toString('base64url'), pinnedIdentity: keys.publicKey.export({ format: 'der', type: 'spki' }).subarray(-32).toString('base64url') }, url => {
    assert.equal(url, 'wss://127.0.0.1:43127/extension/v1'); return socket;
  }, webcrypto);
  client.connect(); socket.dispatchEvent(new Event('open'));
  socket.frame('challenge', { challenge_id: challenge, nonce: nonce.toString('base64url') });
  await client.settled();
  const proof = socket.sent[1].payload;
  const value = Buffer.concat([Buffer.from('lila-extension-v1'), Buffer.from(credentialId), Buffer.from(challenge), nonce, Buffer.from(proof.client_nonce, 'base64url')].map(part => { const n = Buffer.alloc(4); n.writeUInt32BE(part.length); return Buffer.concat([n, part]); }));
  assert.equal(proof.proof, createHmac('sha256', secret).update(value).digest('base64url'));
  const signature = sign(null, createHash('sha256').update(Buffer.concat([value, Buffer.from(proof.proof, 'base64url')])).digest(), keys.privateKey).toString('base64url');
  return { socket, client, payload: { principal_id: credentialId, expires_at: new Date(Date.now() + 900000).toISOString(), signature } };
}
test('socket authenticates before reporting empty qualified capabilities', async () => {
  const { socket, client, payload } = await setup();
  socket.frame('authenticated', payload); await client.settled();
  assert.deepEqual(socket.sent[2], { type: 'capabilities', payload: { protocol_version: 1, tools: [], adapter_ids: [] } });
  socket.frame('capabilities_received', { accepted: true, execution_ready: false }); await client.settled();
  assert.deepEqual(client.status(), { connected: true, capabilitiesReported: true, executionReady: false });
});
test('forged server proof closes socket without reporting capabilities', async () => {
  const { socket, client, payload } = await setup();
  socket.frame('authenticated', { ...payload, signature: Buffer.alloc(64).toString('base64url') }); await client.settled();
  assert.equal(socket.closed, true); assert.equal(socket.sent.length, 2);
  assert.equal(client.status().connected, false);
});
test('reply from disconnected generation cannot revive readiness', async () => {
  const { socket, client, payload } = await setup();
  client.disconnect(); socket.frame('authenticated', payload); await client.settled();
  assert.equal(socket.sent.length, 2); assert.equal(client.status().connected, false);
});
