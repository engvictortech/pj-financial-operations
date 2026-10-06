# Regras, grão e indicadores

## Modelo

| Tabela | Grão | Chave |
|---|---|---|
| dim_empresa | Uma empresa fictícia | empresa_id |
| recebiveis | Uma obrigação simulada | recebivel_id |
| pagamentos_raw | Uma linha do extrato, podendo repetir um evento | pagamento_id pode repetir |
| conciliacao | Uma obrigação e seus pagamentos agregados até o corte | recebivel_id |

Um recebível pode ter vários pagamentos válidos. Somar o valor esperado após um JOIN direto com pagamentos multiplica o valor das obrigações com mais de uma liquidação. Por isso a conciliação agrega os pagamentos primeiro.

## Regras operacionais da demonstração

- Corte: 30/09/2026. Pagamentos posteriores não entram nos totais de conciliação.
- Uma obrigação é elegível quando sua data prevista é menor ou igual ao corte.
- Uma duplicata técnica é a repetição do mesmo ID de pagamento e mesmo conteúdo. É removida e contabilizada. Mesmo ID com conteúdo diferente bloqueia o processamento para evitar escolher silenciosamente uma versão.
- Pagamento sem recebível conhecido é separado dos totais conciliados e contado no relatório de qualidade.
- Não se infere a causa de um saldo: ele pode depender de investigação operacional. Não chamar todo saldo aberto de perda ou inadimplência do cliente.

| Status | Condição |
|---|---|
| A_VENCER | Data prevista depois do corte; excluído do denominador principal |
| PENDENTE | Obrigação elegível sem pagamentos observados até o corte |
| PARCIAL | Valor agregado pago inferior ao esperado e maior que zero |
| A_MAIOR | Valor agregado pago superior ao esperado |
| LIQUIDADO_COM_ATRASO | Valor pago exato, última liquidação depois da data prevista |
| CONCILIADO_NO_PRAZO | Valor pago exato, última liquidação até a data prevista |

A prioridade do status é a ordem acima. Um pagamento parcial atrasado continua PARCIAL, com atraso disponível em campo separado.

## Métricas propostas

| Papel | Indicador | Fórmula / população | Decisão |
|---|---|---|---|
| Principal | Conciliação no prazo | Obrigações CONCILIADO_NO_PRAZO / obrigações elegíveis | Investigar causas de diferenças e atrasos |
| Principal | Saldo aberto vencido | Soma de max(esperado - pago, 0) entre elegíveis | Priorizar conciliação dos maiores saldos |
| Principal | Excesso recebido | Soma de max(pago - esperado, 0) entre elegíveis | Investigar diferenças positivas separadamente |
| Diagnóstico | Atrasados já liquidados | Contagem de LIQUIDADO_COM_ATRASO | Avaliar pontualidade por parceiro |
| Diagnóstico | Idade do saldo aberto | Corte menos data prevista, somente quando saldo > 0 | Priorizar casos antigos |
| Proteção | Duplicatas removidas | Contagem antes do agrupamento, dentro do corte | Evitar inflar o valor recebido |
| Proteção | Pagamentos sem recebível | Contagem e valor de eventos sem vínculo | Expor transações fora da conciliação |

Não há meta de mercado ou do Sofisa. Uma meta só deve ser proposta após observar histórico real, obrigações contratuais e capacidade operacional. Os saldos abertos e excessos não se compensam no painel; exibem problemas diferentes.

Valores estão em centavos inteiros. Divida por 100 somente para exibição. Números em relatórios SQLite também permanecem em centavos.

## Dicionário dos campos adicionais de conciliacao

| Campo | Significado |
|---|---|
| valor_pago_centavos | Soma de eventos únicos vinculados, até o corte |
| diferenca_centavos | Pago menos esperado; sinal preservado |
| saldo_aberto_centavos | Diferença negativa em módulo, apenas entre elegíveis |
| excesso_centavos | Diferença positiva, apenas entre elegíveis |
| ultima_liquidacao | Maior data dos pagamentos considerados; vazio sem pagamento |
| qtd_pagamentos | Quantidade de eventos únicos vinculados |
| elegivel | 1 se vencimento até o corte, 0 caso contrário |
| dias_aberto | Dias desde vencimento, se existe saldo aberto |
| atraso_dias | Dias entre última liquidação e vencimento, piso zero |

## Conferência independente

Para o mesmo recorte de elegíveis:

`total esperado - total pago = saldo aberto - excesso`

Essa igualdade não prova que cada vínculo está correto, mas detecta erros de agregação. Combine-a com unicidade, relacionamentos, casos conhecidos e corte temporal.
