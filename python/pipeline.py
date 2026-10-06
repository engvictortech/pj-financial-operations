"""Demonstração independente: dados sintéticos, valores em centavos, corte temporal.
Python 3.10+; somente biblioteca padrão. Não representa dados/regras do Sofisa.
"""
import csv
import json
import random
import sqlite3
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORTE = date(2026, 9, 30)
SEED = 42


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def gerar():
    rng = random.Random(SEED)
    empresas = [dict(empresa_id=f'PJ{i:04}', nome=f'Empresa simulada {i:04}',
                     segmento=['Comercio', 'Servicos', 'Industria', 'Agro'][i % 4],
                     uf=['SP', 'MG', 'PR', 'GO', 'BA'][i % 5]) for i in range(1, 301)]
    recebiveis, pagamentos = [], []
    inicio = date(2025, 1, 1)
    for i in range(1, 12001):
        venda = inicio + timedelta(days=rng.randrange(638))
        vencimento = venda + timedelta(days=rng.choice([1, 15, 30]))
        bruto = rng.randrange(10000, 2000001)
        taxa = rng.choice([100, 150, 200, 250, 300])  # pontos base, 100 = 1%
        tarifa = (bruto * taxa + 5000) // 10000
        esperado = bruto - tarifa
        rid = f'R{i:06}'
        recebiveis.append(dict(recebivel_id=rid, empresa_id=rng.choice(empresas)['empresa_id'],
                               adquirente=['Adq_A', 'Adq_B', 'Adq_C'][i % 3],
                               bandeira=['Band_A', 'Band_B'][i % 2], data_venda=venda.isoformat(),
                               data_prevista=vencimento.isoformat(), valor_bruto_centavos=bruto,
                               tarifa_centavos=tarifa, valor_esperado_centavos=esperado))
        caso = i % 20
        if caso == 0:
            continue
        if caso == 1:
            valores = [esperado // 2]
        elif caso == 2:
            valores = [esperado + 10000]
        elif caso == 4:
            valores = [esperado // 2, esperado - esperado // 2]
        else:
            valores = [esperado]
        for j, valor in enumerate(valores):
            p = dict(pagamento_id=f'P{i:06}_{j}', recebivel_id=rid,
                     data_liquidacao=(vencimento + timedelta(days=5 if caso == 3 else 0)).isoformat(),
                     valor_pago_centavos=valor)
            pagamentos.append(p)
            if caso == 5:
                pagamentos.append(p.copy())  # repetição técnica, não nova liquidação
    pagamentos.append(dict(pagamento_id='P_ORFAO', recebivel_id='R_INEXISTENTE',
                           data_liquidacao='2026-09-29', valor_pago_centavos=12345))
    return empresas, recebiveis, pagamentos


def conciliar(recebiveis, pagamentos, corte):
    conhecidos = {r['recebivel_id'] for r in recebiveis}
    vistos, grupos = {}, defaultdict(list)
    qualidade = Counter()
    for p in pagamentos:
        if date.fromisoformat(p['data_liquidacao']) > corte:
            qualidade['linhas_fora_do_corte'] += 1
            continue
        pid = p['pagamento_id']
        if pid in vistos:
            if vistos[pid] != p:
                raise ValueError(f'ID de pagamento com conteúdo conflitante: {pid}')
            qualidade['duplicatas_tecnicas_removidas'] += 1
            continue
        vistos[pid] = p
        if p['recebivel_id'] not in conhecidos:
            qualidade['pagamentos_sem_recebivel'] += 1
            qualidade['valor_orfao_centavos'] += p['valor_pago_centavos']
            continue
        if p['valor_pago_centavos'] <= 0:
            raise ValueError('Pagamento não positivo')
        grupos[p['recebivel_id']].append(p)
    linhas = []
    for r in recebiveis:
        if date.fromisoformat(r['data_venda']) > corte:
            continue
        ps = grupos[r['recebivel_id']]
        esperado = r['valor_esperado_centavos']
        pago = sum(p['valor_pago_centavos'] for p in ps)
        ultima = max((p['data_liquidacao'] for p in ps), default='')
        venc = date.fromisoformat(r['data_prevista'])
        elegivel = int(venc <= corte)
        if not elegivel:
            status = 'A_VENCER'
        elif not ps:
            status = 'PENDENTE'
        elif pago < esperado:
            status = 'PARCIAL'
        elif pago > esperado:
            status = 'A_MAIOR'
        elif date.fromisoformat(ultima) > venc:
            status = 'LIQUIDADO_COM_ATRASO'
        else:
            status = 'CONCILIADO_NO_PRAZO'
        em_aberto = max(esperado - pago, 0) if elegivel else 0
        linhas.append(dict(**r, valor_pago_centavos=pago,
                           diferenca_centavos=pago - esperado,
                           saldo_aberto_centavos=em_aberto,
                           excesso_centavos=max(pago - esperado, 0) if elegivel else 0,
                           ultima_liquidacao=ultima, qtd_pagamentos=len(ps),
                           elegivel=elegivel, status=status,
                           dias_aberto=max((corte - venc).days, 0) if em_aberto else 0,
                           atraso_dias=max((date.fromisoformat(ultima) - venc).days, 0) if ultima else 0))
    return linhas, dict(qualidade)


def validar(empresas, recebiveis, linhas):
    assert len({r['recebivel_id'] for r in recebiveis}) == len(recebiveis)
    assert len({e['empresa_id'] for e in empresas}) == len(empresas)
    ids = {e['empresa_id'] for e in empresas}
    for r in linhas:
        assert r['empresa_id'] in ids
        assert r['valor_bruto_centavos'] - r['tarifa_centavos'] == r['valor_esperado_centavos']
        assert r['valor_esperado_centavos'] > 0
        assert r['valor_pago_centavos'] - r['valor_esperado_centavos'] == r['diferenca_centavos']
        assert not r['ultima_liquidacao'] or r['ultima_liquidacao'] <= CORTE.isoformat()
    elegiveis = [r for r in linhas if r['elegivel']]
    esperado = sum(r['valor_esperado_centavos'] for r in elegiveis)
    pago = sum(r['valor_pago_centavos'] for r in elegiveis)
    aberto = sum(r['saldo_aberto_centavos'] for r in elegiveis)
    excesso = sum(r['excesso_centavos'] for r in elegiveis)
    assert esperado - pago == aberto - excesso  # fechamento contábil do recorte
    return dict(data_corte=CORTE.isoformat(), natureza='DADOS SINTETICOS', seed=SEED,
                empresas=len(empresas), recebiveis=len(linhas), elegiveis=len(elegiveis),
                esperado_centavos=esperado, pago_centavos=pago, saldo_aberto_centavos=aberto,
                excesso_centavos=excesso,
                conciliados_no_prazo=sum(r['status'] == 'CONCILIADO_NO_PRAZO' for r in elegiveis),
                status=dict(Counter(r['status'] for r in linhas)))


def sqlite_export(empresas, recebiveis, pagamentos, linhas):
    destino = ROOT / 'data' / 'processed' / 'portfolio.sqlite'
    destino.unlink(missing_ok=True)
    with sqlite3.connect(destino) as db:
        for tabela, rows in [('dim_empresa', empresas), ('recebiveis', recebiveis),
                            ('pagamentos_raw', pagamentos), ('conciliacao', linhas)]:
            campos = list(rows[0])
            definicoes = ', '.join(f'{c} {"INTEGER" if isinstance(rows[0][c], int) else "TEXT"}' for c in campos)
            db.execute(f'CREATE TABLE {tabela} ({definicoes})')
            db.executemany(f'INSERT INTO {tabela} VALUES ({", ".join("?" for _ in campos)})',
                           [tuple(r[c] for c in campos) for r in rows])
        db.execute('CREATE UNIQUE INDEX ix_conciliacao_id ON conciliacao(recebivel_id)')
        resultado = db.execute((ROOT / 'sql' / '01_indicadores.sql').read_text(encoding='utf-8')).fetchone()
        elegiveis = [r for r in linhas if r['elegivel']]
        assert resultado[0] == len(elegiveis)
        assert resultado[1] == sum(r['valor_esperado_centavos'] for r in elegiveis)
        assert resultado[2] == sum(r['valor_pago_centavos'] for r in elegiveis)
        assert resultado[3] == sum(r['saldo_aberto_centavos'] for r in elegiveis)
        assert resultado[4] == sum(r['excesso_centavos'] for r in elegiveis)
        assert resultado[5] == sum(r['status'] == 'CONCILIADO_NO_PRAZO' for r in elegiveis)
        for nome in ['02_prioridades.sql', '03_parceiros.sql']:
            cursor = db.execute((ROOT / 'sql' / nome).read_text(encoding='utf-8'))
            rows = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]
            if rows:
                write_csv(ROOT / 'reports' / nome.replace('.sql', '.csv'), rows)


def main():
    empresas, recebiveis, pagamentos = gerar()
    for nome, rows in [('empresas', empresas), ('recebiveis', recebiveis), ('pagamentos', pagamentos)]:
        write_csv(ROOT / 'data' / 'raw' / f'{nome}.csv', rows)
    linhas, qualidade = conciliar(recebiveis, pagamentos, CORTE)
    resumo = validar(empresas, recebiveis, linhas)
    resumo['qualidade'] = qualidade
    write_csv(ROOT / 'data' / 'processed' / 'dim_empresa.csv', empresas)
    write_csv(ROOT / 'data' / 'processed' / 'conciliacao.csv', linhas)
    sqlite_export(empresas, recebiveis, pagamentos, linhas)
    (ROOT / 'reports' / 'validacao.json').write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(resumo, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
