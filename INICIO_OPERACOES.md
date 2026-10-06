# Comece aqui: PJ Financial Operations — etapa 1

Nesta etapa você executa o motor operacional pelo terminal. A interface visual ainda não foi desenhada nem implementada. O objetivo é entender e validar o processo antes das telas.

## Instalação

1. Extraia o ZIP atualizado em uma pasta nova, para manter sua execução anterior disponível.
2. No VS Code, abra a pasta interna `pj-payments-analytics`, que contém este documento e as pastas `python`, `sql` e `data`.
3. Abra Terminal > Novo Terminal. Seu Python 3.13 é compatível; não há pacotes para instalar nesta etapa.

Os arquivos de dados e a conciliação já estão incluídos no pacote. Você não precisa executar a geração novamente para iniciar o módulo operacional.

## Primeiro comando

```powershell
python .\python\operacoes.py iniciar --ator "Victor"
```

Resultado esperado na primeira execução: `nova_importacao: true` e `ocorrencias: 2348`. Na repetição com os mesmos arquivos: `nova_importacao: false` e as mesmas 2.348 ocorrências; o histórico existente é preservado. `lote_id` é um identificador de origem, não precisa copiá-lo manualmente.

## Verificar a fila

```powershell
python .\python\operacoes.py listar --limite 5
```

Na fila, observe ID da ocorrência, recebível/referência, motivo, prioridade, valor em centavos, idade, status e versão. A prioridade considera uma política didática descrita em `docs/06_operacoes_especificacao.md`.

## Abrir o exemplo que você já investigou

O recebível `R000001` vira a ocorrência 1 em um banco recém-criado com esta base. Primeiro confira o ID e a versão; não suponha o mesmo ID em um banco que já tenha outras importações.

```powershell
python .\python\operacoes.py ver 1
```

Você verá a ocorrência, a conciliação preservada, os pagamentos do arquivo de origem e os eventos históricos. O pagamento `P000001_0` de 766.920 centavos deve aparecer. Pagamentos originais posteriores ao corte, se presentes em outros casos, são exibidos como evidência e não fazem parte do valor conciliado; confira as datas.

## Testar sem alterar seu banco

```powershell
python .\python\test_operacoes.py
```

Esperado: 13 testes e `OK`. Os testes usam bancos temporários, separados de suas ocorrências.

## Tratamento guiado do exemplo

Execute estes comandos em sequência somente depois de compreender os resultados de `ver 1`. As versões abaixo pressupõem uma ocorrência 1 nova, com versão inicial 1. Se você já a tratou, consulte novamente e use a versão atual.

```powershell
python .\python\operacoes.py atribuir 1 --responsavel "Victor" --ator "Victor" --versao 1
python .\python\operacoes.py analisar 1 --ator "Victor" --versao 2
python .\python\operacoes.py observar 1 --ator "Victor" --versao 3 --texto "Pagamento P000001_0 localizado na origem; valor parcial confirmado."
python .\python\operacoes.py resolver 1 --ator "Victor" --versao 4 --conclusao "ANALISE_CONCLUIDA" --texto "Analise da origem concluida; o saldo permanece aberto no corte e exige acompanhamento."
python .\python\operacoes.py ver 1
```

O status de tratamento estará RESOLVIDA, mas a evidência financeira continuará PARCIAL, com saldo de 766.921 centavos. Aqui RESOLVIDA significa investigação encerrada e documentada; não significa quitação, recuperação ou correção financeira.

## Reabrir preservando a conclusão anterior

```powershell
python .\python\operacoes.py reabrir 1 --ator "Victor" --versao 5 --texto "Novo documento recebido exige revisao da conclusao anterior."
python .\python\operacoes.py ver 1
```

O estado volta para EM_ANALISE. A conclusão atual é limpa para nova análise, mas a conclusão anterior permanece no histórico.

## Arquivo que guarda seu trabalho

`data/processed/operacoes.sqlite` contém o banco operacional. Ele é criado no seu computador ao executar `iniciar` e não acompanha o ZIP. O banco analítico `portfolio.sqlite` é separado. Regenerar a base analítica não apaga os tratamentos do banco operacional; fontes alteradas criam outro lote, que deve ser avaliado separadamente.

Para preservar o trabalho antes de trocar de pasta/versão, feche os programas que usam esse banco e guarde uma cópia de `operacoes.sqlite`. Evite colocar cópias de bancos locais tratados no repositório de demonstração.
