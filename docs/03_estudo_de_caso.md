# Seu estudo de caso para o recrutador

Preencha depois de conferir o dashboard. Mantenha claramente a natureza simulada.

1. **Problema:** acompanhar liquidação de recebíveis PJ e localizar divergências.
2. **Dados:** 300 empresas fictícias, 12.000 obrigações, corte em 30/09/2026; nenhuma informação de clientes reais.
3. **Método:** identificação de eventos duplicados, exclusão temporal, agregação de pagamentos, comparação por obrigação e análise de saldos por parceiro/empresa.
4. **Evidências:** cite os totais do relatório de validação e as consultas que sustentam cada conclusão.
5. **Ações propostas:** investigar primeiro [empresa/parceiro], porque [saldo e idade]; apurar pagamentos a maior separadamente; revisar duplicatas na ingestão.
6. **Limitações:** simulação, regras simplificadas, ausência de UR formal e registradoras; nenhum resultado comercial real foi medido.
7. **Próxima melhoria:** snapshots diários para histórico de saldos, registros de resolução de ocorrências e medição de tempo de tratamento.

## Exercícios para dominar o projeto

- Encontre um caso de cada status e explique os valores em reais.
- Mostre por que somar antes de remover uma duplicata é incorreto.
- Explique por que dois pagamentos com IDs distintos para o mesmo recebível podem ser válidos.
- Mostre como uma liquidação posterior ao corte mudaria a classificação de uma obrigação.
- Compare taxa por quantidade com taxa ponderada pelo valor. Qual decisão cada uma suporta?
- Explique por que saldo aberto e excesso devem aparecer separados.

## Apresentação de três minutos

Conte o problema (30s), mostre os controles e a conciliação (60s), destaque uma evidência e a decisão que ela apoia (60s), e termine com limitações e próxima melhoria (30s). Cite a aderência às atividades da vaga, sem afirmar que conhece processos internos do banco.

Depois de concluir e validar o painel, uma descrição possível para currículo é:

“Desenvolvi um projeto independente de conciliação de recebíveis PJ com Python, SQL e Power BI, utilizando 12 mil obrigações simuladas. Implementei controles de duplicidade e corte temporal, identificação de pagamentos parciais, atrasos e divergências, além de indicadores para priorização de ocorrências.”

Use essa descrição somente depois de montar e validar o Power BI. Não declare que esse trabalho foi realizado para o Sofisa.
