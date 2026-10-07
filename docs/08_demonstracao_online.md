# Demonstração online

A demonstração é publicada no GitHub Pages a partir da pasta `docs/`.
O visitante pode filtrar as 2.348 ocorrências, conferir evidências, atribuir um
responsável, iniciar uma análise, observar, encerrar, reabrir e exportar JSON.
Não precisa instalar Python nem manter o computador do autor ligado.

## Dois ambientes

| Ambiente | Dados e tratamento | Persistência |
|---|---|---|
| Python em `127.0.0.1:8765` | Motor Python, API HTTP local e SQLite | Banco operacional local e histórico de eventos |
| GitHub Pages | Snapshot sintético validado pelo motor Python; regras de tratamento simuladas em JavaScript | Somente memória da aba; recarregar ou reiniciar descarta as alterações |

O site não executa Python, não conecta ao SQLite do autor e não representa um
sistema multiusuário de produção. Os nomes são informados pelo visitante, sem
autenticação. Os valores financeiros nunca são editados pelo tratamento.
Os controles transacionais e as proteções do banco são demonstrados pelos testes
da versão Python; não devem ser atribuídos à hospedagem estática.

## Origem verificável

`python/exportar_demo.py` usa `operacoes.preparar` e `operacoes.importar` para
revalidar as fontes e gerar um banco temporário. Exporta o lote, os hashes SHA-256,
as evidências e as ocorrências para `docs/demo/dados.json`. O banco temporário é
fechado e removido. O banco `data/processed/operacoes.sqlite` não é acessado.

Todos os casos começam abertos e sem responsável. O histórico inicial identifica
o gerador da demonstração. As ações do visitante registram o instante da sua
interação; não reproduzem os tratamentos históricos do computador do autor.
O identificador do lote depende dos bytes das fontes, inclusive quebras de linha.
Ele pode diferir do lote local preservado sem diferença nos valores conciliados.

## Gerar novamente

```powershell
python .\python\exportar_demo.py
python .\python\test_exportar_demo.py
```

Se Node.js estiver instalado, verifique as regras do simulador:

```powershell
node --test .\python\test_demo_engine.cjs
```

Para conferir antes de publicar:

```powershell
python -m http.server 8766 --directory docs --bind 127.0.0.1
```

Abra `http://127.0.0.1:8766`. Servir por HTTP permite carregar o JSON;
abrir `index.html` por duplo clique não é o fluxo suportado.

## Publicar no GitHub

1. Envie os arquivos ao repositório com `git add`, `git commit` e `git push`.
2. Abra **Settings → Pages** no repositório.
3. Em **Source**, escolha **Deploy from a branch**.
4. Selecione a branch **main** e a pasta **/docs**, depois **Save**.
5. Aguarde a execução de publicação e use a URL informada pelo GitHub.

URL prevista: `https://engvictortech.github.io/pj-financial-operations/`.
Essa URL só fica disponível após ativar o Pages e concluir a publicação.

## Apresentação no README

Depois de verificar a URL pública, acrescente abaixo do subtítulo:

```markdown
**[Abrir demonstração interativa](https://engvictortech.github.io/pj-financial-operations/)** · [Como funciona a versão online](docs/08_demonstracao_online.md)

Explore a fila, confira os pagamentos de origem e experimente o tratamento.
Dados sintéticos; alterações apenas na aba do visitante. A versão Python com SQLite permanece disponível para execução local.
```

## Roteiro de vídeo (60 a 90 segundos)

1. Mostre a fila e explique o objetivo: investigar diferenças de liquidação.
2. Abra o exemplo #304: esperado R$ 19.526,34; pago e saldo aberto R$ 9.763,17.
3. Confira o evento P001581_0 e explique por que pagamento na data prevista não significa quitação integral.
4. Atribua um responsável, inicie a análise e registre evidência e próximo passo, sem inventar a causa.
5. Mostre o histórico e exporte o JSON.
6. Finalize com o repositório, onde estão o motor Python, o SQL e os testes.

Informe no vídeo que é uma simulação com dados sintéticos. Evite apresentar o
encerramento de um caso como recuperação financeira.
