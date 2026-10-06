"""Verificações HTTP do aplicativo local. Não alteram o banco do usuário."""
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app
import operacoes as ops


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.TemporaryDirectory()
        cls.template = Path(cls.root.name) / 'base.sqlite'
        with ops.database(cls.template) as db:
            ops.importar(db, ator='Teste')
            ops.tratar(db, 2324, 'atribuir', 'Victor', 1, responsavel='Victor')
            ops.tratar(db, 2324, 'analisar', 'Victor', 2)
            ops.tratar(db, 2324, 'observar', 'Victor', 3, nota='Origem conferida; causa da pendencia permanece em investigacao.')

    @classmethod
    def tearDownClass(cls):
        cls.root.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'teste.sqlite'
        shutil.copy2(self.template, self.db)
        self.server = app.create_server(self.db, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.token = self.server.csrf_token

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, payload=None, headers=None, raw=None):
        data = json.dumps(payload).encode() if payload is not None else raw
        base_headers = {'Content-Type': 'application/json', 'X-PJ-Token': self.token} if data is not None else {}
        base_headers.update(headers or {})
        req = Request(self.url + path, data=data, headers=base_headers)
        try:
            with urlopen(req, timeout=5) as response:
                content = response.read()
                mime = response.headers.get('Content-Type', '')
                return response.status, json.loads(content) if mime.startswith('application/json') else content, dict(response.headers)
        except HTTPError as exc:
            return exc.code, json.loads(exc.read()), dict(exc.headers)

    def test_interface_assets_e_csp(self):
        code, body, headers = self.request('/')
        self.assertEqual(code, 200)
        self.assertIn(b'Fila de investiga', body)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        for path in ['/static/app.js', '/static/app.css']:
            self.assertEqual(self.request(path)[0], 200)
        self.assertEqual(self.request('/static/../python/operacoes.py')[0], 404)

    def test_fila_estado_preservado_e_lotes(self):
        _, queue, _ = self.request('/api/fila')
        self.assertEqual(queue['total'], 2348)
        self.assertEqual(queue['resumo_lote']['EM_ANALISE'], 1)
        self.assertEqual(queue['ocorrencias'][0]['ocorrencia_id'], 2324)
        self.assertEqual(queue['ocorrencias'][0]['versao'], 4)
        _, lotes, _ = self.request('/api/lotes')
        self.assertEqual(lotes[0]['qualidade']['duplicatas_tecnicas_removidas'], 586)

    def test_filtros_pagina_e_busca_literal(self):
        _, filtered, _ = self.request('/api/fila?status=EM_ANALISE&responsavel=Victor&busca=R011880')
        self.assertEqual(filtered['total'], 1)
        _, p1, _ = self.request('/api/fila?pagina=1&tamanho=10')
        _, p2, _ = self.request('/api/fila?pagina=2&tamanho=10')
        self.assertEqual(len(p1['ocorrencias']), 10)
        self.assertTrue({r['ocorrencia_id'] for r in p1['ocorrencias']}.isdisjoint(r['ocorrencia_id'] for r in p2['ocorrencias']))
        _, escaped, _ = self.request('/api/fila?busca=%25')
        self.assertEqual(escaped['total'], 0)
        self.assertEqual(self.request('/api/fila?status=INVALIDO')[0], 400)
        self.assertEqual(self.request('/api/fila?pagina=0')[0], 400)
        self.assertEqual(self.request('/api/fila?lote=desconhecido')[0], 404)

    def test_exportacao_e_evidencia(self):
        _, case, _ = self.request('/api/ocorrencias/2324')
        self.assertEqual(case['ocorrencia']['status'], 'EM_ANALISE')
        self.assertEqual(case['evidencia']['conciliacao']['saldo_aberto_centavos'], 1978522)
        self.assertEqual(len(case['historico']), 4)
        _, export, headers = self.request('/api/ocorrencias/2324/exportar')
        self.assertIn('filename="ocorrencia_2324.json"', headers['Content-Disposition'])
        self.assertIn('SINTETICOS', export['natureza'])

    def test_acao_resolve_sem_alterar_financeiro(self):
        payload = {'acao': 'resolver', 'ator': 'Victor', 'versao': 4, 'conclusao': 'ANALISE_CONCLUIDA',
                   'texto': 'Conferencia encerrada nesta demonstracao; saldo financeiro mantido para acompanhamento.'}
        code, result, _ = self.request('/api/ocorrencias/2324/acao', payload)
        self.assertEqual(code, 200)
        self.assertEqual(result['versao'], 5)
        _, case, _ = self.request('/api/ocorrencias/2324')
        self.assertEqual(case['evidencia']['conciliacao']['saldo_aberto_centavos'], 1978522)
        self.assertEqual(case['ocorrencia']['status'], 'RESOLVIDA')
        self.assertEqual(len(case['historico']), 5)

    def test_conflito_409_sem_sobrescrever(self):
        code, _, _ = self.request('/api/ocorrencias/2324/acao',
                                  {'acao': 'observar', 'ator': 'Victor', 'versao': 3, 'texto': 'Tentativa com versao antiga.'})
        self.assertEqual(code, 409)
        _, case, _ = self.request('/api/ocorrencias/2324')
        self.assertEqual(case['ocorrencia']['versao'], 4)

    def test_token_origem_e_host_externos_bloqueados(self):
        payload = {'acao': 'observar', 'ator': 'Victor', 'versao': 4, 'texto': 'Texto nao deve ser gravado.'}
        for headers in [{'X-PJ-Token': ''}, {'Origin': 'https://externo.example'}, {'Host': 'externo.example'}]:
            with self.subTest(headers=headers):
                self.assertEqual(self.request('/api/ocorrencias/2324/acao', payload, headers)[0], 403)
        self.assertEqual(self.request('/api/fila', headers={'Host': 'externo.example'})[0], 403)

    def test_payload_invalido_e_regra_de_justificativa(self):
        self.assertEqual(self.request('/api/ocorrencias/2324/acao', raw=b'{')[0], 400)
        self.assertEqual(self.request('/api/ocorrencias/2324/acao', raw=b'[]')[0], 400)
        self.assertEqual(self.request('/api/ocorrencias/2324/acao', {'ator': 'Victor', 'versao': True, 'acao': 'analisar'})[0], 400)
        self.assertEqual(self.request('/api/ocorrencias/2324/acao', {'ator': 'Victor', 'versao': 4, 'acao': 'resolver', 'texto': 'ok', 'conclusao': 'ANALISE_CONCLUIDA'})[0], 422)

    def test_importacao_http_idempotente(self):
        code, result, _ = self.request('/api/importar', {'ator': 'Victor'})
        self.assertEqual(code, 200)
        self.assertFalse(result['nova_importacao'])
        _, case, _ = self.request('/api/ocorrencias/2324')
        self.assertEqual(case['ocorrencia']['versao'], 4)

    def test_servidor_novo_nao_importa_automaticamente(self):
        with ops.database(Path(self.tmp.name) / 'vazio.sqlite') as db:
            self.assertEqual(app.queue(db, {})['total'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
