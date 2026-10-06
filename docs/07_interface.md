# Interface de operacoes

A tela principal e uma fila de trabalho: filtrar, priorizar, conferir origem e registrar uma decisao.
Os totais das abas mostram as situacoes no lote selecionado; o contador abaixo mostra o resultado dos filtros.
Os saldos permanecem referenciados ao corte do lote, e nao a data em que a tela foi aberta.

## Integracao

`python/app.py` serve HTML, CSS e JavaScript locais e chama o mesmo motor `operacoes.py`.
Cada requisicao abre sua conexao SQLite. As transicoes, evidencias, eventos e versoes continuam sob as regras do motor.
O servidor escuta somente em 127.0.0.1; usa verificacao de Host/Origin, token por sessao local e politica de conteudo sem recursos externos.
Nomes de analistas sao declarados pelo usuario e nao constituem autenticacao ou garantia de autoria.

## Casos de uso

Atribuir responsavel; iniciar analise; observar; encerrar com conclusao e justificativa;
reabrir com motivo; consultar qualidade do lote; exportar evidencia e historico em JSON.
Pagamentos de origem identificam eventos unicos, duplicatas tecnicas e linhas posteriores ao corte.
Um pagamento sem recebivel exibe o evento do historico de criacao e permanece separado dos totais conciliados.

Em conflito de versao, a acao nao e aplicada. A tela recarrega o caso, mantem o texto digitado e exige
que o usuario escolha explicitamente usar a versao atual antes de tentar salvar novamente.
A exportacao contem evidencias financeiras, eventos, versoes, manifesto e corte. Sao dados sinteticos.

## Atualizacao

`atualizar_interface.py` verifica hashes do motor/esquema, exige um banco existente, usa SQLite Backup API
para copia consistente e substitui apenas os sete arquivos autorizados de interface/teste/documentacao.
Se a substituicao de codigo falhar, tenta restaurar os arquivos anteriores. O banco original nao e substituido.
Feche o servidor e evite novas acoes durante a atualizacao.
O atualizador nao modifica README, dados, SQL ou regras na pasta antiga.

## Limites

Aplicacao local de portfolio com base simulada, sem integracao com bancos ou adquirentes.
Sem login, permissoes por usuario, SLA contratual, prova criptografica de autoria ou infraestrutura de producao.
A protecao de eventos ocorre por regras e triggers no SQLite; quem tem acesso administrativo ao arquivo
pode alterar o banco. Nao ha alegacao de inviolabilidade.
O encerramento da investigacao nao altera o saldo da conciliacao nem prova recebimento de recursos.
