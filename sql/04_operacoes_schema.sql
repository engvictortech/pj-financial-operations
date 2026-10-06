-- SQLite. Banco operacional separado da base analítica que pode ser regenerada.
CREATE TABLE IF NOT EXISTS lotes (
    lote_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL UNIQUE,
    corte TEXT NOT NULL,
    regra_versao TEXT NOT NULL,
    importado_em TEXT NOT NULL,
    importado_por TEXT NOT NULL,
    manifesto_json TEXT NOT NULL,
    qualidade_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidencias (
    lote_id TEXT NOT NULL REFERENCES lotes(lote_id),
    recebivel_id TEXT NOT NULL,
    empresa_id TEXT NOT NULL,
    dados_json TEXT NOT NULL,
    PRIMARY KEY(lote_id, recebivel_id)
);
CREATE TABLE IF NOT EXISTS ocorrencias (
    ocorrencia_id INTEGER PRIMARY KEY,
    lote_id TEXT NOT NULL REFERENCES lotes(lote_id),
    referencia TEXT NOT NULL,
    recebivel_id TEXT,
    empresa_id TEXT,
    motivo TEXT NOT NULL CHECK(motivo IN ('PARCIAL','PENDENTE','A_MAIOR','LIQUIDADO_COM_ATRASO','PAGAMENTO_SEM_RECEBIVEL')),
    valor_impacto_centavos INTEGER NOT NULL CHECK(valor_impacto_centavos >= 0),
    idade_dias INTEGER NOT NULL CHECK(idade_dias >= 0),
    prioridade TEXT NOT NULL CHECK(prioridade IN ('P1','P2','P3')),
    status TEXT NOT NULL DEFAULT 'ABERTA' CHECK(status IN ('ABERTA','EM_ANALISE','RESOLVIDA')),
    responsavel TEXT,
    conclusao TEXT,
    justificativa TEXT,
    criada_em TEXT NOT NULL,
    atualizada_em TEXT NOT NULL,
    resolvida_em TEXT,
    versao INTEGER NOT NULL DEFAULT 1 CHECK(versao > 0),
    UNIQUE(lote_id, referencia, motivo),
    FOREIGN KEY(lote_id, recebivel_id) REFERENCES evidencias(lote_id, recebivel_id)
);
CREATE TABLE IF NOT EXISTS eventos (
    evento_id INTEGER PRIMARY KEY,
    ocorrencia_id INTEGER NOT NULL REFERENCES ocorrencias(ocorrencia_id),
    tipo TEXT NOT NULL,
    ator TEXT NOT NULL,
    instante TEXT NOT NULL,
    versao INTEGER NOT NULL,
    detalhes_json TEXT NOT NULL,
    UNIQUE(ocorrencia_id, versao)
);
CREATE INDEX IF NOT EXISTS ix_fila ON ocorrencias(status, prioridade, valor_impacto_centavos DESC);
CREATE INDEX IF NOT EXISTS ix_historico ON eventos(ocorrencia_id, evento_id);
CREATE TRIGGER IF NOT EXISTS eventos_nao_alterar BEFORE UPDATE ON eventos BEGIN
    SELECT RAISE(ABORT, 'Historico nao pode ser alterado');
END;
CREATE TRIGGER IF NOT EXISTS eventos_nao_excluir BEFORE DELETE ON eventos BEGIN
    SELECT RAISE(ABORT, 'Historico nao pode ser excluido');
END;
CREATE TRIGGER IF NOT EXISTS evidencias_nao_alterar BEFORE UPDATE ON evidencias BEGIN
    SELECT RAISE(ABORT, 'Evidencias de origem sao imutaveis');
END;
CREATE TRIGGER IF NOT EXISTS evidencias_nao_excluir BEFORE DELETE ON evidencias BEGIN
    SELECT RAISE(ABORT, 'Evidencias de origem sao imutaveis');
END;
CREATE TRIGGER IF NOT EXISTS lotes_nao_alterar BEFORE UPDATE ON lotes BEGIN
    SELECT RAISE(ABORT, 'Manifesto de origem e imutavel');
END;
CREATE TRIGGER IF NOT EXISTS lotes_nao_excluir BEFORE DELETE ON lotes BEGIN
    SELECT RAISE(ABORT, 'Manifesto de origem e imutavel');
END;
PRAGMA user_version = 1;
