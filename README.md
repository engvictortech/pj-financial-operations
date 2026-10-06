# PJ Financial Operations

**Sistema local de conciliacao e tratamento de ocorrencias financeiras — projeto independente, com dados sinteticos.**

Fila de investigacao com origem financeira, responsaveis, observacoes, conclusao, reabertura e historico.
A base analitica sustenta as evidencias; Power BI e uma extensao opcional.

## Comecar

Para atualizar um projeto ja iniciado, leia `INICIO_INTERFACE.md`: o atualizador salva backup e preserva seu banco.
Para uma primeira instalacao, abra a pasta interna do projeto no PowerShell:

```powershell
python .\python\operacoes.py iniciar --ator "Victor"
python .\python\app.py --ator "Victor"
```

Abra `http://127.0.0.1:8765`. Python 3.10+; sem pacotes adicionais.
A primeira importacao cria 2.348 ocorrencias. Repetir os mesmos arquivos preserva lote e tratamentos.
O servidor reutiliza o banco operacional, sem importar ou reconstruir dados ao iniciar.

## Entrega

- Fila com busca, filtros, prioridades explicaveis e paginacao.
- Investigacao de cada ocorrencia, pagamentos de origem e historico.
- Atribuicao, analise, observacao, encerramento e reabertura pelo navegador ou terminal.
- Controle de versao e gravacao atomica de acao/evento.
- Lotes, qualidade e identificacao dos arquivos de origem.
- Exportacao de evidencias e historico em JSON.

## Organizacao

- `python/operacoes.py`: regras e CLI.
- `python/app.py` e `web/`: servidor local e interface.
- `python/test_operacoes.py`: 13 testes do motor.
- `python/test_app.py`: 10 testes HTTP em bancos temporarios.
- `python/test_atualizacao.py`: 7 testes de preservacao, restauracao e fechamento de conexoes na atualizacao.
- `atualizar_interface.py`: atualizacao com backup do banco existente.
- `sql/04_operacoes_schema.sql`: entidades, indices e protecao de evidencias/eventos.
- `INICIO_OPERACOES.md` e `INICIO_INTERFACE.md`: passos de uso.
- `docs/06_operacoes_especificacao.md` e `docs/07_interface.md`: regras e limites.
- `docs/05_base_analitica.md`: geracao sintetica, SQL e Power BI opcional.

## Verificacao

```powershell
python .\python\test_operacoes.py
python .\python\test_app.py
```

Os testes nao alteram o banco do usuario. O motor e a API foram verificados com Python 3.12 nesta execucao.
O usuario verificou o motor em Python 3.13. Encerrar uma investigacao nao altera o saldo financeiro do snapshot.

## Portfolio

O projeto evidencia conciliacao, analise de divergencias, controle operacional e documentacao de decisoes.
A aderencia as vagas esta documentada em `docs/04_aderencia_vagas.md`.
Nao existe vinculo com o Sofisa nem uso de seus dados ou sistemas.
As prioridades sao premissas didaticas. A identificacao do analista e informada localmente, sem autenticacao.
Este e um projeto de portfolio executavel; nao e um sistema bancario em producao.
