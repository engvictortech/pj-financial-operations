"""Testes de integridade e negócio. Usam bancos temporários; não alteram seu trabalho."""
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import operacoes as ops


class OperacoesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory()
        cls.base = Path(cls.workspace.name) / 'modelo.sqlite'
        with ops.database(cls.base) as db:
            cls.importacao = ops.importar(db, ator='Teste')

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dbpath = Path(self.tmp.name) / 'teste.sqlite'
        shutil.copy2(self.base, self.dbpath)
        self.ctx = ops.database(self.dbpath)
        self.db = self.ctx.__enter__()
        self.oid = self.db.execute("SELECT ocorrencia_id FROM ocorrencias WHERE referencia='R000001'").fetchone()[0]

    def tearDown(self):
        self.ctx.__exit__(None, None, None)
        self.tmp.cleanup()

    def analisar(self):
        ops.tratar(self.db, self.oid, 'atribuir', 'Teste', 1, responsavel='Analista Demo')
        return ops.tratar(self.db, self.oid, 'analisar', 'Teste', 2)

    def copiar_fontes(self):
        root = Path(self.tmp.name) / 'fontes'
        for name in ops.SOURCES:
            destino = root / name
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ops.ROOT / name, destino)
        return root

    def test_quantidades_e_estados_conhecidos(self):
        self.assertEqual(self.importacao['ocorrencias'], 2348)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM evidencias').fetchone()[0], 12000)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM eventos').fetchone()[0], 2348)
        caso = ops.obter(self.db, self.oid)
        self.assertEqual(caso['valor_impacto_centavos'], 766921)
        self.assertEqual(caso['motivo'], 'PARCIAL')
        self.assertEqual(caso['status'], 'ABERTA')

    def test_reimportacao_nao_duplica_nem_apaga_tratamento(self):
        self.analisar()
        result = ops.importar(self.db, ator='Outro operador')
        self.assertFalse(result['nova_importacao'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM ocorrencias').fetchone()[0], 2348)
        self.assertEqual(ops.obter(self.db, self.oid)['status'], 'EM_ANALISE')
        self.assertEqual(len(ops.historico(self.db, self.oid)), 3)

    def test_fluxo_resolucao_e_reabertura_preserva_financeiro(self):
        original = ops.detalhe(self.db, self.oid)['evidencia']
        self.analisar()
        ops.tratar(self.db, self.oid, 'observar', 'Teste', 3, nota='Pagamento localizado no arquivo de origem.')
        fechado = ops.tratar(self.db, self.oid, 'resolver', 'Teste', 4,
                             conclusao='TRATAMENTO_EXTERNO_DOCUMENTADO',
                             nota='Analise concluida e tratativa externa documentada para acompanhamento.')
        self.assertEqual(fechado['status'], 'RESOLVIDA')
        self.assertTrue(fechado['resolvida_em'])
        self.assertEqual(ops.detalhe(self.db, self.oid)['evidencia'], original)
        self.assertEqual(fechado['valor_impacto_centavos'], 766921)
        aberto = ops.tratar(self.db, self.oid, 'reabrir', 'Teste', 5,
                            nota='Novo documento recebido exige revisao da analise anterior.')
        self.assertEqual(aberto['status'], 'EM_ANALISE')
        self.assertIsNone(aberto['resolvida_em'])
        self.assertIsNone(aberto['conclusao'])
        self.assertEqual(len(ops.historico(self.db, self.oid)), 6)
        resolucao = ops.historico(self.db, self.oid)[4]
        self.assertEqual(resolucao['detalhes']['alteracoes']['conclusao']['depois'],
                         'TRATAMENTO_EXTERNO_DOCUMENTADO')

    def test_iniciar_analise_exige_responsavel(self):
        with self.assertRaises(ops.RegraError):
            ops.tratar(self.db, self.oid, 'analisar', 'Teste', 1)
        self.assertEqual(ops.obter(self.db, self.oid)['versao'], 1)

    def test_nao_resolve_direto_da_abertura(self):
        with self.assertRaises(ops.RegraError):
            ops.tratar(self.db, self.oid, 'resolver', 'Teste', 1,
                       conclusao='ANALISE_CONCLUIDA', nota='Analise da divergencia foi concluida e documentada.')

    def test_justificativa_curta_ou_conclusao_invalida(self):
        self.analisar()
        for conclusao, nota in [('ANALISE_CONCLUIDA', 'ok'), ('INVALIDA', 'Uma justificativa longa mas conclusao invalida.')]:
            with self.subTest(conclusao=conclusao), self.assertRaises(ops.RegraError):
                ops.tratar(self.db, self.oid, 'resolver', 'Teste', 3, conclusao=conclusao, nota=nota)
        self.assertEqual(ops.obter(self.db, self.oid)['versao'], 3)
        self.assertEqual(len(ops.historico(self.db, self.oid)), 3)

    def test_concorrencia_versao_antiga_nao_sobrescreve(self):
        with ops.database(self.dbpath) as outro:
            versao_antiga = ops.obter(outro, self.oid)['versao']
        ops.tratar(self.db, self.oid, 'atribuir', 'Teste', 1, responsavel='Analista Demo')
        with ops.database(self.dbpath) as outro, self.assertRaises(ops.RegraError):
            ops.tratar(outro, self.oid, 'atribuir', 'Outro', versao_antiga, responsavel='Outra pessoa')
        self.assertEqual(ops.obter(self.db, self.oid)['responsavel'], 'Analista Demo')

    def test_falha_no_evento_reverte_atualizacao(self):
        with patch('operacoes.evento', side_effect=sqlite3.IntegrityError('falha simulada')):
            with self.assertRaises(sqlite3.IntegrityError):
                ops.tratar(self.db, self.oid, 'atribuir', 'Teste', 1, responsavel='Analista Demo')
        self.assertIsNone(ops.obter(self.db, self.oid)['responsavel'])
        self.assertEqual(len(ops.historico(self.db, self.oid)), 1)

    def test_protecao_historico_e_evidencias(self):
        for query in ["UPDATE eventos SET ator='Adulterado'", 'DELETE FROM eventos',
                      "UPDATE evidencias SET dados_json='{}'", 'DELETE FROM evidencias',
                      "UPDATE lotes SET importado_por='Adulterado'"]:
            with self.subTest(query=query), self.assertRaises(sqlite3.IntegrityError):
                self.db.execute(query)

    def test_rastreabilidade_e_pagam_orfao(self):
        detalhe = ops.detalhe(self.db, self.oid)
        self.assertEqual(detalhe['evidencia']['pagamentos_origem'][0]['pagamento_id'], 'P000001_0')
        orfao = self.db.execute("SELECT * FROM ocorrencias WHERE motivo='PAGAMENTO_SEM_RECEBIVEL'").fetchone()
        self.assertIsNone(orfao['recebivel_id'])
        self.assertEqual(orfao['valor_impacto_centavos'], 12345)
        self.assertEqual(ops.historico(self.db, orfao['ocorrencia_id'])[0]['detalhes']['origem']['pagamento']['pagamento_id'], 'P_ORFAO')

    def test_divergencia_csv_bloqueia_lote(self):
        root = self.copiar_fontes()
        path = root / 'data/processed/conciliacao.csv'
        path.write_bytes(path.read_bytes().replace(b'766920', b'766919', 1))
        with self.assertRaises(ops.RegraError):
            ops.importar(self.db, root, ator='Teste')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM lotes').fetchone()[0], 1)

    def test_lote_incompleto_reverte_tudo(self):
        root = self.copiar_fontes()
        report = root / 'reports/validacao.json'
        report.write_text(report.read_text(encoding='utf-8') + '\n', encoding='utf-8')
        with patch('operacoes.evento', side_effect=sqlite3.IntegrityError('falha simulada')):
            with self.assertRaises(sqlite3.IntegrityError):
                ops.importar(self.db, root, ator='Teste')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM lotes').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM evidencias').fetchone()[0], 12000)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM ocorrencias').fetchone()[0], 2348)

    def test_limites_prioridade_e_filtros(self):
        self.assertEqual(ops.prioridade('PARCIAL', 1_000_000, 0), 'P1')
        self.assertEqual(ops.prioridade('PARCIAL', 99_999, 180), 'P1')
        self.assertEqual(ops.prioridade('PARCIAL', 100_000, 0), 'P2')
        self.assertEqual(ops.prioridade('PARCIAL', 99_999, 29), 'P3')
        self.assertEqual(len(ops.listar(self.db, limite=5, status='ABERTA')), 5)
        with self.assertRaises(ops.RegraError):
            ops.listar(self.db, limite=0)
        with self.assertRaises(ops.RegraError):
            ops.obter(self.db, -1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
