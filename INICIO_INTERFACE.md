# Interface local — passo a passo

Se voce ja criou ocorrencias, atualize a pasta existente para continuar com seus tratamentos.
O pacote contem apenas dados sinteticos. Nao exige instalacao de pacotes Python.

## 1. Preparar a atualizacao

Baixe o ZIP atualizado e extraia em uma pasta NOVA, por exemplo:
`C:\Users\Giovanna Martins\Downloads\AtualizacaoInterface`.
Dentro dela deve existir `pj-payments-analytics`.
Mantenha a pasta do projeto atual no lugar. Feche o servidor da interface com Ctrl+C caso esteja aberto.

## 2. Atualizar a pasta atual

No PowerShell, execute o atualizador contido no pacote novo. Ajuste o caminho do primeiro arquivo se sua extracao estiver em outro local:

```powershell
python "C:\Users\Giovanna Martins\Downloads\AtualizacaoInterface\pj-payments-analytics\atualizar_interface.py" --destino "C:\Users\Giovanna Martins\Downloads\PJ_Payments_Analytics\pj-payments-analytics"
```

Ele verifica a compatibilidade do motor e salva um backup consistente do banco em
`backups\interface_<data>_<identificador>\operacoes.sqlite`, na pasta atual.
Copia somente sete arquivos de interface, teste e documentacao. Preserva o motor,
os dados de origem, o banco operacional e todo o historico.
Se o motor estiver diferente, o atualizador interrompe sem substituir a interface.
Guarde a pasta de backup.

## 3. Abrir o sistema

Volte para a pasta ORIGINAL do projeto:

```powershell
cd "C:\Users\Giovanna Martins\Downloads\PJ_Payments_Analytics\pj-payments-analytics"
python .\python\app.py --ator "Victor"
```

Mantenha esse terminal aberto e acesse no navegador:
`http://127.0.0.1:8765/#ocorrencia-2324`.

No caso que voce ja tratou, confira **Em analise**, **Victor**, **versao 4**,
**R$ 19.785,22** e quatro eventos no historico, incluindo sua observacao.
O sistema abre o banco existente. Nao e necessario importar a base novamente.

## 4. Investigar pela interface

- Confira o corte do lote e os valores esperados/recebidos da origem.
- Use os filtros de motivo, prioridade, responsavel e situacao.
- Abra uma ocorrencia e confira os pagamentos de origem e o historico.
- Registre uma observacao baseada na evidencia, sem inventar a causa da divergencia.
- Encerre somente quando houver uma conclusao documentada. O encerramento operacional nao quita o recebivel.
- Exporte o JSON para demonstrar a rastreabilidade da analise.

As acoes de tratamento alteram o banco, assim como os comandos do terminal.
Para apenas demonstrar, confira o caso sem confirmar novas acoes.

## Verificacao opcional

```powershell
python .\python\test_operacoes.py
python .\python\test_app.py
```

Os testes usam bancos temporarios e nao alteram seu banco operacional.
Para parar o servidor, pressione Ctrl+C no terminal. Para outra porta:
`python .\python\app.py --porta 8766` e abra `http://127.0.0.1:8766`.

## Primeira instalacao

Se voce nunca iniciou o projeto, extraia o pacote, entre na pasta interna e execute
`python .\python\operacoes.py iniciar --ator "Victor"`, depois `python .\python\app.py`.
O atualizador e reservado para uma instalacao que ja possui banco operacional.
