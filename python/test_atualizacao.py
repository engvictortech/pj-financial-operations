"""Atualizacao segura em uma copia temporaria, sem tocar no banco do usuario."""
import importlib.util
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import operacoes as ops

spec = importlib.util.spec_from_file_location('atualizador', ops.ROOT / 'atualizar_interface.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class AtualizacaoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory()
        cls.template = Path(cls.base.name) / 'banco.sqlite'
        with ops.database(cls.template) as db:
            ops.importar(db, ator='Victor')
            ops.tratar(db, 2324, 'atribuir', 'Victor', 1, responsavel='Victor')
            ops.tratar(db, 2324, 'analisar', 'Victor', 2)
            ops.tratar(db, 2324, 'observar', 'Victor', 3, nota='Origem conferida na base simulada; causa ainda a investigar.')

    @classmethod
    def tearDownClass(cls):
        cls.base.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.target = Path(self.temp.name) / 'projeto atual com espacos'
        self.target.mkdir()
        for rel in updater.COMPATIBLE:
            path = self.target / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ops.ROOT / rel, path)
        self.db = self.target / 'data/processed/operacoes.sqlite'
        self.db.parent.mkdir(parents=True)
        shutil.copy2(self.template, self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_preserva_banco_e_historico_e_cria_backup(self):
        original = self.db.read_bytes()
        result = updater.update(self.target)
        self.assertEqual(self.db.read_bytes(), original)
        with ops.database(Path(result['backup']) / 'operacoes.sqlite') as db:
            case = ops.detalhe(db, 2324)
            self.assertEqual(case['ocorrencia']['versao'], 4)
            self.assertEqual(len(case['historico']), 4)
            self.assertEqual(case['ocorrencia']['responsavel'], 'Victor')
            self.assertEqual(case['evidencia']['conciliacao']['saldo_aberto_centavos'], 1978522)
        for rel in updater.FILES:
            self.assertEqual((self.target / rel).read_bytes(), (ops.ROOT / rel).read_bytes())

    def test_motor_modificado_bloqueia_antes_de_copiar(self):
        (self.target / 'python/operacoes.py').write_text('modificado')
        with self.assertRaisesRegex(ValueError, 'incompativel'):
            updater.update(self.target)
        self.assertFalse((self.target / 'web').exists())
        self.assertFalse((self.target / 'backups').exists())

    def test_sem_banco_nao_inventa_estado(self):
        self.db.unlink()
        with self.assertRaisesRegex(ValueError, 'Banco operacional nao encontrado'):
            updater.update(self.target)
        self.assertFalse(self.db.exists())

    def test_falha_de_substituicao_restaura_codigo(self):
        old = self.target / 'python/app.py'
        old.write_text('interface anterior')
        original = self.db.read_bytes()
        replace = updater.os.replace
        calls = 0

        def failing_replace(source, destination):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError('falha simulada')
            return replace(source, destination)

        with patch.object(updater.os, 'replace', side_effect=failing_replace):
            with self.assertRaisesRegex(OSError, 'falha simulada'):
                updater.update(self.target)
        self.assertEqual(old.read_text(), 'interface anterior')
        self.assertFalse((self.target / 'python/test_app.py').exists())
        self.assertEqual(self.db.read_bytes(), original)

    def test_segunda_atualizacao_preserva_backup_anterior(self):
        first = updater.update(self.target)
        second = updater.update(self.target)
        self.assertNotEqual(first['backup'], second['backup'])
        self.assertTrue((Path(first['backup']) / 'operacoes.sqlite').exists())
        self.assertTrue((Path(second['backup']) / 'arquivos/web/app.js').exists())

    def verify_connections_closed(self, fail_backup=False):
        """Mantenha referencias vivas: o teste nao depende da coleta de lixo."""
        connections = []
        real_connect = sqlite3.connect

        class TrackedConnection(sqlite3.Connection):
            def backup(self, target, *args, **kwargs):
                if fail_backup:
                    raise sqlite3.OperationalError('falha simulada no backup')
                return super().backup(target, *args, **kwargs)

        def connect(*args, **kwargs):
            kwargs['factory'] = TrackedConnection
            connection = real_connect(*args, **kwargs)
            connections.append(connection)
            return connection

        original = self.db.read_bytes()
        try:
            with patch.object(updater.sqlite3, 'connect', side_effect=connect):
                if fail_backup:
                    with self.assertRaisesRegex(sqlite3.OperationalError, 'falha simulada no backup'):
                        updater.update(self.target)
                    self.assertFalse((self.target / 'python/app.py').exists())
                else:
                    updater.update(self.target)
            self.assertEqual(len(connections), 2)
            # Uma conexao ainda aberta aceita SELECT mesmo depois do backup.
            for connection in connections:
                with self.assertRaises(sqlite3.ProgrammingError):
                    connection.execute('SELECT 1')
            self.assertEqual(self.db.read_bytes(), original)
        finally:
            # Libere os handles inclusive se uma regressao fizer o teste falhar.
            for connection in connections:
                connection.close()

    def test_fecha_conexoes_original_e_backup(self):
        self.verify_connections_closed()

    def test_falha_backup_fecha_conexoes_e_preserva_original(self):
        self.verify_connections_closed(fail_backup=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
