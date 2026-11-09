// Runs the real JavaScript from workflow.json's Code nodes with mocked n8n inputs.
// Usage: node tests/code_nodes.test.js
const assert = require('assert');
const wf = require('../workflow.json');
const code = (name) => wf.nodes.find((n) => n.name === name).parameters.jsCode;

function runNode(js, inputJson, refs = {}) {
  const $input = { first: () => ({ json: inputJson }) };
  const $ = (name) => ({ first: () => ({ json: refs[name] }) });
  return new Function('$input', '$', js)($input, $);
}

let passed = 0;
const test = (name, fn) => { fn(); passed++; console.log('✓', name); };

const normalize = code('Normalize Lead');
const parse = code('Parse AI Result');

test('normalizes webhook body', () => {
  const [out] = runNode(normalize, { body: { name: ' Ravi ', phone: '+91 98765-43210', email: 'RAVI@X.COM', message: ' Need 150Ah battery price ' } });
  assert.equal(out.json.name, 'Ravi');
  assert.equal(out.json.phone, '+919876543210');
  assert.equal(out.json.email, 'ravi@x.com');
  assert.equal(out.json.message, 'Need 150Ah battery price');
  assert.equal(out.json.source, 'website');
});

test('rejects lead without message', () => {
  assert.throws(() => runNode(normalize, { body: { phone: '999' } }), /no message/);
});

test('rejects lead without contact', () => {
  assert.throws(() => runNode(normalize, { body: { message: 'hi' } }), /phone or email/);
});

const lead = { name: 'Ravi', phone: '+919876543210', message: 'Need battery today' };

test('parses valid Gemini JSON', () => {
  const ai = { candidates: [{ content: { parts: [{ text: JSON.stringify({ intent: 'price_enquiry', priority: 'hot', product: '150Ah battery', reply: 'Hi Ravi! 150Ah tubular is Rs.12,800.' }) }] } }] };
  const [out] = runNode(parse, ai, { 'Normalize Lead': lead });
  assert.equal(out.json.priority, 'hot');
  assert.equal(out.json.product, '150Ah battery');
  assert.equal(out.json.ai_ok, true);
  assert.equal(out.json.phone, lead.phone);
});

test('handles ```json fenced output', () => {
  const ai = { candidates: [{ content: { parts: [{ text: '```json\n{"priority":"cold","reply":"Thanks!"}\n```' }] } }] };
  const [out] = runNode(parse, ai, { 'Normalize Lead': lead });
  assert.equal(out.json.priority, 'cold');
});

test('falls back safely when AI fails', () => {
  const [out] = runNode(parse, { error: 'quota exceeded' }, { 'Normalize Lead': lead });
  assert.equal(out.json.priority, 'warm');
  assert.equal(out.json.ai_ok, false);
  assert.match(out.json.reply, /Hi Ravi/);
});

test('rejects invalid priority from AI', () => {
  const ai = { candidates: [{ content: { parts: [{ text: '{"priority":"URGENT!!","reply":"ok"}' }] } }] };
  const [out] = runNode(parse, ai, { 'Normalize Lead': lead });
  assert.equal(out.json.priority, 'warm');
});

test('every connection points to an existing node', () => {
  const names = new Set(wf.nodes.map((n) => n.name));
  for (const [from, c] of Object.entries(wf.connections)) {
    assert(names.has(from), from);
    c.main.flat().forEach((t) => assert(names.has(t.node), t.node));
  }
});

console.log(`\n${passed} tests passed`);
