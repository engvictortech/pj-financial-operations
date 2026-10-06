"""Casos pequenos com resultados definidos independentemente do gerador."""
from datetime import date
from pipeline import conciliar

corte = date(2026, 9, 30)
base = dict(empresa_id='PJ1', data_venda='2026-09-01', data_prevista='2026-09-10',
            valor_esperado_centavos=10000)

def r(rid, **kwargs):
    return dict(base, recebivel_id=rid, **kwargs)

def p(pid, rid, valor, dia='2026-09-10'):
    return dict(pagamento_id=pid, recebivel_id=rid, valor_pago_centavos=valor, data_liquidacao=dia)

recebiveis = [r(str(i)) for i in range(6)]
futuro = r('6')
futuro['data_prevista'] = '2026-10-01'
recebiveis.append(futuro)
pagamentos = [p('p1', '1', 4000), p('p2', '2', 11000), p('p3', '3', 10000, '2026-09-12'),
              p('p4a', '4', 4000), p('p4b', '4', 6000), p('p5', '5', 10000), p('p5', '5', 10000),
              p('pf', '0', 10000, '2026-10-01'), p('po', 'nao_existe', 2500)]
linhas, dq = conciliar(recebiveis, pagamentos, corte)
by_id = {x['recebivel_id']: x for x in linhas}
esperado = {'0': 'PENDENTE', '1': 'PARCIAL', '2': 'A_MAIOR', '3': 'LIQUIDADO_COM_ATRASO',
            '4': 'CONCILIADO_NO_PRAZO', '5': 'CONCILIADO_NO_PRAZO', '6': 'A_VENCER'}
assert {k: v['status'] for k, v in by_id.items()} == esperado
assert by_id['1']['saldo_aberto_centavos'] == 6000
assert by_id['2']['excesso_centavos'] == 1000
assert by_id['3']['atraso_dias'] == 2
assert by_id['4']['qtd_pagamentos'] == 2
assert by_id['5']['valor_pago_centavos'] == 10000
assert by_id['6']['elegivel'] == 0 and by_id['6']['saldo_aberto_centavos'] == 0
assert dq['duplicatas_tecnicas_removidas'] == 1 and dq['pagamentos_sem_recebivel'] == 1
assert dq['linhas_fora_do_corte'] == 1
try:
    conciliar(recebiveis, [p('mesmo', '1', 4000), p('mesmo', '1', 5000)], corte)
except ValueError:
    pass
else:
    raise AssertionError('Duplicata conflitante deve bloquear a execução')
print('OK: parcial, excesso, atraso, múltiplos pagamentos, duplicatas, órfãos e corte temporal.')
