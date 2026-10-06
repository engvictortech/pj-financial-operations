-- Fila para investigação: total devido e maior envelhecimento por empresa.
SELECT c.empresa_id, e.nome, e.segmento, e.uf,
       SUM(CAST(c.saldo_aberto_centavos AS BIGINT)) AS saldo_aberto_centavos,
       MAX(c.dias_aberto) AS maior_dias_aberto,
       COUNT(*) AS recebiveis_com_saldo
FROM conciliacao c
JOIN dim_empresa e ON c.empresa_id = e.empresa_id
WHERE c.elegivel = 1 AND c.saldo_aberto_centavos > 0
GROUP BY c.empresa_id, e.nome, e.segmento, e.uf
ORDER BY saldo_aberto_centavos DESC, maior_dias_aberto DESC, c.empresa_id;
