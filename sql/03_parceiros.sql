SELECT adquirente,
       COUNT(*) AS recebiveis_elegiveis,
       SUM(CAST(saldo_aberto_centavos AS BIGINT)) AS saldo_aberto_centavos,
       SUM(CAST(excesso_centavos AS BIGINT)) AS excesso_centavos,
       SUM(CASE WHEN status = 'LIQUIDADO_COM_ATRASO' THEN 1 ELSE 0 END) AS atrasados,
       100.0 * SUM(CASE WHEN status = 'CONCILIADO_NO_PRAZO' THEN 1 ELSE 0 END)
         / NULLIF(COUNT(*), 0) AS percentual_no_prazo
FROM conciliacao
WHERE elegivel = 1
GROUP BY adquirente
ORDER BY saldo_aberto_centavos DESC;
