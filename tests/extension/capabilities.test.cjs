const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
// Compile only this known local source using the locked TypeScript dependency.
const source = path.resolve(__dirname, '../../extension/src/capabilities.ts');
const compiled = ts.transpileModule(fs.readFileSync(source, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const fixture = new Module(source, module);
fixture._compile(compiled, source);
const { CapabilityExchange, reportCapabilities } = fixture.exports;
const acknowledgement = { type: 'capabilities_received', payload: { accepted: true, execution_ready: false } };

test('reports only in a verified session and waits for acknowledgement', () => {
  const sent = [];
  const exchange = new CapabilityExchange(frame => sent.push(frame));
  assert.throws(() => exchange.report(0, [], []));
  const epoch = exchange.verifiedSession();
  exchange.report(epoch, ['inspect_context'], ['fixture-v1']);
  assert.deepEqual(sent, [{ type: 'capabilities', payload: reportCapabilities(['inspect_context'], ['fixture-v1']) }]);
  assert.equal(exchange.status().capabilitiesReported, false);
  assert.throws(() => exchange.report(epoch, [], []));
  exchange.acknowledge(epoch, acknowledgement);
  assert.deepEqual(exchange.status(), { capabilitiesReported: true, executionReady: false });
});

test('renewal and disconnect fence old acknowledgements', () => {
  const exchange = new CapabilityExchange(() => {});
  const old = exchange.verifiedSession();
  exchange.report(old, [], []);
  const current = exchange.verifiedSession();
  exchange.report(current, [], []);
  assert.throws(() => exchange.acknowledge(old, acknowledgement));
  exchange.acknowledge(current, acknowledgement);
  exchange.reset();
  assert.equal(exchange.status().capabilitiesReported, false);
  assert.throws(() => exchange.report(current, [], []));
});

test('capability acknowledgement cannot enable execution', () => {
  const exchange = new CapabilityExchange(() => {});
  const epoch = exchange.verifiedSession();
  exchange.report(epoch, [], []);
  assert.throws(() => exchange.acknowledge(epoch, { ...acknowledgement, payload: { accepted: true, execution_ready: true } }));
  assert.equal(exchange.status().executionReady, false);
});

test('failed send invalidates session rather than reporting success', () => {
  const exchange = new CapabilityExchange(() => { throw new Error('fixture disconnect'); });
  const epoch = exchange.verifiedSession();
  assert.throws(() => exchange.report(epoch, [], []));
  assert.throws(() => exchange.acknowledge(epoch, acknowledgement));
  assert.equal(exchange.status().capabilitiesReported, false);
});

test('allowlist, duplicates, bounds and adapter identifiers are enforced', () => {
  for (const [tools, adapters] of [
    [['Runtime.evaluate'], []], [['inspect_context', 'inspect_context'], []],
    [[], ['fixture', 'fixture']], [[], ['https://remote.example/code.js']],
    [[], ['x'.repeat(101)]], [[], Array.from({ length: 33 }, (_, i) => `fixture-${i}`)],
  ]) assert.throws(() => reportCapabilities(tools, adapters));
});
