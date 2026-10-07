'use strict';
const $ = id => document.getElementById(id);
const state = {csrf: '', actor: 'Victor', lots: [], lot: '', status: '', page: 1, detail: null,
  view: 'fila', queue: null, request: 0, detailRequest: 0, action: null, actionVersion: null, saving: false};
const labels = {ABERTA: 'Aberta', EM_ANALISE: 'Em análise', RESOLVIDA: 'Encerrada',
  PENDENTE: 'Pendente', PARCIAL: 'Pagamento parcial', A_MAIOR: 'Recebido a maior',
  LIQUIDADO_COM_ATRASO: 'Liquidado com atraso', PAGAMENTO_SEM_RECEBIVEL: 'Pagamento sem vínculo',
  CRIADA: 'Ocorrência criada', ATRIBUIR: 'Responsável atribuído', ANALISAR: 'Análise iniciada',
  OBSERVAR: 'Observação registrada', RESOLVER: 'Investigação encerrada', REABRIR: 'Investigação reaberta',
  ANALISE_CONCLUIDA: 'Análise concluída', SEM_DIVERGENCIA_APOS_REVISAO: 'Sem divergência após revisão',
  TRATAMENTO_EXTERNO_DOCUMENTADO: 'Tratamento externo documentado'};
const money = value => new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(Number(value) / 100);
const number = value => new Intl.NumberFormat('pt-BR').format(value);
const date = value => value ? new Intl.DateTimeFormat('pt-BR').format(new Date(value.length === 10 ? value + 'T12:00:00' : value)) : '—';
const timestamp = value => value ? new Intl.DateTimeFormat('pt-BR', {dateStyle: 'short', timeStyle: 'short'}).format(new Date(value)) : '—';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

async function api(path, body) {
  return PJDemo.request(path, body);
}


function notice(text, error = false) {
  $('notice').textContent = text;
  $('notice').classList.toggle('error', error);
  $('notice').hidden = false;
}

function statusPill(status) {
  const style = status === 'EM_ANALISE' ? 'review' : status === 'RESOLVIDA' ? 'closed' : '';
  const dot = status === 'EM_ANALISE' ? 'blue' : status === 'RESOLVIDA' ? 'green' : 'gray';
  return `<span class="status-pill ${style}"><i class="dot ${dot}"></i>${esc(labels[status] || status)}</span>`;
}

function setActor(actor) {
  state.actor = actor;
  $('actor-button').innerHTML = `${esc(actor)} <span>⌄</span>`;
  document.querySelector('.operator-avatar').textContent = actor[0].toUpperCase();

}

async function loadLots(keep = true) {
  state.lots = await api('/api/lotes');
  if (!keep || !state.lots.some(l => l.lote_id === state.lot)) state.lot = state.lots[0]?.lote_id || '';
  $('lot-select').innerHTML = state.lots.length ? state.lots.map(l => `<option value="${esc(l.lote_id)}">${date(l.corte)} · ${esc(l.lote_id.slice(0, 10))}</option>`).join('') : '<option value="">Nenhum lote importado</option>';
  $('lot-select').value = state.lot;
  $('lot-select').disabled = !state.lots.length;
  $('cutoff-label').textContent = state.lots.length ? 'Corte ' + date(state.lots.find(l => l.lote_id === state.lot)?.corte) : 'Importe a base para começar';
  renderLots();
}

function query() {
  const owner = $('owner-filter').value;
  return new URLSearchParams({lote: state.lot, status: state.status, prioridade: $('priority-filter').value,
    motivo: $('reason-filter').value, responsavel: owner === '--me--' ? state.actor : owner,
    busca: $('search').value.trim(), pagina: state.page, tamanho: 25});
}

async function loadQueue() {
  const request = ++state.request;
  $('queue-body').setAttribute('aria-busy', 'true');
  try {
    const result = await api('/api/fila?' + query());
    if (request !== state.request) return;
    state.queue = result;
    state.page = result.pagina;
    const sum = result.resumo_lote;
    $('count-all').textContent = number(sum.ABERTA + sum.EM_ANALISE + sum.RESOLVIDA);
    $('count-open').textContent = number(sum.ABERTA);
    $('count-review').textContent = number(sum.EM_ANALISE);
    $('count-closed').textContent = number(sum.RESOLVIDA);
    $('result-count').textContent = `${number(result.total)} ocorrência${result.total === 1 ? '' : 's'} encontrada${result.total === 1 ? '' : 's'}`;
    $('empty-state').hidden = result.total !== 0;
    $('queue-body').innerHTML = result.ocorrencias.map(c => `<tr data-case="${c.ocorrencia_id}" class="${state.detail?.ocorrencia.ocorrencia_id === c.ocorrencia_id ? 'selected' : ''}">
      <td><button class="case-link" data-open="${c.ocorrencia_id}" aria-label="Investigar ocorrência ${c.ocorrencia_id}">#${c.ocorrencia_id}<span class="row-sub">${esc(c.referencia)} · ${esc(c.empresa_id || 'Sem vínculo')}</span></button></td>
      <td><span class="reason-tag">${esc(labels[c.motivo])}</span></td>
      <td><span class="priority-tag ${c.prioridade.toLowerCase()}">${esc(c.prioridade)}</span></td>
      <td class="numeric">${money(c.valor_impacto_centavos)}</td><td class="numeric">${number(c.idade_dias)} d</td>
      <td>${statusPill(c.status)}<span class="row-sub">${esc(c.responsavel || 'Sem responsável')}</span></td></tr>`).join('');
    $('page-label').textContent = result.total ? `${number((result.pagina - 1) * result.tamanho + 1)}–${number(Math.min(result.pagina * result.tamanho, result.total))} de ${number(result.total)} · página ${result.pagina}/${result.paginas}` : '0 ocorrências';
    $('prev-page').disabled = result.pagina <= 1;
    $('next-page').disabled = result.pagina >= result.paginas;
  } catch (error) { if (request === state.request) notice(error.message, true); }
  finally { if (request === state.request) $('queue-body').removeAttribute('aria-busy'); }
}

async function openCase(id, updateHash = true) {
  const request = ++state.detailRequest;
  const data = await api('/api/ocorrencias/' + id);
  if (request !== state.detailRequest) return;
  state.detail = data;
  if (data.ocorrencia.lote_id !== state.lot) {
    state.lot = data.ocorrencia.lote_id;
    state.page = 1;
    $('lot-select').value = state.lot;
    $('cutoff-label').textContent = 'Corte ' + date(data.lote.corte);
    await loadQueue();
  }
  if (updateHash) history.replaceState(null, '', '#ocorrencia-' + id);
  renderDetail();
  document.querySelectorAll('[data-case]').forEach(row => row.classList.toggle('selected', Number(row.dataset.case) === id));
}

function closeCase() {
  state.detailRequest++;
  state.detail = null;
  $('inspector').hidden = true;
  document.body.classList.remove('has-case');
  history.replaceState(null, '', location.pathname);
  document.querySelectorAll('[data-case]').forEach(row => row.classList.remove('selected'));
}

function contextItem(label, value) { return `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`; }

function renderDetail() {
  const {ocorrencia: c, evidencia: e, historico: events, lote} = state.detail;
  const r = e?.conciliacao;
  const actor = c.responsavel || 'Sem responsável';
  let actions = `<button class="button secondary" data-action="atribuir">${c.responsavel ? 'Alterar responsável' : 'Atribuir responsável'}</button>`;
  if (c.status === 'ABERTA') actions += `<button class="button primary" data-action="analisar" ${c.responsavel ? '' : 'disabled'}>Iniciar análise</button>`;
  if (c.status === 'EM_ANALISE') actions += '<button class="button primary" data-action="observar">Registrar observação</button><button class="button secondary" data-action="resolver">Encerrar investigação</button>';
  if (c.status === 'RESOLVIDA') actions = '<button class="button secondary" data-action="reabrir">Reabrir investigação</button>';
  const amountLabel = c.motivo === 'A_MAIOR' ? 'EXCESSO RECEBIDO' : c.motivo === 'LIQUIDADO_COM_ATRASO' ? 'SALDO RESIDUAL' : c.motivo === 'PAGAMENTO_SEM_RECEBIVEL' ? 'PAGAMENTO SEM VÍNCULO' : 'SALDO EM ABERTO NO CORTE';
  const note = c.motivo === 'LIQUIDADO_COM_ATRASO' ? 'O recebível foi liquidado integralmente. Esta ocorrência investiga a pontualidade, com saldo residual zero.' : c.motivo === 'PAGAMENTO_SEM_RECEBIVEL' ? 'Evento de pagamento sem vínculo com um recebível conhecido. O valor está separado dos totais conciliados.' : 'Valores preservados da conciliação. Encerrar a investigação não altera o saldo desta origem.';
  let payments = '<div class="evidence-note">Nenhum pagamento vinculado encontrado nos arquivos de origem deste lote.</div>';
  if (e?.pagamentos_origem?.length) {
    const seen = new Set();
    payments = '<table class="payments-table"><thead><tr><th>Evento / data</th><th class="numeric">Valor</th><th>Consideração</th></tr></thead><tbody>' + e.pagamentos_origem.map(p => {
      const future = p.data_liquidacao > lote.corte;
      const duplicate = seen.has(p.pagamento_id);
      seen.add(p.pagamento_id);
      const flag = future ? 'Após o corte' : duplicate ? 'Duplicata técnica' : 'Evento único';
      return `<tr><td>${esc(p.pagamento_id)}<span class="row-sub">${date(p.data_liquidacao)}</span></td><td class="numeric">${money(p.valor_pago_centavos)}</td><td class="payment-flags">${flag}</td></tr>`;
    }).join('') + '</tbody></table>';
  } else if (!e) {
    const p = events.find(ev => ev.tipo === 'CRIADA')?.detalhes.origem.pagamento;
    if (p) payments = `<div class="evidence-note">Evento ${esc(p.pagamento_id)} · ${date(p.data_liquidacao)}<br>${money(p.valor_pago_centavos)} · Referência informada: ${esc(p.recebivel_id)}</div>`;
  }
  const timeline = [...events].reverse().map(ev => {
    const changes = ev.detalhes.alteracoes || {};
    const detail = ev.detalhes.observacao || ev.detalhes.motivo_reabertura || changes.justificativa?.depois || (changes.responsavel ? `Responsável: ${changes.responsavel.depois}` : '');
    return `<li><div class="timeline-title">${esc(labels[ev.tipo] || ev.tipo)}<span>v${ev.versao}</span></div><div class="timeline-meta">${esc(ev.ator)} · ${timestamp(ev.instante)}</div>${detail ? `<p class="timeline-text">${esc(detail)}</p>` : ''}</li>`;
  }).join('');
  $('inspector').innerHTML = `<div class="inspector-head"><div><div class="eyebrow">INVESTIGAÇÃO</div><h2>Ocorrência #${c.ocorrencia_id}</h2><p>${esc(c.referencia)} · ${esc(c.empresa_id || 'Referência sem vínculo')}</p></div><button class="icon-button" id="close-case" aria-label="Fechar investigação">×</button></div>
    <div class="inspector-body"><div class="case-flags">${statusPill(c.status)}<span>${esc(c.prioridade)} · versão ${c.versao}</span></div>
    <div class="financial-box"><div class="eyebrow">${amountLabel}</div><div class="amount">${money(c.valor_impacto_centavos)}</div>${r ? `<div class="financial-split"><div><span>Esperado</span><strong>${money(r.valor_esperado_centavos)}</strong></div><div><span>Recebido até o corte</span><strong>${money(r.valor_pago_centavos)}</strong></div></div>` : ''}</div>
    <dl class="case-context">${contextItem('Motivo financeiro', labels[c.motivo])}${contextItem('Responsável', actor)}${contextItem('Adquirente', r?.adquirente || '—')}${contextItem('Liquidação prevista', date(r?.data_prevista))}${contextItem(c.motivo === 'LIQUIDADO_COM_ATRASO' ? 'Atraso de liquidação' : 'Idade no corte', number(c.idade_dias) + ' dias')}${contextItem('Corte do lote', date(lote.corte))}</dl>
    <div class="section-title">Tratamento operacional<span>v${c.versao}</span></div><div class="treatment-actions">${actions}</div>
    ${c.status === 'RESOLVIDA' ? `<div class="case-outcome"><strong>${esc(labels[c.conclusao])}</strong><br>${esc(c.justificativa)}</div>` : ''}
    <div class="evidence-note">${note}</div><div class="section-title">Pagamentos de origem<span>${e?.pagamentos_origem?.length ?? 1} linha(s)</span></div>${payments}
    <div class="section-title">Histórico do tratamento<span>${events.length} eventos</span></div><ol class="timeline">${timeline}</ol>
    <a class="export-link" href="#" data-export="${c.ocorrencia_id}">↓ Exportar evidências e histórico (JSON)</a></div>`;
  $('inspector').hidden = false;
  document.body.classList.add('has-case');
}

function renderLots() {
  $('lots-view').innerHTML = state.lots.length ? state.lots.map(l => {
    const q = l.qualidade;
    return `<article class="lot-card"><h2>Origem com corte em ${date(l.corte)}</h2><p>Importado por ${esc(l.importado_por)} em ${timestamp(l.importado_em)} · regra ${esc(l.regra_versao)}</p><div class="lot-id">${esc(l.lote_id)}</div>
      <div class="quality-grid"><div class="quality-item"><strong>${number(q.duplicatas_tecnicas_removidas || 0)}</strong><span>Duplicatas técnicas removidas<br>Não somadas como novos pagamentos</span></div><div class="quality-item"><strong>${number(q.linhas_fora_do_corte || 0)}</strong><span>Linhas posteriores ao corte<br>Excluídas da conciliação</span></div><div class="quality-item"><strong>${number(q.pagamentos_sem_recebivel || 0)}</strong><span>Pagamentos sem recebível<br>Separados dos totais conciliados</span></div><div class="quality-item"><strong>${money(q.valor_orfao_centavos || 0)}</strong><span>Valor sem vínculo<br>Exige investigação da referência</span></div></div>
      <div class="section-title">Arquivos de origem<span>Identificação SHA-256</span></div><div class="source-list">${Object.entries(l.manifesto).map(([file, hash]) => `<div class="source-row"><span>${esc(file)}</span><code title="${esc(hash)}">${esc(hash.slice(0, 24))}…</code></div>`).join('')}</div></article>`;
  }).join('') : '<div class="empty-state"><h2>Nenhum lote importado</h2><p>Use “Importar base do projeto” para validar e carregar os dados simulados.</p></div>';
}

function setView(view) {
  state.view = view;
  $('queue-view').hidden = view !== 'fila';
  $('lots-view').hidden = view !== 'lotes';
  $('page-title').textContent = view === 'fila' ? 'Fila de investigação' : 'Lotes e qualidade';
  $('page-subtitle').textContent = view === 'fila' ? 'Confira a origem de cada diferença e documente o tratamento.' : 'Confira os controles aplicados e os arquivos que sustentam a análise.';
  $('breadcrumb-current').textContent = view === 'fila' ? 'Ocorrências' : 'Lotes e qualidade';
  document.querySelectorAll('[data-view]').forEach(b => {b.classList.toggle('active', b.dataset.view === view); if (b.dataset.view === view) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');});
}

function openAction(action) {
  state.action = action;
  state.actionVersion = state.detail?.ocorrencia.versao ?? null;
  $('dialog-error').hidden = true;
  $('review-version').hidden = true;
  const caseId = state.detail?.ocorrencia.ocorrencia_id;
  $('dialog-caption').textContent = action === 'ator' ? 'IDENTIFICAÇÃO LOCAL' : 'OCORRÊNCIA #' + caseId;
  const descriptions = {
    atribuir: ['Atribuir responsável', 'Defina quem acompanha esta investigação. A atribuição ficará registrada no histórico.'],
    analisar: ['Iniciar análise', 'O caso passará para Em análise. Os valores da conciliação serão preservados.'],
    observar: ['Registrar observação', 'Descreva a evidência conferida, sua interpretação e o próximo ponto a investigar.'],
    resolver: ['Encerrar investigação', 'Registre a conclusão da análise. Encerrar não significa quitação: o saldo financeiro desta origem permanece inalterado.'],
    reabrir: ['Reabrir investigação', 'Documente o motivo da revisão. A conclusão anterior permanecerá no histórico.'],
    ator: ['Identificação do analista', 'Nome registrado nas ações desta demonstração local. Esta identificação é informada pelo usuário; não representa autenticação.']};
  const [title, description] = descriptions[action];
  $('dialog-title').textContent = title;
  $('dialog-description').textContent = description;
  let fields = '';
  if (action === 'ator' || action === 'atribuir') fields = `<label for="action-name">${action === 'ator' ? 'Seu nome' : 'Responsável'}<input id="action-name" required maxlength="100" value="${esc(action === 'ator' ? state.actor : state.detail.ocorrencia.responsavel || state.actor)}" autocomplete="off"></label>`;
  if (action === 'resolver') fields += `<label for="action-conclusion">Conclusão<select id="action-conclusion" required><option value="ANALISE_CONCLUIDA">Análise concluída</option><option value="SEM_DIVERGENCIA_APOS_REVISAO">Sem divergência após revisão</option><option value="TRATAMENTO_EXTERNO_DOCUMENTADO">Tratamento externo documentado</option></select></label>`;
  if (['observar', 'resolver', 'reabrir'].includes(action)) fields += `<label for="action-text">${action === 'observar' ? 'Observação' : 'Justificativa'}<textarea id="action-text" required minlength="${action === 'observar' ? 5 : 20}" maxlength="2000" placeholder="Registre fatos verificados e o contexto do tratamento."></textarea></label><span class="hint">Mínimo de ${action === 'observar' ? 5 : 20} caracteres. A informação será preservada no histórico.</span>`;
  $('dialog-fields').innerHTML = fields;
  $('dialog-version').textContent = action === 'ator' ? 'Uso local' : 'Versão lida: ' + state.actionVersion;
  $('dialog-submit').textContent = action === 'ator' ? 'Salvar identificação' : 'Confirmar ação';
  $('dialog-submit').disabled = false;
  $('action-dialog').showModal();
}

async function saveAction(event) {
  event.preventDefault();
  if (state.saving) return;
  const action = state.action;
  if (action === 'ator') {
    const actor = $('action-name').value.trim();
    if (!actor) return;
    setActor(actor);
    $('action-dialog').close();
    if ($('owner-filter').value === '--me--') await loadQueue();
    notice('Identificação local atualizada.');
    return;
  }
  const oid = state.detail.ocorrencia.ocorrencia_id;
  const data = {acao: action, ator: state.actor, versao: state.actionVersion};
  if ($('action-name')) data.responsavel = $('action-name').value.trim();
  if ($('action-text')) data.texto = $('action-text').value.trim();
  if ($('action-conclusion')) data.conclusao = $('action-conclusion').value;
  state.saving = true;
  let saved = null;
  $('dialog-submit').disabled = true;
  $('dialog-error').hidden = true;
  try {
    saved = await api('/api/ocorrencias/' + oid + '/acao', data);
    $('action-dialog').close();
    await openCase(oid);
    await loadQueue();
    notice(`Ação registrada na ocorrência #${oid} · versão ${saved.versao}. Valores financeiros preservados.`);
  } catch (error) {
    if (saved) {
      notice(`Ação gravada na versão ${saved.versao}, mas a atualização da tela falhou. Clique em Atualizar para conferir o estado atual.`, true);
      return;
    }
    $('dialog-error').textContent = error.message;
    $('dialog-error').hidden = false;
    if (error.code === 409) {
      try { await openCase(oid); $('review-version').hidden = false; }
      catch (reloadError) { $('dialog-error').textContent += ' ' + reloadError.message; }
    }
  } finally { state.saving = false; $('dialog-submit').disabled = false; }
}

async function refresh() {
  try {
    await loadLots();
    await loadQueue();
    if (state.detail) await openCase(state.detail.ocorrencia.ocorrencia_id);
  } catch (error) { notice(error.message, true); }
}

async function bootstrap() {
  try {
    const context = await api('/api/contexto');
    state.csrf = context.csrf_token;
    let stored;

    setActor(stored?.trim().slice(0, 100) || context.ator);
    $('db-label').textContent = 'Simulação nesta aba';
    await loadLots(false);
    await loadQueue();
    $('demo-example').disabled = false;
    $('demo-reset').disabled = false;
    const match = location.hash.match(/^#ocorrencia-(\d+)$/);
    if (match) await openCase(Number(match[1]));
  } catch (error) { notice(error.message, true); $('result-count').textContent = 'Conexão não disponível'; }
}

document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
document.querySelectorAll('[data-status]').forEach(b => b.addEventListener('click', () => {
  state.status = b.dataset.status; state.page = 1;
  document.querySelectorAll('[data-status]').forEach(tab => {tab.classList.toggle('active', tab === b); tab.setAttribute('aria-pressed', tab === b);});
  loadQueue();
}));
let searchTimer;
$('search').addEventListener('input', () => {clearTimeout(searchTimer); searchTimer = setTimeout(() => {state.page = 1; loadQueue();}, 250);});
['priority-filter', 'reason-filter', 'owner-filter'].forEach(id => $(id).addEventListener('change', () => {state.page = 1; loadQueue();}));
$('lot-select').addEventListener('change', () => {state.lot = $('lot-select').value; state.page = 1; closeCase(); $('cutoff-label').textContent = 'Corte ' + date(state.lots.find(l => l.lote_id === state.lot)?.corte); loadQueue();});
$('clear-filters').addEventListener('click', () => {$('search').value = ''; ['priority-filter','reason-filter','owner-filter'].forEach(id => $(id).value = ''); state.page = 1; loadQueue();});
$('prev-page').addEventListener('click', () => {state.page--; loadQueue();});
$('next-page').addEventListener('click', () => {state.page++; loadQueue();});
$('queue-body').addEventListener('click', event => {
  const button = event.target.closest('[data-open]');
  if (button) openCase(Number(button.dataset.open)).catch(error => notice(error.message, true));
});
$('inspector').addEventListener('click', event => {
  if (event.target.closest('#close-case')) closeCase();
  const button = event.target.closest('[data-action]');
  if (button && !button.disabled) openAction(button.dataset.action);
});
$('actor-button').addEventListener('click', () => openAction('ator'));
$('refresh-button').addEventListener('click', refresh);
$('import-button').addEventListener('click', async () => {
  const button = $('import-button'); button.disabled = true;
  try {
    const result = await api('/api/importar', {ator: state.actor});
    await loadLots(false);
    if (state.detail && state.detail.ocorrencia.lote_id !== state.lot) closeCase();
    await loadQueue();
    notice(result.nova_importacao ? `${number(result.ocorrencias)} ocorrências importadas e validadas.` : 'Base simulada já carregada. Suas alterações nesta aba foram preservadas.');
  } catch (error) { notice(error.message, true); }
  finally { button.disabled = false; }
});
$('action-form').addEventListener('submit', saveAction);
['dialog-close', 'dialog-cancel'].forEach(id => $(id).addEventListener('click', () => {if (!state.saving) $('action-dialog').close();}));
$('action-dialog').addEventListener('cancel', event => {if (state.saving) event.preventDefault();});
$('review-version').addEventListener('click', () => {state.actionVersion = state.detail.ocorrencia.versao; $('dialog-version').textContent = 'Versão revisada: ' + state.actionVersion; $('review-version').hidden = true; $('dialog-error').textContent = 'Versão atual selecionada. Confira sua justificativa antes de confirmar.';});
bootstrap();

$('demo-example').addEventListener('click', async () => {
  setView('fila');
  try {await openCase(304); $('inspector').scrollIntoView({behavior: 'auto', block: 'start'});}
  catch (error) {notice(error.message, true);}
});
$('demo-reset').addEventListener('click', () => {history.replaceState(null, '', location.pathname); location.reload();});
$('inspector').addEventListener('click', async event => {
  const link = event.target.closest('[data-export]');
  if (!link) return;
  event.preventDefault();
  try {
    const id = Number(link.dataset.export);
    const data = await api('/api/ocorrencias/' + id + '/exportar');
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2) + '\n'], {type: 'application/json'}));
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = 'ocorrencia_demo_' + id + '.json';
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {notice(error.message, true);}
});
