'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createDemo} = require('../web/demo-engine.js');
const seed = JSON.parse(fs.readFileSync(path.join(__dirname, '../docs/demo/dados.json'), 'utf8'));
const make = () => createDemo(seed, () => '2026-10-07T16:00:00.000Z');
const detail = demo => demo.request('/api/ocorrencias/304');
const act = (demo, acao, versao, extra = {}) => demo.request('/api/ocorrencias/304/acao',
  {acao, versao, ator: 'Visitante', ...extra});
async function analyze(demo) {
  await act(demo, 'atribuir', 1, {responsavel: 'Analista'});
  await act(demo, 'analisar', 2);
}

test('volume, valores de referência, qualidade e ordem da fila', async () => {
  const demo = make(), q = await demo.request('/api/fila');
  assert.equal(q.total, 2348);
  assert.equal(q.ocorrencias[0].ocorrencia_id, 2324);
  assert.equal(q.paginas, 94);
  assert.deepEqual(q.resumo_lote, {ABERTA: 2348, EM_ANALISE: 0, RESOLVIDA: 0});
  const c = await detail(demo);
  assert.equal(c.ocorrencia.referencia, 'R001581');
  assert.equal(c.evidencia.conciliacao.valor_esperado_centavos, 1952634);
  assert.equal(c.evidencia.conciliacao.valor_pago_centavos, 976317);
  assert.equal(c.evidencia.conciliacao.saldo_aberto_centavos, 976317);
  assert.equal(c.evidencia.pagamentos_origem[0].pagamento_id, 'P001581_0');
  const [l] = await demo.request('/api/lotes');
  assert.equal(l.qualidade.duplicatas_tecnicas_removidas, 586);
  assert.equal(l.qualidade.linhas_fora_do_corte, 293);
});
test('filtros, busca literal, paginação limitada e resumo independente do filtro', async () => {
  const demo = make();
  assert.equal((await demo.request('/api/fila?motivo=PARCIAL')).total, 585);
  assert.equal((await demo.request('/api/fila?busca=R001581')).total, 1);
  assert.equal((await demo.request('/api/fila?busca=%25')).total, 0);
  assert.equal((await demo.request('/api/fila?busca=R001581&pagina=99')).pagina, 1);
  const q = await demo.request('/api/fila?status=RESOLVIDA');
  assert.equal(q.total, 0); assert.equal(q.resumo_lote.ABERTA, 2348);
  await assert.rejects(demo.request('/api/fila?tamanho=100'), e => e.code === 400);
  await assert.rejects(demo.request('/api/fila?status=INVALIDO'), e => e.code === 400);
  await assert.rejects(demo.request('/api/fila?lote=outro'), e => e.code === 404);
});
test('análise exige responsável e encerramento exige análise', async () => {
  const demo = make(), before = await detail(demo);
  await assert.rejects(act(demo, 'analisar', 1), e => e.code === 422);
  await assert.rejects(act(demo, 'resolver', 1, {conclusao: 'ANALISE_CONCLUIDA', texto: 'Texto suficientemente longo.'}), e => e.code === 422);
  assert.deepEqual(await detail(demo), before);
});
test('fluxo de tratamento preserva valores, origem e conclusão anterior no histórico', async () => {
  const demo = make(), original = (await detail(demo)).evidencia;
  await analyze(demo);
  await act(demo, 'observar', 3, {texto: 'Pagamento parcial conferido. Causa ainda a investigar.'});
  await act(demo, 'resolver', 4, {conclusao: 'ANALISE_CONCLUIDA', texto: 'Encerramento exclusivamente simulado para testar o fluxo.'});
  assert.equal((await detail(demo)).ocorrencia.status, 'RESOLVIDA');
  await act(demo, 'reabrir', 5, {texto: 'Reabertura simulada para conferir novamente os pagamentos.'});
  const after = await detail(demo);
  assert.equal(after.ocorrencia.status, 'EM_ANALISE');
  assert.equal(after.ocorrencia.conclusao, null);
  assert.equal(after.ocorrencia.resolvida_em, null);
  assert.equal(after.ocorrencia.valor_impacto_centavos, 976317);
  assert.deepEqual(after.evidencia, original);
  assert.equal(after.historico.length, 6);
  assert.equal(after.historico[4].detalhes.alteracoes.conclusao.depois, 'ANALISE_CONCLUIDA');
});
test('versão antiga não sobrescreve nem cria um evento', async () => {
  const demo = make();
  await act(demo, 'atribuir', 1, {responsavel: 'Analista'});
  const before = await detail(demo);
  await assert.rejects(act(demo, 'atribuir', 1, {responsavel: 'Outra pessoa'}), e => e.code === 409);
  assert.deepEqual(await detail(demo), before);
});
test('payload, ator, versão, conclusão e justificativa inválidos não alteram o caso', async () => {
  const demo = make(); await analyze(demo);
  const before = await detail(demo);
  for (const extra of [{texto: 'ok', conclusao: 'ANALISE_CONCLUIDA'},
    {texto: 'Uma justificativa longa para o teste.', conclusao: 'INVALIDA'},
    {texto: 'Uma justificativa longa para o teste.', conclusao: 'ANALISE_CONCLUIDA', ator: ''},
    {versao: true}, {versao: 3.5}]) {
    await assert.rejects(act(demo, 'resolver', 3, extra));
    assert.deepEqual(await detail(demo), before);
  }
});
test('atribuição repetida, observação fora de análise e alteração de caso encerrado bloqueadas', async () => {
  const demo = make();
  await assert.rejects(act(demo, 'observar', 1, {texto: 'Observação de teste.'}));
  await act(demo, 'atribuir', 1, {responsavel: 'Analista'});
  await assert.rejects(act(demo, 'atribuir', 2, {responsavel: 'Analista'}));
  await act(demo, 'analisar', 2);
  await act(demo, 'resolver', 3, {conclusao: 'ANALISE_CONCLUIDA', texto: 'Investigação encerrada apenas para testar as regras.'});
  await assert.rejects(act(demo, 'atribuir', 4, {responsavel: 'Outra pessoa'}));
  assert.equal((await detail(demo)).ocorrencia.versao, 4);
});
test('visitantes isolados, retorno defensivo e reinício preservam a base original', async () => {
  const a = make(), b = make();
  const sourceBefore = JSON.stringify(seed);
  const returned = await detail(a);
  returned.evidencia.conciliacao.saldo_aberto_centavos = 0;
  returned.historico[0].ator = 'Adulterado';
  assert.equal((await detail(a)).evidencia.conciliacao.saldo_aberto_centavos, 976317);
  await analyze(a);
  assert.equal((await detail(b)).ocorrencia.status, 'ABERTA');
  await a.reset();
  assert.equal((await detail(a)).ocorrencia.versao, 1);
  assert.equal(JSON.stringify(seed), sourceBefore);
});
test('conferir lote é idempotente e não apaga tratamento', async () => {
  const demo = make(); await analyze(demo);
  const before = await detail(demo);
  const result = await demo.request('/api/importar', {ator: 'Visitante'});
  assert.equal(result.nova_importacao, false);
  assert.equal(result.ocorrencias, 2348);
  assert.deepEqual(await detail(demo), before);
});
test('pagamento órfão e exportação identificam origem e ambiente de simulação', async () => {
  const demo = make();
  const q = await demo.request('/api/fila?motivo=PAGAMENTO_SEM_RECEBIVEL');
  assert.equal(q.total, 1);
  assert.equal(q.ocorrencias[0].valor_impacto_centavos, 12345);
  const c = await demo.request(`/api/ocorrencias/${q.ocorrencias[0].ocorrencia_id}`);
  assert.equal(c.evidencia, null);
  assert.equal(c.historico[0].detalhes.origem.pagamento.pagamento_id, 'P_ORFAO');
  const out = await demo.request('/api/ocorrencias/304/exportar');
  assert.match(out.natureza, /SIMULACAO NO NAVEGADOR/);
  assert.match(out.ambiente, /sem banco compartilhado/);
  await assert.rejects(demo.request('/api/ocorrencias/99999'), e => e.code === 404);
});
