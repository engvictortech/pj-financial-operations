"""Gera a demonstração estática com um banco TEMPORÁRIO, nunca o banco do usuário.

Uso: python python/exportar_demo.py
Saída: docs/index.html e docs/demo/*. Base validada pelo motor original.
"""
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import app
import operacoes as ops

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs'


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'Interface mudou; revise a adaptação antes de exportar: {old[:65]}')
    return source.replace(old, new, 1)


def exportar(destino=DEST):
    destino = Path(destino)
    with tempfile.TemporaryDirectory(prefix='pj_demo_') as temporary:
        with ops.database(Path(temporary) / 'demo.sqlite') as db:
            result = ops.importar(db, ROOT, ator='Gerador da demonstração')
            lots = app.lots(db)
            cases = []
            for row in db.execute('SELECT ocorrencia_id FROM ocorrencias ORDER BY ocorrencia_id'):
                cases.append(ops.detalhe(db, row[0]))
    if result['ocorrencias'] != 2348 or len(cases) != 2348:
        raise ValueError('Volume de casos diferente da base documentada. Revise a demonstração.')
    data = {'schema': 1, 'gerado_em_utc': datetime.now(timezone.utc).isoformat(),
            'natureza': 'DADOS SINTETICOS', 'lote': lots[0], 'conclusoes': list(ops.CONCLUSOES),
            'casos': cases}

    html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
    html = replace_once(html, '<title>PJ Financial Operations · Ocorrências</title>',
                        '<title>PJ Financial Operations · Demonstração interativa</title>\n'
                        '  <meta name="description" content="Explore 2.348 ocorrências financeiras simuladas: conciliação, pagamentos de origem e histórico de investigação. Projeto de Victor Crispim.">')
    html = replace_once(html, 'href="/static/app.css"', 'href="./demo/app.css"')
    html = replace_once(html, '<script src="/static/app.js" defer></script>',
                        '<link rel="stylesheet" href="./demo/demo.css">\n'
                        '  <script src="./demo/demo-engine.js" defer></script>\n'
                        '  <script src="./demo/app.js" defer></script>')
    html = replace_once(html, '<body>', '<body>\n  <a class="skip-link" href="#main">Pular para o conteúdo</a>')
    html = replace_once(html, 'Ambiente local', 'Demonstração online')
    html = replace_once(html, 'Operações · v2.0', 'Python + SQL · portfólio')
    html = replace_once(html, '<main>', '''<main id="main">
      <section class="demo-intro" aria-labelledby="demo-title">
        <div class="eyebrow">PORTFÓLIO · VICTOR CRISPIM</div>
        <h2>Uma diferença financeira exige uma investigação.</h2>
        <p>Explore uma fila com <strong>2.348 ocorrências</strong> geradas a partir de <strong>12.000 recebíveis de 300 empresas fictícias</strong>. Confira a origem, atribua um responsável e registre sua análise.</p>
        <div class="demo-tools">
          <button class="button primary" id="demo-example" disabled>Explorar um pagamento parcial →</button>
          <a class="button secondary" href="https://github.com/engvictortech/pj-financial-operations" target="_blank" rel="noopener noreferrer">Ver código e documentação ↗</a>
          <button class="text-button" id="demo-reset" disabled>Reiniciar demonstração</button>
        </div>
        <details><summary>O que observar neste caso?</summary><ol>
          <li>Na ocorrência #304, compare o esperado de R$ 19.526,34 com o pagamento de R$ 9.763,17: a liquidação corresponde a 50% do valor.</li>
          <li>Confira o evento P001581_0 e a data de 28/03/2025. Um pagamento na data prevista pode deixar saldo em aberto.</li>
          <li>Atribua um responsável, inicie a análise e registre uma observação com evidência e próximo passo. A causa permanece a investigar.</li>
          <li>Exporte o JSON. Se experimentar encerrar e reabrir, confira que o saldo financeiro de R$ 9.763,17 permanece preservado.</li>
        </ol></details>
        <p class="demo-limit">Dados sintéticos · simulação independente no navegador. Alterações ficam somente nesta aba e são descartadas ao recarregar. A versão Python com SQLite e testes está no repositório.</p>
      </section>''')
    html = replace_once(html, 'Importar base do projeto</button>', 'Conferir lote carregado</button>')
    html = replace_once(html, 'Banco operacional local', 'Simulação nesta aba')
    html = replace_once(html, 'SIMULAÇÃO</span>', 'DADOS SINTÉTICOS</span>')
    js = (ROOT / 'web/app.js').read_text(encoding='utf-8')
    js = replace_once(js, 'async function api(path, body) {',
                      'async function api(path, body) {\n  return PJDemo.request(path, body);\n}\n\nasync function unusedLocalApi(path, body) {')
    # Não embarque a função HTTP local inutilizada na demonstração.
    start = js.index('async function unusedLocalApi(')
    end = js.index('\nfunction notice(', start)
    js = js[:start] + js[end:]
    js = replace_once(js, "  try { localStorage.setItem('pj-operations-actor', actor); } catch { /* Memória local opcional. */ }", '')
    js = replace_once(js, "    try { stored = localStorage.getItem('pj-operations-actor'); } catch { /* Opcional. */ }", '')
    js = replace_once(js, "    $('db-label').textContent = 'Banco: ' + context.banco;",
                      "    $('db-label').textContent = 'Simulação nesta aba';")
    js = replace_once(js, 'href="/api/ocorrencias/${c.ocorrencia_id}/exportar" download',
                      'href="#" data-export="${c.ocorrencia_id}"')
    js = replace_once(js, "    await loadQueue();\n    const match = location.hash.match", "    await loadQueue();\n    $('demo-example').disabled = false;\n    $('demo-reset').disabled = false;\n    const match = location.hash.match")
    js = replace_once(js, 'Esta base já foi importada. Ocorrências e histórico existentes foram preservados.',
                      'Base simulada já carregada. Suas alterações nesta aba foram preservadas.')
    js += '''
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
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2) + '\\n'], {type: 'application/json'}));
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = 'ocorrencia_demo_' + id + '.json';
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {notice(error.message, true);}
});
'''
    files = {'index.html': html, '.nojekyll': '', 'demo/app.js': js,
             'demo/app.css': (ROOT / 'web/app.css').read_text(encoding='utf-8'),
             'demo/demo.css': (ROOT / 'web/demo.css').read_text(encoding='utf-8'),
             'demo/demo-engine.js': (ROOT / 'web/demo-engine.js').read_text(encoding='utf-8'),
             'demo/dados.json': json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n'}
    for relative, content in files.items():
        path = destino / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8', newline='\n')
    return {'destino': str(destino), 'ocorrencias': len(cases), 'lote_id': lots[0]['lote_id'],
            'arquivos': list(files), 'banco_operacional_do_usuario': 'NAO ACESSADO'}


if __name__ == '__main__':
    print(json.dumps(exportar(), ensure_ascii=False, indent=2))
