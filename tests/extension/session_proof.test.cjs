const assert = require('node:assert/strict');
const { test } = require('node:test');
const { webcrypto, createHmac, createHash, generateKeyPairSync, sign } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const source = path.resolve(__dirname, '../../extension/src/session_proof.ts');
const fixture = new Module(source, module);
fixture._compile(ts.transpileModule(fs.readFileSync(source, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, source);
const { sessionProof, decode } = fixture.exports;
const id = '00000000-0000-4000-8000-000000000001';
const challenge = '00000000-0000-4000-8000-000000000002';
const nonce = Buffer.alloc(32, 1);
const secret = Buffer.alloc(32, 2);
// Independent server-side transcript, HMAC and signature implementation.
function serverTranscript(clientNonce) {
  return Buffer.concat([Buffer.from('lila-extension-v1'), Buffer.from(id), Buffer.from(challenge), nonce, clientNonce].map(part => {
    const length = Buffer.alloc(4); length.writeUInt32BE(part.length); return Buffer.concat([length, part]);
  }));
}
async function setup() {
  const { privateKey, publicKey } = generateKeyPairSync('ed25519');
  const publicBytes = publicKey.export({ format: 'der', type: 'spki' }).subarray(-32);
  const proof = await sessionProof(id, challenge, nonce.toString('base64url'), secret.toString('base64url'), publicBytes.toString('base64url'), webcrypto);
  const value = serverTranscript(Buffer.from(proof.payload.client_nonce, 'base64url'));
  const expected = createHmac('sha256', secret).update(value).digest();
  assert.equal(proof.payload.proof, expected.toString('base64url'));
  const digest = createHash('sha256').update(Buffer.concat([value, expected])).digest();
  return { proof, signature: sign(null, digest, privateKey).toString('base64url') };
}
test('client HMAC matches server transcript and verifies pinned server exactly once', async () => {
  const { proof, signature } = await setup();
  await proof.verify(signature);
  await assert.rejects(proof.verify(signature), /PROOF_ALREADY_CONSUMED/);
});
test('signature from another handshake cannot authenticate the client', async () => {
  const first = await setup(); const second = await setup();
  await assert.rejects(first.proof.verify(second.signature), /SERVER_IDENTITY_MISMATCH/);
  await assert.rejects(first.proof.verify(first.signature), /PROOF_ALREADY_CONSUMED/);
});
test('strict base64url rejects malformed, padded and wrong-sized key material', () => {
  for (const text of ['!', 'AA', secret.toString('base64'), secret.toString('base64url') + '=']) {
    assert.throws(() => decode(text, 32));
  }
});
