# PJ Payments Analytics

**Conciliação de recebíveis de cartão PJ com Python, SQL e Power BI.**

Projeto independente de portfólio, inspirado em responsabilidades públicas de vagas bancárias. Todos os clientes, parceiros, pagamentos e valores são **sintéticos**. Não há vínculo com o Banco Sofisa nem acesso a seus dados, sistemas ou políticas.

## Problema de negócio

Uma operação fictícia precisa confrontar o que deveria receber com o que foi liquidado, identificar saldos pendentes e organizar a investigação de divergências por empresa e adquirente. A decisão diária é: quais ocorrências investigar primeiro e quais parceiros concentram atrasos ou diferenças?

Foco principal: Analista de Meios de Pagamento PJ Júnior. O anúncio oficial menciona conciliação, liquidação financeira, ocorrências operacionais, recebíveis PJ e indicadores; Excel, SQL e Power BI aparecem nos conhecimentos desejáveis/diferenciais.

## Primeiro passo no seu Windows

1. Extraia o ZIP para `D:\VICTOR\pj-payments-analytics` (ou outra pasta sua).
2. No VS Code, abra a pasta extraída que contém este README e abra um terminal.
3. Execute:

```powershell
python python/pipeline.py
python python/verificar_cenarios.py
```

Se `python` não for reconhecido, use `py` nos dois comandos. Requer Python 3.10 ou superior; a etapa inicial usa somente a biblioteca padrão, sem instalação de pacotes.

O pacote já inclui uma execução de exemplo. Ao rodar, os arquivos gerados dentro deste projeto são recriados. A geração tem semente 42 e corte em 30/09/2026.

Depois abra `reports/validacao.json`: ele mostra os totais sintéticos, o fechamento financeiro e os controles de qualidade. O segundo comando verifica casos pequenos com resultado conhecido.

## O que foi entregue

- `python/pipeline.py`: geração de dados, conciliação e validações.
- `python/verificar_cenarios.py`: testes de casos financeiros e do corte temporal.
- `data/raw/`: três fontes CSV simuladas, antes da conciliação.
- `data/processed/conciliacao.csv`: uma linha por recebível, pronta para análise.
- `data/processed/dim_empresa.csv`: dimensão de empresas fictícias.
- `data/processed/portfolio.sqlite`: banco local para executar e estudar SQL.
- `sql/`: indicadores, fila de prioridades e comparação de parceiros.
- `reports/`: resultados e controles desta execução.
- `powerbi/medidas.dax`: medidas propostas para o Power BI.
- `docs/`: definições, roteiro e associação às vagas.

O Power BI ainda precisa ser montado no seu computador; este pacote não contém PBIX. As consultas SQL foram executadas no SQLite. A execução no SQL Server e as medidas no Power BI não foram verificadas nesses aplicativos.

## Como estudar o SQL

Abra `data/processed/portfolio.sqlite` em um cliente SQLite e execute `sql/01_indicadores.sql`, depois `02_prioridades.sql` e `03_parceiros.sql`. Você pode conferir os resultados contra `reports/validacao.json` e os dois CSVs de relatório.

Os SQLs usam construções também disponíveis no T-SQL. Para sua etapa com SQL Server, importe `dim_empresa.csv` e `conciliacao.csv` para tabelas chamadas `dim_empresa` e `conciliacao`, em um banco separado de portfólio. Confira os tipos: IDs/status/textos como NVARCHAR; datas como DATE; valores em centavos como BIGINT; indicadores e contagens como INT. A data de última liquidação vazia deve virar NULL. Revise o esquema sugerido pelo assistente antes de concluir: valores monetários não devem virar FLOAT. Depois execute as mesmas consultas e compare os totais. Esse caminho é uma etapa posterior, não requisito para começar.

## Sequência de desenvolvimento

1. **Entender a operação:** leia `docs/01_regras_e_metricas.md` e investigue cinco recebíveis de status diferentes.
2. **Executar e conferir:** rode a geração e os testes; explique a identidade `esperado - pago = saldo aberto - excesso`.
3. **Analisar em SQL:** explique o agrupamento, o denominador da taxa e o motivo para agregar pagamentos antes de juntar recebíveis.
4. **Montar o Power BI:** siga `docs/02_powerbi.md`, confira totais e crie filtros.
5. **Escrever conclusões:** preencha `docs/03_estudo_de_caso.md` com números calculados e recomendações limitadas ao cenário simulado.
6. **Apresentar:** publique o código no seu GitHub, adicione capturas do dashboard e prepare uma explicação de três minutos.

## Limites do modelo

Uma obrigação simulada representa um recebível analítico de uma venda; **não é uma implementação formal da Unidade de Recebíveis (UR)**. O prazo de 1, 15 ou 30 dias é uma premissa da simulação, não uma regra real de arranjo de pagamento. Não são modelados feriados, parcelas, chargebacks, cancelamentos, antecipação, cessões, garantias ou integração com registradoras. A tarifa é simulada e constante por obrigação. Diferenças são comparadas exatamente em centavos; não há tolerância implícita.

A base foi desenhada para conter problemas. Frequências e valores não são evidência sobre o mercado nem sobre o Sofisa. Esta versão é um snapshot: um gráfico histórico por vencimento mostra o estado atual das coortes, não o histórico de saldos em cada mês. Evoluir para monitoramento real exigiria snapshots/eventos e novas regras.

## Fontes de alinhamento profissional

Consultadas em 05/10/2026:

- Meios de Pagamento PJ Júnior: https://bancosofisa.gupy.io/jobs/12417144
- Crédito Pleno Agronegócios: https://bancosofisa.gupy.io/jobs/12316669
- PLD Pleno Temporário: https://bancosofisa.gupy.io/jobs/12526787
- AI Lead: https://bancosofisa.gupy.io/jobs/12395357

O projeto demonstra competências e não substitui experiência profissional específica, certificações ou requisitos de senioridade das vagas.
