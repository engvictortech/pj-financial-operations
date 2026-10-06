-- Valores em centavos. Uma linha por recebível. Recorte = vencidos até 30/09/2026.
-- Compatível com SQLite e T-SQL após carregar conciliacao.
SELECT COUNT(*) AS recebiveis_elegiveis,
       SUM(CAST(valor_esperado_centavos AS BIGINT)) AS esperado_centavos,
       SUM(CAST(valor_pago_centavos AS BIGINT)) AS pago_centavos,
       SUM(CAST(saldo_aberto_centavos AS BIGINT)) AS aberto_centavos,
       SUM(CAST(excesso_centavos AS BIGINT)) AS excesso_centavos,
       SUM(CASE WHEN status = 'CONCILIADO_NO_PRAZO' THEN 1 ELSE 0 END) AS conciliados_no_prazo,
       100.0 * SUM(CASE WHEN status = 'CONCILIADO_NO_PRAZO' THEN 1 ELSE 0 END)
         / NULLIF(COUNT(*), 0) AS percentual_no_prazo
FROM conciliacao
WHERE elegivel = 1;
