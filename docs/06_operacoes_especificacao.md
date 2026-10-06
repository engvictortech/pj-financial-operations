# PJ Financial Operations — especificação e critérios da etapa 1

## Problema e usuário

Um analista de operações precisa investigar divergências de liquidação, organizar seu trabalho e documentar decisões. Esta etapa oferece um motor reutilizável e uma CLI local para validar as regras. Uma interface de operação será uma etapa posterior; não há dashboard como entrega principal.

## Entidades

| Entidade | Grão / função | Proteção implementada |
|---|---|---|
| lotes | Uma combinação de arquivos, corte e versão de regras | Hash SHA-256 dos bytes efetivamente analisados; conteúdo imutável por triggers |
| evidencias | Um recebível em um lote | Conciliação e linhas de pagamento originais preservadas; update/delete bloqueados |
| ocorrencias | Uma referência e um motivo em um lote | Chave única; status, responsável, versão e conclusão |
| eventos | Uma mudança em uma ocorrência | Ator, instante UTC, versão e detalhes; update/delete bloqueados |

Uma importação repetida dos mesmos bytes com a mesma versão das regras retorna o lote existente e não recria ocorrências. Arquivos diferentes (incluindo diferença de formatação), corte diferente ou regras diferentes produzem outro lote. Nesta primeira etapa não há sincronização automática de tratamentos entre lotes; eles representam avaliações separadas. A fila lista os casos importados, e a consulta de detalhes informa o lote de origem. Não some versões de uma mesma carteira como se fossem obrigações distintas.

## Importação

1. Capturar os bytes de cada fonte uma vez e calcular o manifesto.
2. Validar IDs únicos, vínculos com empresas, datas, valores e integridade dos arquivos.
3. Reexecutar a conciliação a partir das fontes e comparar todas as linhas com o CSV processado.
4. Conferir os totais e o relatório de qualidade.
5. Inserir lote, evidências, ocorrências e eventos em uma transação única.

Uma falha de validação não cria lote. Uma falha durante a gravação reverte toda a importação. Mesmo ID de pagamento com conteúdos diferentes dentro do corte bloqueia a conciliação, sem escolher silenciosamente uma versão.

## Tipos de ocorrência

| Motivo | Quantidade nesta base | Valor de impacto |
|---|---:|---|
| PARCIAL | 585 | Saldo que falta no corte |
| PENDENTE | 591 | Valor esperado ainda não liquidado no corte |
| A_MAIOR | 585 | Excesso recebido |
| LIQUIDADO_COM_ATRASO | 586 | Zero de saldo residual; ocorrência de pontualidade |
| PAGAMENTO_SEM_RECEBIVEL | 1 | Valor do evento sem vínculo, separado dos saldos conciliados |
| **Total** | **2.348** | Não é um total de perda ou inadimplência |

Os 273 recebíveis a vencer e os 9.380 conciliados no prazo não geram casos de divergência. As 586 duplicatas técnicas são contabilizadas no controle da importação, sem virar outros 586 pagamentos/casos. Os 293 registros posteriores ao corte ficam fora dos totais conciliados.

## Priorização didática, versão ops-1.0

| Prioridade | Regra |
|---|---|
| P1 | Valor de impacto >= R$ 10.000,00 OU idade >= 180 dias |
| P2 | Valor >= R$ 1.000,00 OU idade >= 30 dias, quando não é P1 |
| P3 | Demais casos |

Pagamento sem recebível é P2 por regra específica de rastreabilidade. Para parcial/pendente/excesso, idade é a do saldo aberto; excesso tem idade zero nesta base. Para liquidado com atraso, idade é a diferença entre última liquidação e data prevista. Ordenação: prioridade, maior impacto, maior idade e ID para desempate.

Esses limites foram escolhidos para a demonstração, não extraídos de políticas do Sofisa, SLA de adquirentes ou norma. Uma operação real teria critérios validados com os responsáveis e capacidade da equipe.

## Fluxo de tratamento

ABERTA → EM_ANALISE → RESOLVIDA. RESOLVIDA pode voltar para EM_ANALISE mediante justificativa de reabertura.

- Para iniciar análise, precisa haver responsável.
- Para encerrar, precisa estar EM_ANALISE, ter conclusão permitida e justificativa de pelo menos 20 caracteres.
- Observações são registradas em eventos; não substituem as anteriores.
- Uma atualização informa a versão lida; se outra ação mudou a versão, a gravação é rejeitada. Isso evita sobrescrever trabalho que o operador ainda não revisou.
- Mudança de estado e registro do evento são atômicos: ou ambos são gravados, ou nenhum.
- Conclusão permitida: ANALISE_CONCLUIDA, SEM_DIVERGENCIA_APOS_REVISAO ou TRATAMENTO_EXTERNO_DOCUMENTADO. Nenhuma conclui automaticamente que houve quitação.
- A resolução/reabertura não altera os valores financeiros, evidências ou classificação da conciliação. Uma nova situação financeira precisará de outra fonte/snapshot e análise própria.

## Qualidade verificada

13 testes de aceitação cobrem quantidades conhecidas, reimportação, rastreabilidade, órfão, fluxo completo, justificativa, transições inválidas, concorrência de versões, proteção de histórico/evidências, adulteração do CSV processado, rollback de atualização/importação e limites de prioridade.

O banco usa integridade referencial, transações e controles do aplicativo. Os nomes de atores são informados pelo usuário local, sem autenticação; não provam identidade. Triggers protegem contra alterações pelas rotas normais, mas não constituem evidência inviolável contra quem administra o arquivo SQLite. Esta é uma demonstração de portfólio, sem integração com registradoras, contas bancárias ou comunicações externas.

## Próximas etapas

1. Desenhar uma tela de fila e uma tela de investigação, usando o motor validado.
2. Conectar ações de atribuição, observação, resolução e reabertura.
3. Incluir filtro por lote e tratamento de erros/conflitos na interface.
4. Construir importação assistida e registro de documentos de investigação.
5. Preparar homologação e um estudo de caso rastreável para entrevista.

Aplicação pretendida: uso local no Windows, operada por um analista; interface clara, tabelas legíveis, tipografia neutra e ênfase na origem dos valores e nas ações. Sem marcas de bancos, aparência de produto oficial, resultados financeiros inventados ou excesso de cartões decorativos.
