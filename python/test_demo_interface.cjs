/* Integração dos scripts publicados com DOM simulado. Não é QA visual. */
'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
test('interface estática: carregar, filtrar, investigar, tratar, escapar texto, exportar e reiniciar', async () => {
  const html = fs.readFileSync(path.join(root, 'docs/index.html'), 'utf8');
  const elements = new Map();
  let downloaded = false, reloaded = false, blob;
  class Element {
    constructor(id) {this.id = id; this.value = ''; this.hidden = false; this.handlers = {};
      this.classList = {toggle(){}, add(){}, remove(){}};}
    set innerHTML(value) {
      this.markup = value;
      if (this.id === 'dialog-fields') {
        for (const id of ['action-name', 'action-text', 'action-conclusion']) elements.delete(id);
        for (const match of value.matchAll(/id="([^"]+)"/g)) {
          const e = new Element(match[1]); elements.set(match[1], e);
          if (e.id === 'action-conclusion') e.value = 'ANALISE_CONCLUIDA';
        }
      }
    }
    get innerHTML() {return this.markup || '';}
    addEventListener(type, fn) {(this.handlers[type] ||= []).push(fn);}
    setAttribute(){} removeAttribute(){} showModal(){this.open = true;} close(){this.open = false;}
    scrollIntoView(){} appendChild(){} remove(){} click(){downloaded = true;}
  }
  for (const m of html.matchAll(/id="([^"]+)"/g)) elements.set(m[1], new Element(m[1]));
  const sandbox = {console, Intl, URL, URLSearchParams, Blob, setTimeout, clearTimeout,
    document: {getElementById: id => elements.get(id) || null, querySelectorAll: () => [],
      querySelector: () => new Element('avatar'), createElement: () => new Element('anchor'), body: new Element('body')},
    location: {hash: '', pathname: '/pj-financial-operations/', reload(){reloaded = true;}},
    history: {replaceState(){}},
    fetch: async url => {
      assert.equal(url, './demo/dados.json', 'Não deve chamar uma API de servidor.');
      return {ok: true, json: async () => JSON.parse(fs.readFileSync(path.join(root, 'docs/demo/dados.json'), 'utf8'))};
    }};
  sandbox.window = sandbox;
  // A exportação usa um Blob real; o endereço temporário é simulado nesta verificação.
  sandbox.URL = class extends URL {static createObjectURL(value){blob = value; return 'blob:test';} static revokeObjectURL(){}};
  vm.createContext(sandbox);
  for (const script of ['demo-engine.js', 'app.js'])
    vm.runInContext(fs.readFileSync(path.join(root, 'docs/demo', script), 'utf8'), sandbox);
  const run = code => vm.runInContext(code, sandbox);
  const fire = async (id, event, value = {}) => {
    for (const handler of elements.get(id).handlers[event] || []) await handler(value);
  };
  for (let i = 0; i < 100 && !run('state.queue'); i++) await new Promise(r => setTimeout(r, 10));
  assert.equal(run('state.queue.total'), 2348);
  assert.equal(elements.get('actor-button').innerHTML.startsWith('Visitante'), true);
  await fire('demo-example', 'click');
  assert.equal(run('state.detail.ocorrencia.ocorrencia_id'), 304);
  assert.match(elements.get('inspector').innerHTML, /19\.526,34/);
  run("openAction('atribuir')"); elements.get('action-name').value = 'Analista Demo';
  await run('saveAction({preventDefault(){}})');
  run("openAction('analisar')"); await run('saveAction({preventDefault(){}})');
  run("openAction('observar')");
  const note = 'Pagamento parcial revisado: <img src=x onerror=alert(1)> é texto.';
  elements.get('action-text').value = note;
  await run('saveAction({preventDefault(){}})');
  assert.equal(run('state.detail.ocorrencia.versao'), 4);
  assert.match(elements.get('inspector').innerHTML, /&lt;img/);
  assert.doesNotMatch(elements.get('inspector').innerHTML, /<img/);
  assert.equal(run('state.detail.historico.length'), 4);
  run("openAction('resolver')");
  elements.get('action-text').value = 'Encerramento exclusivamente simulado, sem alterar a origem financeira.';
  await run('saveAction({preventDefault(){}})');
  assert.equal(run('state.detail.ocorrencia.status'), 'RESOLVIDA');
  assert.equal(run('state.detail.evidencia.conciliacao.saldo_aberto_centavos'), 976317);
  const exportLink = {dataset: {export: '304'}};
  await fire('inspector', 'click', {target: {closest: selector => selector === '[data-export]' ? exportLink : null}, preventDefault(){}});
  assert.equal(downloaded, true);
  const exported = JSON.parse(await blob.text());
  assert.equal(exported.ocorrencia.versao, 5);
  assert.match(exported.natureza, /SIMULACAO/);
  elements.get('search').value = 'R001581'; await run('loadQueue()');
  assert.equal(run('state.queue.total'), 1);
  elements.get('search').value = 'inexistente'; await run('loadQueue()');
  assert.equal(elements.get('empty-state').hidden, false);
  await fire('demo-reset', 'click'); assert.equal(reloaded, true);
});
