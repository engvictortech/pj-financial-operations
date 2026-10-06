"""Gestão local de ocorrências. Etapa 1: motor + CLI; sem autenticação ou UI.

Recebíveis, evidências e eventos ficam preservados em operacoes.sqlite.
Encerrar uma investigação nunca altera os valores financeiros.
"""
import argparse
import csv
import hashlib
import io
import json
import sqlite3
import sys
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline import conciliar

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / 'data' / 'processed' / 'operacoes.sqlite'
RULE_VERSION = 'ops-1.0'
CONCLUSOES = ('ANALISE_CONCLUIDA', 'SEM_DIVERGENCIA_APOS_REVISAO', 'TRATAMENTO_EXTERNO_DOCUMENTADO')
INTEGER_FIELDS = {
    'valor_bruto_centavos', 'tarifa_centavos', 'valor_esperado_centavos',
    'valor_pago_centavos', 'diferenca_centavos', 'saldo_aberto_centavos',
    'excesso_centavos', 'qtd_pagamentos', 'elegivel', 'dias_aberto', 'atraso_dias'
}
SOURCES = ('data/raw/empresas.csv', 'data/raw/recebiveis.csv', 'data/raw/pagamentos.csv',
           'data/processed/conciliacao.csv', 'reports/validacao.json')


class RegraError(ValueError):
    pass


def jdump(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def agora():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def texto(value, nome, minimo=1, maximo=2000):
    if not isinstance(value, str) or not minimo <= len(value.strip()) <= maximo:
        raise RegraError(f'{nome}: informe entre {minimo} e {maximo} caracteres.')
    return value.strip()


@contextmanager
def database(path=DEFAULT_DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA foreign_keys = ON')
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1):
            raise RegraError('Versao do banco operacional nao suportada; preserve o arquivo.')
        db.executescript((ROOT / 'sql/04_operacoes_schema.sql').read_text(encoding='utf-8'))
        yield db
    finally:
        db.close()


@contextmanager
def transaction(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def csv_rows(path, data):
    rows = list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline='')))
    if not rows:
        raise RegraError(f'Arquivo vazio: {path.name}')
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise RegraError(f'CSV malformado: {path.name}')
        for key in INTEGER_FIELDS & row.keys():
            try:
                row[key] = int(row[key])
            except ValueError as exc:
                raise RegraError(f'Inteiro invalido em {key}, arquivo {path.name}') from exc
    return rows


def prioridade(motivo, impacto, idade):
    # Politica didatica, versionada. Nao representa SLA ou politica de um banco.
    if motivo == 'PAGAMENTO_SEM_RECEBIVEL':
        return 'P2'
    if impacto >= 1_000_000 or idade >= 180:
        return 'P1'
    if impacto >= 100_000 or idade >= 30:
        return 'P2'
    return 'P3'


def preparar(root):
    """Verifica a base e reexecuta a conciliação antes de criar qualquer caso."""
    root = Path(root)
    # Leia cada arquivo uma vez: o hash identifica exatamente os bytes analisados.
    arquivos = {name: (root / name).read_bytes() for name in SOURCES}
    manifesto = {name: hashlib.sha256(data).hexdigest() for name, data in arquivos.items()}
    report = json.loads(arquivos[SOURCES[-1]].decode('utf-8'))
    if report.get('natureza') != 'DADOS SINTETICOS':
        raise RegraError('Esta etapa aceita somente a base sintetica do projeto.')
    corte = date.fromisoformat(report['data_corte'])
    empresas = csv_rows(root / SOURCES[0], arquivos[SOURCES[0]])
    recebiveis = csv_rows(root / SOURCES[1], arquivos[SOURCES[1]])
    pagamentos = csv_rows(root / SOURCES[2], arquivos[SOURCES[2]])
    processados = csv_rows(root / SOURCES[3], arquivos[SOURCES[3]])
    eids = {e['empresa_id'] for e in empresas}
    rids = {r['recebivel_id'] for r in recebiveis}
    if len(eids) != len(empresas) or len(rids) != len(recebiveis):
        raise RegraError('Duplicidade na chave de empresa ou recebivel.')
    mapa = {r['recebivel_id']: r for r in recebiveis}
    for r in recebiveis:
        if r['empresa_id'] not in eids:
            raise RegraError('Recebivel com empresa inexistente.')
        if not r['recebivel_id'] or not r['empresa_id']:
            raise RegraError('Chave vazia em recebivel.')
        venda = date.fromisoformat(r['data_venda'])
        prevista = date.fromisoformat(r['data_prevista'])
        if venda > prevista:
            raise RegraError('Vencimento anterior a venda.')
        if r['valor_bruto_centavos'] - r['tarifa_centavos'] != r['valor_esperado_centavos']:
            raise RegraError('Valor esperado inconsistente com bruto e tarifa.')
        if r['valor_esperado_centavos'] <= 0 or r['tarifa_centavos'] < 0:
            raise RegraError('Valor financeiro invalido.')
    for p in pagamentos:
        liquidacao = date.fromisoformat(p['data_liquidacao'])
        if not p['pagamento_id'] or not p['recebivel_id'] or p['valor_pago_centavos'] <= 0:
            raise RegraError('Pagamento com chave vazia ou valor nao positivo.')
        if p['recebivel_id'] in mapa and liquidacao < date.fromisoformat(mapa[p['recebivel_id']]['data_venda']):
            raise RegraError('Liquidacao anterior a venda.')
    recalculados, qualidade = conciliar(recebiveis, pagamentos, corte)
    key = lambda row: row['recebivel_id']
    if sorted(processados, key=key) != sorted(recalculados, key=key):
        raise RegraError('CSV processado diverge da conciliacao recalculada. Reexecute pipeline.py.')
    if qualidade != report['qualidade']:
        raise RegraError('Relatorio de qualidade diverge das fontes.')
    elegiveis = [r for r in recalculados if r['elegivel']]
    totals = {'empresas': len(empresas), 'recebiveis': len(recalculados), 'elegiveis': len(elegiveis),
              'esperado_centavos': sum(r['valor_esperado_centavos'] for r in elegiveis),
              'pago_centavos': sum(r['valor_pago_centavos'] for r in elegiveis),
              'saldo_aberto_centavos': sum(r['saldo_aberto_centavos'] for r in elegiveis),
              'excesso_centavos': sum(r['excesso_centavos'] for r in elegiveis),
              'conciliados_no_prazo': sum(r['status'] == 'CONCILIADO_NO_PRAZO' for r in elegiveis)}
    if any(report.get(k) != value for k, value in totals.items()):
        raise RegraError('Totais do relatorio divergem das fontes.')
    fingerprint = hashlib.sha256(jdump({'fontes': manifesto, 'regra': RULE_VERSION,
                                       'corte': corte.isoformat()}).encode()).hexdigest()
    orfaos = {p['pagamento_id']: p for p in pagamentos
              if p['recebivel_id'] not in rids and date.fromisoformat(p['data_liquidacao']) <= corte}
    return fingerprint, manifesto, corte, recalculados, qualidade, list(orfaos.values()), pagamentos


def evento(db, oid, tipo, ator, versao, detalhes, instante):
    db.execute('INSERT INTO eventos(ocorrencia_id,tipo,ator,instante,versao,detalhes_json) VALUES(?,?,?,?,?,?)',
               (oid, tipo, ator, instante, versao, jdump(detalhes)))


def importar(db, root=ROOT, ator='Victor'):
    ator = texto(ator, 'Ator', maximo=100)
    fingerprint, manifesto, corte, rows, qualidade, orfaos, pagamentos = preparar(root)
    por_recebivel = {}
    for p in pagamentos:
        por_recebivel.setdefault(p['recebivel_id'], []).append(p)
    with transaction(db):
        existing = db.execute('SELECT lote_id FROM lotes WHERE fingerprint=?', (fingerprint,)).fetchone()
        if existing:
            n = db.execute('SELECT COUNT(*) FROM ocorrencias WHERE lote_id=?', (existing[0],)).fetchone()[0]
            return {'lote_id': existing[0], 'nova_importacao': False, 'ocorrencias': n}
        instante = agora()
        lote = fingerprint
        db.execute('INSERT INTO lotes VALUES(?,?,?,?,?,?,?,?)',
                   (lote, fingerprint, corte.isoformat(), RULE_VERSION, instante, ator,
                    jdump(manifesto), jdump(qualidade)))
        db.executemany('INSERT INTO evidencias VALUES(?,?,?,?)',
                       [(lote, r['recebivel_id'], r['empresa_id'],
                         jdump({'conciliacao': r, 'pagamentos_origem': por_recebivel.get(r['recebivel_id'], [])}))
                        for r in rows])
        casos = []
        for r in sorted(rows, key=lambda r: r['recebivel_id']):
            if r['status'] in ('A_VENCER', 'CONCILIADO_NO_PRAZO'):
                continue
            impacto = r['saldo_aberto_centavos'] + r['excesso_centavos']
            idade = r['dias_aberto'] if impacto else r['atraso_dias']
            casos.append((r['recebivel_id'], r['recebivel_id'], r['empresa_id'], r['status'],
                          impacto, idade, {'recebivel': r}))
        for p in sorted(orfaos, key=lambda p: p['pagamento_id']):
            casos.append((p['pagamento_id'], None, None, 'PAGAMENTO_SEM_RECEBIVEL',
                          p['valor_pago_centavos'], 0, {'pagamento': p}))
        for referencia, rid, eid, motivo, valor, idade, origem in casos:
            pri = prioridade(motivo, valor, idade)
            cur = db.execute('''INSERT INTO ocorrencias(lote_id,referencia,recebivel_id,empresa_id,motivo,
                               valor_impacto_centavos,idade_dias,prioridade,criada_em,atualizada_em)
                               VALUES(?,?,?,?,?,?,?,?,?,?)''',
                             (lote, referencia, rid, eid, motivo, valor, idade, pri, instante, instante))
            evento(db, cur.lastrowid, 'CRIADA', ator, 1,
                   {'origem': origem, 'prioridade': pri, 'regra_versao': RULE_VERSION}, instante)
    return {'lote_id': lote, 'nova_importacao': True, 'ocorrencias': len(casos)}


def obter(db, oid):
    row = db.execute('SELECT * FROM ocorrencias WHERE ocorrencia_id=?', (oid,)).fetchone()
    if row is None:
        raise RegraError(f'Ocorrencia {oid} nao encontrada.')
    return dict(row)


def tratar(db, oid, acao, ator, versao, *, responsavel=None, nota=None, conclusao=None):
    ator = texto(ator, 'Ator', maximo=100)
    if not isinstance(versao, int) or versao < 1:
        raise RegraError('Informe a versao atual da ocorrencia.')
    with transaction(db):
        before = obter(db, oid)
        if before['versao'] != versao:
            raise RegraError(f'Conflito de versao: atual={before["versao"]}. Reabra o caso e revise.')
        changes, details = {}, {}
        if acao == 'atribuir':
            if before['status'] == 'RESOLVIDA':
                raise RegraError('Reabra a ocorrencia antes de alterar o responsavel.')
            resp = texto(responsavel, 'Responsavel', maximo=100)
            if resp == before['responsavel']:
                raise RegraError('Responsavel ja atribuido; nenhuma mudanca realizada.')
            changes['responsavel'] = resp
        elif acao == 'analisar':
            if before['status'] != 'ABERTA' or not before['responsavel']:
                raise RegraError('Para analisar, o caso deve estar ABERTO e ter responsavel.')
            changes['status'] = 'EM_ANALISE'
        elif acao == 'observar':
            if before['status'] != 'EM_ANALISE':
                raise RegraError('Observacoes de investigacao exigem caso EM_ANALISE.')
            details['observacao'] = texto(nota, 'Observacao', minimo=5)
        elif acao == 'resolver':
            if before['status'] != 'EM_ANALISE':
                raise RegraError('A resolucao exige uma ocorrencia EM_ANALISE.')
            if conclusao not in CONCLUSOES:
                raise RegraError(f'Conclusao deve ser uma destas: {", ".join(CONCLUSOES)}')
            changes.update(status='RESOLVIDA', conclusao=conclusao,
                           justificativa=texto(nota, 'Justificativa', minimo=20))
        elif acao == 'reabrir':
            if before['status'] != 'RESOLVIDA':
                raise RegraError('Somente ocorrencias RESOLVIDAS podem ser reabertas.')
            details['motivo_reabertura'] = texto(nota, 'Motivo de reabertura', minimo=20)
            changes.update(status='EM_ANALISE', conclusao=None, justificativa=None, resolvida_em=None)
        else:
            raise RegraError('Acao desconhecida.')
        instante = agora()
        if acao == 'resolver':
            changes['resolvida_em'] = instante
        changes.update(versao=versao + 1, atualizada_em=instante)
        details['alteracoes'] = {key: {'antes': before[key], 'depois': value}
                                for key, value in changes.items() if key not in ('atualizada_em', 'versao')}
        keys = list(changes)
        cur = db.execute('UPDATE ocorrencias SET ' + ','.join(f'{key}=?' for key in keys)
                         + ' WHERE ocorrencia_id=? AND versao=?',
                         tuple(changes[key] for key in keys) + (oid, versao))
        if cur.rowcount != 1:
            raise RegraError('Conflito ao salvar; nenhuma alteracao realizada.')
        evento(db, oid, acao.upper(), ator, versao + 1, details, instante)
        return obter(db, oid)


def historico(db, oid):
    obter(db, oid)
    rows = db.execute('SELECT * FROM eventos WHERE ocorrencia_id=? ORDER BY evento_id', (oid,)).fetchall()
    result = []
    for row in rows:
        value = dict(row)
        value['detalhes'] = json.loads(value.pop('detalhes_json'))
        result.append(value)
    return result


def detalhe(db, oid):
    caso = obter(db, oid)
    origem = db.execute('SELECT dados_json FROM evidencias WHERE lote_id=? AND recebivel_id=?',
                        (caso['lote_id'], caso['recebivel_id'])).fetchone()
    return {'ocorrencia': caso, 'evidencia': json.loads(origem[0]) if origem else None,
            'historico': historico(db, oid)}


def listar(db, limite=5, status=None):
    if not 1 <= limite <= 100:
        raise RegraError('Limite deve estar entre 1 e 100.')
    if status and status not in ('ABERTA', 'EM_ANALISE', 'RESOLVIDA'):
        raise RegraError('Status invalido.')
    columns = 'ocorrencia_id,referencia,motivo,prioridade,valor_impacto_centavos,idade_dias,status,responsavel,versao'
    where = ' WHERE status=?' if status else ''
    params = (status, limite) if status else (limite,)
    rows = db.execute('SELECT ' + columns + ' FROM ocorrencias' + where
                      + ' ORDER BY prioridade,valor_impacto_centavos DESC,idade_dias DESC,ocorrencia_id LIMIT ?', params)
    return [dict(row) for row in rows]


def main():
    parser = argparse.ArgumentParser(description='PJ Financial Operations — motor local de ocorrencias (dados sinteticos).')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest='comando', required=True)
    ini = sub.add_parser('iniciar', help='Validar as fontes e importar sem duplicar lotes.')
    ini.add_argument('--ator', required=True)
    lista = sub.add_parser('listar')
    lista.add_argument('--limite', type=int, default=5)
    lista.add_argument('--status', choices=['ABERTA', 'EM_ANALISE', 'RESOLVIDA'])
    ver = sub.add_parser('ver')
    ver.add_argument('id', type=int)
    for action in ('atribuir', 'analisar', 'observar', 'resolver', 'reabrir'):
        cmd = sub.add_parser(action)
        cmd.add_argument('id', type=int)
        cmd.add_argument('--ator', required=True)
        cmd.add_argument('--versao', type=int, required=True)
        if action == 'atribuir':
            cmd.add_argument('--responsavel', required=True)
        if action in ('observar', 'resolver', 'reabrir'):
            cmd.add_argument('--texto', required=True)
        if action == 'resolver':
            cmd.add_argument('--conclusao', choices=CONCLUSOES, required=True)
    args = parser.parse_args()
    try:
        with database(args.db) as db:
            if args.comando == 'iniciar':
                result = importar(db, ator=args.ator)
            elif args.comando == 'listar':
                result = listar(db, args.limite, args.status)
            elif args.comando == 'ver':
                result = detalhe(db, args.id)
            else:
                result = tratar(db, args.id, args.comando, args.ator, args.versao,
                                 responsavel=getattr(args, 'responsavel', None),
                                 nota=getattr(args, 'texto', None), conclusao=getattr(args, 'conclusao', None))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (RegraError, sqlite3.Error, OSError, ValueError, KeyError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
