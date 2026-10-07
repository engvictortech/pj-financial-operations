"""Verificação da geração da demo; não acessa o banco operacional do usuário."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import exportar_demo as demo
import operacoes as ops


class ExportarDemoTests(unittest.TestCase):
    def test_exporta_com_banco_temporario_sem_acessar_operacional(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_database = ops.database
            accessed = []

            def guarded(path):
                path = Path(path)
                self.assertNotEqual(path.resolve(), ops.DEFAULT_DB.resolve())
                self.assertEqual(path.name, 'demo.sqlite')
                accessed.append(path)
                return real_database(path)

            with patch.object(ops, 'database', side_effect=guarded):
                result = demo.exportar(root / 'docs')
            self.assertEqual(len(accessed), 1)
            self.assertFalse(accessed[0].exists())
            self.assertEqual(result['ocorrencias'], 2348)
            data = json.loads((root / 'docs/demo/dados.json').read_text(encoding='utf-8'))
            self.assertTrue(all(c['ocorrencia']['status'] == 'ABERTA' for c in data['casos']))
            self.assertEqual(data['casos'][303]['evidencia']['conciliacao']['saldo_aberto_centavos'], 976317)
            html = (root / 'docs/index.html').read_text(encoding='utf-8')
            for asset in ('./demo/app.css', './demo/demo.css', './demo/demo-engine.js', './demo/app.js'):
                self.assertIn(asset, html)
                self.assertTrue((root / 'docs' / asset).is_file())
            js = (root / 'docs/demo/app.js').read_text(encoding='utf-8')
            self.assertNotIn('fetch(path', js)
            self.assertNotIn('href="/api', js)
            self.assertNotIn('localStorage', js)
            self.assertIn('URL.createObjectURL', js)

    def test_base_invalida_bloqueia_antes_de_escrever(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'docs'
            with patch.object(ops, 'importar', side_effect=ops.RegraError('Base inconsistente')):
                with self.assertRaises(ops.RegraError):
                    demo.exportar(output)
            self.assertFalse(output.exists())

    def test_mudanca_na_interface_exige_revisao_explicita(self):
        with self.assertRaises(ValueError):
            demo.replace_once('novo formato', 'formato antigo', 'adaptado')
        with self.assertRaises(ValueError):
            demo.replace_once('duplo duplo', 'duplo', 'adaptado')


if __name__ == '__main__':
    unittest.main(verbosity=2)
