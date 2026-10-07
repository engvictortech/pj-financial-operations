/* Demonstração estática. Não é o servidor Python nem um banco compartilhado. */
'use strict';
(function (root) {
  const copy = value => JSON.parse(JSON.stringify(value));
  const fail = (code, message) => { throw Object.assign(new Error(message), {code}); };
  const text = (value, name, min = 1, max = 2000) => {
    if (typeof value !== 'string' || value.trim().length < min || value.trim().length > max)
      fail(422, `${name}: informe entre ${min} e ${max} caracteres.`);
    return value.trim();
  };
  function createDemo(source, clock = () => new Date().toISOString()) {
    let seed, cases, nextEvent;
    const ready = Promise.resolve(source).then(data => {
      if (data.schema !== 1 || !data.lote || !Array.isArray(data.casos))
        fail(503, 'Base de demonstração incompatível. Atualize a página.');
      seed = copy(data);
      reset();
    });
    function reset() {
      cases = new Map(seed.casos.map(item => [item.ocorrencia.ocorrencia_id, copy(item)]));
      nextEvent = Math.max(...seed.casos.flatMap(item => item.historico.map(e => e.evento_id))) + 1;
    }
    function find(id) {
      const item = cases.get(id);
      if (!item) fail(404, `Ocorrência ${id} não encontrada.`);
      return item;
    }
    function queue(params) {
      const lot = params.get('lote') || seed.lote.lote_id;
      if (lot !== seed.lote.lote_id) fail(404, 'Lote não encontrado.');
      const all = [...cases.values()].map(item => item.ocorrencia);
      let rows = all;
      const allowed = {status: ['ABERTA', 'EM_ANALISE', 'RESOLVIDA'], prioridade: ['P1', 'P2', 'P3'],
        motivo: ['PENDENTE', 'PARCIAL', 'A_MAIOR', 'LIQUIDADO_COM_ATRASO', 'PAGAMENTO_SEM_RECEBIVEL']};
      for (const [field, choices] of Object.entries(allowed)) {
        const value = params.get(field);
        if (value) {
          if (!choices.includes(value)) fail(400, `Filtro inválido: ${field}`);
          rows = rows.filter(row => row[field] === value);
        }
      }
      const owner = params.get('responsavel');
      if (owner) rows = rows.filter(row => owner === '--sem--' ? row.responsavel === null : row.responsavel === owner);
      const search = (params.get('busca') || '').trim().toLowerCase();
      if (search.length > 80) fail(400, 'Busca muito longa.');
      if (search) rows = rows.filter(row => [row.referencia, row.empresa_id, row.ocorrencia_id]
        .some(value => String(value ?? '').toLowerCase().includes(search)));
      const size = Number(params.get('tamanho') || 25);
      let page = Number(params.get('pagina') || 1);
      if (![10, 25, 50].includes(size) || !Number.isInteger(page) || page < 1 || page > 100000)
        fail(400, 'Paginação inválida.');
      const total = rows.length;
      const pages = Math.max(1, Math.ceil(total / size));
      page = Math.min(page, pages);
      rows.sort((a, b) => a.prioridade.localeCompare(b.prioridade)
        || b.valor_impacto_centavos - a.valor_impacto_centavos
        || b.idade_dias - a.idade_dias || a.ocorrencia_id - b.ocorrencia_id);
      const summary = {ABERTA: 0, EM_ANALISE: 0, RESOLVIDA: 0};
      all.forEach(row => summary[row.status]++);
      return {lote_id: lot, ocorrencias: rows.slice((page - 1) * size, page * size),
        total, pagina: page, paginas: pages, tamanho: size, resumo_lote: summary};
    }
    function action(id, payload) {
      if (!payload || typeof payload !== 'object' || Array.isArray(payload)) fail(400, 'Informe uma ação válida.');
      const actor = text(payload.ator, 'Ator', 1, 100);
      if (!Number.isInteger(payload.versao) || payload.versao < 1) fail(400, 'Informe uma versão inteira positiva.');
      const item = find(id), before = item.ocorrencia;
      if (before.versao !== payload.versao)
        fail(409, `Conflito de versão: atual=${before.versao}. Reabra o caso e revise.`);
      const changes = {}, details = {};
      switch (payload.acao) {
        case 'atribuir': {
          if (before.status === 'RESOLVIDA') fail(422, 'Reabra a ocorrência antes de alterar o responsável.');
          const owner = text(payload.responsavel, 'Responsável', 1, 100);
          if (owner === before.responsavel) fail(422, 'Responsável já atribuído; nenhuma mudança realizada.');
          changes.responsavel = owner;
          break;
        }
        case 'analisar':
          if (before.status !== 'ABERTA' || !before.responsavel)
            fail(422, 'Para analisar, o caso deve estar ABERTO e ter responsável.');
          changes.status = 'EM_ANALISE';
          break;
        case 'observar':
          if (before.status !== 'EM_ANALISE') fail(422, 'Observações de investigação exigem caso EM_ANALISE.');
          details.observacao = text(payload.texto, 'Observação', 5);
          break;
        case 'resolver':
          if (before.status !== 'EM_ANALISE') fail(422, 'O encerramento exige uma ocorrência EM_ANALISE.');
          if (!seed.conclusoes.includes(payload.conclusao)) fail(422, 'Conclusão inválida.');
          Object.assign(changes, {status: 'RESOLVIDA', conclusao: payload.conclusao,
            justificativa: text(payload.texto, 'Justificativa', 20)});
          break;
        case 'reabrir':
          if (before.status !== 'RESOLVIDA') fail(422, 'Somente ocorrências RESOLVIDAS podem ser reabertas.');
          details.motivo_reabertura = text(payload.texto, 'Motivo de reabertura', 20);
          Object.assign(changes, {status: 'EM_ANALISE', conclusao: null, justificativa: null, resolvida_em: null});
          break;
        default: fail(400, 'Ação inválida.');
      }
      const time = clock();
      if (payload.acao === 'resolver') changes.resolvida_em = time;
      details.alteracoes = Object.fromEntries(Object.entries(changes)
        .map(([field, after]) => [field, {antes: before[field], depois: after}]));
      // Todas as validações precedem a alteração. Evidências financeiras não são editadas.
      const updated = {...before, ...changes, versao: before.versao + 1, atualizada_em: time};
      const event = {evento_id: nextEvent++, ocorrencia_id: id, tipo: payload.acao.toUpperCase(),
        ator: actor, instante: time, versao: updated.versao, detalhes: details};
      item.ocorrencia = updated;
      item.historico.push(event);
      return updated;
    }
    async function request(path, body) {
      await ready;
      const url = new URL(path, 'https://demo.invalid');
      let result;
      if (url.pathname === '/api/contexto' && body === undefined) {
        result = {csrf_token: '', ator: 'Visitante', banco: 'simulação nesta aba', natureza: 'DADOS SINTETICOS',
          conclusoes: seed.conclusoes, versao_app: 'demo-1.0'};
      } else if (url.pathname === '/api/lotes' && body === undefined) result = [seed.lote];
      else if (url.pathname === '/api/fila' && body === undefined) result = queue(url.searchParams);
      else if (url.pathname === '/api/importar' && body !== undefined) {
        text(body.ator, 'Ator', 1, 100);
        result = {lote_id: seed.lote.lote_id, nova_importacao: false, ocorrencias: cases.size};
      } else {
        const match = url.pathname.match(/^\/api\/ocorrencias\/(\d+)(\/(acao|exportar))?$/);
        if (!match) fail(404, 'Recurso não encontrado.');
        const id = Number(match[1]);
        if (match[3] === 'acao' && body !== undefined) result = action(id, body);
        else if (body === undefined && match[3] !== 'acao') {
          result = {...copy(find(id)), lote: copy(seed.lote)};
          if (match[3] === 'exportar') Object.assign(result, {exportado_em_utc: clock(),
            natureza: 'DADOS SINTETICOS — SIMULACAO NO NAVEGADOR',
            ambiente: 'GitHub Pages; alterações efêmeras nesta aba; sem banco compartilhado'});
        } else fail(400, 'Requisição inválida.');
      }
      return copy(result);
    }
    return {request, reset: async () => {await ready; reset();}};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {createDemo};
  if (typeof window !== 'undefined') {
    let source;
    root.PJDemo = createDemo(Promise.resolve().then(async () => {
      try {
        const response = await fetch('./demo/dados.json');
        if (!response.ok) throw new Error('Base indisponível.');
        source = await response.json();
        return source;
      } catch {
        fail(503, 'Não foi possível carregar a demonstração. Confira a conexão e atualize a página.');
      }
    }));
  }
})(globalThis);
