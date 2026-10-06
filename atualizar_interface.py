"""Atualiza somente a interface; preserva o motor, as fontes e o banco existente."""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
COMPATIBLE = ('python/operacoes.py', 'sql/04_operacoes_schema.sql')
FILES = ('python/app.py', 'python/test_app.py', 'web/index.html', 'web/app.css',
         'web/app.js', 'INICIO_INTERFACE.md', 'docs/07_interface.md')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update(destination, source=SOURCE):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError('Extraia a atualizacao em uma pasta separada da pasta do projeto existente.')
    if not destination.is_dir():
        raise ValueError('Destino inexistente. Informe a pasta interna pj-payments-analytics do projeto atual.')
    for relative in COMPATIBLE:
        old, new = destination / relative, source / relative
        if not old.is_file() or not new.is_file() or digest(old) != digest(new):
            raise ValueError(f'Motor incompativel ou modificado: {relative}. Nenhum arquivo foi atualizado.')
    for relative in FILES:
        if not (source / relative).is_file():
            raise ValueError(f'Atualizacao incompleta: falta {relative}.')
        target = destination / relative
        # Evite substituir caminhos que apontem para fora do projeto.
        if destination not in target.resolve().parents:
            raise ValueError(f'Caminho fora do projeto: {relative}.')
        if target.exists() and not target.is_file():
            raise ValueError(f'O destino nao e um arquivo: {relative}.')
    db = destination / 'data/processed/operacoes.sqlite'
    if not db.is_file():
        raise ValueError('Banco operacional nao encontrado. Este atualizador exige o projeto ja iniciado.')
    if destination not in db.resolve().parents:
        raise ValueError('O banco aponta para fora do projeto.')
    backup_parent = destination / 'backups'
    if backup_parent.exists() and backup_parent.is_symlink():
        raise ValueError('A pasta backups nao pode ser um link simbolico.')
    backup_parent.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = Path(tempfile.mkdtemp(prefix=f'interface_{stamp}_', dir=backup_parent))
    # A API de backup inclui transacoes confirmadas mesmo se o banco usar WAL.
    # O contexto da Connection faz commit/rollback, mas nao fecha o arquivo.
    # closing libera ambos os bancos tambem quando verificacao/backup falham.
    with closing(sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)) as original:
        if original.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('A verificacao do banco falhou. Nenhum arquivo de interface foi alterado.')
        tables = {row[0] for row in original.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'lotes', 'ocorrencias', 'eventos', 'evidencias'} <= tables:
            raise ValueError('Esquema operacional inesperado. Nenhum arquivo de interface foi alterado.')
        with closing(sqlite3.connect(backup / 'operacoes.sqlite')) as saved:
            original.backup(saved)
    previous = []
    try:
        # Guarde todos os arquivos anteriores antes da primeira substituicao.
        for relative in FILES:
            target = destination / relative
            existed = target.exists()
            if existed:
                stored = backup / 'arquivos' / relative
                stored.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, stored)
            previous.append((relative, existed))
        with tempfile.TemporaryDirectory(prefix='.interface-stage-', dir=destination) as temp:
            stage = Path(temp)
            for relative in FILES:
                candidate = stage / relative
                candidate.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative, candidate)
            for relative in FILES:
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(stage / relative, target)
    except Exception:
        # Restaure os arquivos de codigo; o banco original nunca foi substituido.
        for relative, existed in reversed(previous):
            target = destination / relative
            if existed:
                shutil.copy2(backup / 'arquivos' / relative, target)
            elif target.is_file():
                target.unlink()
        raise
    result = {'interface_atualizada': True, 'destino': str(destination),
              'backup': str(backup), 'banco_original_preservado': True,
              'arquivos_atualizados': list(FILES)}
    (backup / 'atualizacao.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description='Atualizacao da interface com backup do banco existente.')
    parser.add_argument('--destino', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = update(args.destino)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f'Atualizacao interrompida: {exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
