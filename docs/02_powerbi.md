# Montagem no Power BI Desktop

1. Em Obter Dados > Texto/CSV, importe `data/processed/conciliacao.csv` e `dim_empresa.csv`.
2. Use nomes `conciliacao` e `dim_empresa`. CSV: delimitador vírgula, UTF-8. No Power Query, ajuste tipos explicitamente. Datas ISO como Data; todos os campos de centavos como Número Inteiro; IDs e status como Texto. Substitua data de última liquidação vazia por null se necessário. A localidade não pode converter erroneamente o separador decimal das medidas futuras.
3. Crie relacionamento `dim_empresa[empresa_id]` 1 para muitos `conciliacao[empresa_id]`, filtro em uma direção.
4. Crie as medidas de `powerbi/medidas.dax`, uma por vez. Se seu editor usar ponto e vírgula, adapte os separadores.
5. Formate medidas monetárias como R$ e taxas como percentual. Mantenha os dados originais em centavos.

## Perguntas que o relatório deve responder

- Quanto deveria ter sido liquidado e quanto chegou no recorte de obrigações vencidas?
- Quanto falta conciliar e quanto foi recebido a maior?
- Qual adquirente concentra o maior saldo e a pior taxa no prazo?
- Quais empresas e recebíveis investigar primeiro?

## Conteúdo sugerido

Visão operacional: cartões de esperado, recebido, saldo aberto, excesso e taxa no prazo. Comparação por adquirente. Distribuição dos status. Tabela de ocorrências com ID, empresa, data prevista, esperado, pago, saldo, dias e status. Filtros por adquirente, segmento, UF e data prevista.

Mantenha visível: **Dados simulados — corte 30/09/2026 — projeto independente**. Um filtro mensal pela data prevista mostra uma coorte avaliada no corte; não representa o saldo histórico daquele mês. Não chame o gráfico de evolução do saldo sem construir snapshots.

## Validação antes de divulgar

- Sem filtros, compare esperado, pago, aberto, excesso, quantidade elegível e quantidade no prazo com `reports/validacao.json`. Divida os totais em centavos por 100.
- Confirme que o denominador da taxa exclui A_VENCER.
- Filtre uma empresa e confira um recebível com múltiplos pagamentos em `data/raw/pagamentos.csv`.
- Confira que duplicatas técnicas não dobraram o valor e que o órfão não entrou na conciliação.
- Faça captura com rótulo de simulação. Não atribua ganhos reais ou resultados do banco a esse material.

As medidas são um ponto de partida e não foram executadas em uma sessão de Power BI. A validação final no aplicativo é parte desta etapa.
