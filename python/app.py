"""Interface HTTP local usando somente a biblioteca padrão do Python.

Uso: python python/app.py
Escuta apenas em 127.0.0.1; reutiliza o banco e as regras de operacoes.py.
"""
import argparse
import json
import logging
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import operacoes as ops

WEB = ops.ROOT / 'web'
LOG = logging.getLogger('pj.operations')
STATUSES = ('ABERTA', 'EM_ANALISE', 'RESOLVIDA')
REASONS = ('PENDENTE', 'PARCIAL', 'A_MAIOR', 'LIQUIDADO_COM_ATRASO', 'PAGAMENTO_SEM_RECEBIVEL')


class HTTPError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


def lots(db):
    result = []
    for row in db.execute('SELECT * FROM lotes ORDER BY importado_em DESC, rowid DESC'):
        item = dict(row)
        item['qualidade'] = json.loads(item.pop('qualidade_json'))
        item['manifesto'] = json.loads(item.pop('manifesto_json'))
        result.append(item)
    return result


def filters(db, query):
    def value(name, maximum=100):
        values = query.get(name, [''])
        if len(values) != 1 or len(values[0]) > maximum:
            raise HTTPError(400, f'Filtro invalido: {name}')
        return values[0].strip()
    lote = value('lote')
    if not lote:
        row = db.execute('SELECT lote_id FROM lotes ORDER BY importado_em DESC,rowid DESC LIMIT 1').fetchone()
        lote = row[0] if row else ''
    if lote and not db.execute('SELECT 1 FROM lotes WHERE lote_id=?', (lote,)).fetchone():
        raise HTTPError(404, 'Lote nao encontrado.')
    clauses, params = ['lote_id=?'], [lote]
    for field, allowed in [('status', STATUSES), ('prioridade', ('P1', 'P2', 'P3')), ('motivo', REASONS)]:
        v = value(field)
        if v:
            if v not in allowed:
                raise HTTPError(400, f'Filtro invalido: {field}')
            clauses.append(field + '=?')
            params.append(v)
    responsible = value('responsavel')
    if responsible == '--sem--':
        clauses.append('responsavel IS NULL')
    elif responsible:
        clauses.append('responsavel=?')
        params.append(responsible)
    busca = value('busca', 80)
    if busca:
        pattern = '%' + busca.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
        clauses.append("(referencia LIKE ? ESCAPE '!' OR empresa_id LIKE ? ESCAPE '!' OR CAST(ocorrencia_id AS TEXT) LIKE ? ESCAPE '!')")
        params.extend([pattern] * 3)
    try:
        pagina = int(value('pagina') or 1)
        tamanho = int(value('tamanho') or 25)
    except ValueError as exc:
        raise HTTPError(400, 'Paginacao invalida.') from exc
    if not 1 <= pagina <= 100000 or tamanho not in (10, 25, 50):
        raise HTTPError(400, 'Paginacao invalida.')
    return lote, ' AND '.join(clauses), params, pagina, tamanho


def queue(db, query):
    lote, where, params, pagina, tamanho = filters(db, query)
    total = db.execute('SELECT COUNT(*) FROM ocorrencias WHERE ' + where, params).fetchone()[0]
    # Se o filtro mudou, mantenha uma página válida, inclusive para zero resultados.
    paginas = max(1, (total + tamanho - 1) // tamanho)
    pagina = min(pagina, paginas)
    rows = db.execute('''SELECT ocorrencia_id,lote_id,referencia,empresa_id,motivo,prioridade,
                         valor_impacto_centavos,idade_dias,status,responsavel,versao
                         FROM ocorrencias WHERE ''' + where + ''' ORDER BY prioridade,
                         valor_impacto_centavos DESC,idade_dias DESC,ocorrencia_id LIMIT ? OFFSET ?''',
                      params + [tamanho, (pagina - 1) * tamanho]).fetchall()
    summary = {s: 0 for s in STATUSES}
    for row in db.execute('SELECT status,COUNT(*) AS n FROM ocorrencias WHERE lote_id=? GROUP BY status', (lote,)):
        summary[row['status']] = row['n']
    return {'lote_id': lote, 'ocorrencias': [dict(r) for r in rows], 'total': total,
            'pagina': pagina, 'paginas': paginas, 'tamanho': tamanho, 'resumo_lote': summary}


def case_details(db, oid):
    result = ops.detalhe(db, oid)
    lot = db.execute('SELECT lote_id,corte,regra_versao,importado_em,manifesto_json FROM lotes WHERE lote_id=?',
                     (result['ocorrencia']['lote_id'],)).fetchone()
    result['lote'] = dict(lot)
    result['lote']['manifesto'] = json.loads(result['lote'].pop('manifesto_json'))
    return result


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    server_version = 'PJOperations/2.0'

    def log_message(self, fmt, *args):
        LOG.info('%s %s', self.address_string(), fmt % args)

    def guard_origin(self):
        port = self.server.server_port
        allowed_hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host', '') not in allowed_hosts:
            raise HTTPError(403, 'Acesso permitido apenas pelo endereco local da aplicacao.')
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://{host}' for host in allowed_hosts}:
            raise HTTPError(403, 'Origem da requisicao nao permitida.')

    def send(self, status, data, mime='application/json; charset=utf-8', extra=None):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.dispatch(False)

    def do_POST(self):
        self.dispatch(True)

    def dispatch(self, mutation):
        try:
            self.guard_origin()
            parsed = urlsplit(self.path)
            if mutation:
                self.post(parsed.path)
            else:
                self.get(parsed.path, parse_qs(parsed.query, keep_blank_values=True))
        except HTTPError as exc:
            self.send(exc.code, {'erro': exc.message})
        except ops.RegraError as exc:
            message = str(exc)
            code = 409 if message.startswith('Conflito') else 404 if 'nao encontrada' in message else 422
            self.send(code, {'erro': message})
        except sqlite3.Error:
            LOG.exception('Falha de banco')
            self.send(503, {'erro': 'Banco temporariamente indisponivel. Nenhuma acao deve ser presumida concluida; atualize o caso.'})
        except (ValueError, KeyError, TypeError) as exc:
            self.send(400, {'erro': f'Dados invalidos: {exc}'})
        except OSError:
            LOG.exception('Arquivo nao disponivel')
            self.send(500, {'erro': 'Arquivo do projeto indisponivel. Confira a pasta e o terminal.'})

    def get(self, path, query):
        static = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/static/app.css': ('app.css', 'text/css; charset=utf-8'),
                  '/static/app.js': ('app.js', 'text/javascript; charset=utf-8')}
        if path in static:
            name, mime = static[path]
            self.send(200, (WEB / name).read_bytes(), mime)
            return
        if path == '/favicon.ico':
            self.send(204, b'', 'image/x-icon')
            return
        if path == '/api/contexto':
            self.send(200, {'csrf_token': self.server.csrf_token, 'ator': self.server.default_actor,
                            'banco': self.server.dbpath.name, 'natureza': 'DADOS SINTETICOS',
                            'conclusoes': list(ops.CONCLUSOES), 'versao_app': '2.0'})
            return
        with ops.database(self.server.dbpath) as db:
            if path == '/api/lotes':
                result = lots(db)
            elif path == '/api/fila':
                result = queue(db, query)
            elif match := re.fullmatch(r'/api/ocorrencias/(\d+)(/exportar)?', path):
                result = case_details(db, int(match[1]))
                if match[2]:
                    result['exportado_em_utc'] = datetime.now(timezone.utc).isoformat()
                    result['natureza'] = 'DADOS SINTETICOS — PROJETO INDEPENDENTE'
                    self.send(200, json.dumps(result, indent=2, ensure_ascii=False).encode(),
                              extra={'Content-Disposition': f'attachment; filename="ocorrencia_{int(match[1])}.json"'})
                    return
            else:
                raise HTTPError(404, 'Recurso nao encontrado.')
        self.send(200, result)

    def post(self, path):
        token = self.headers.get('X-PJ-Token', '')
        if not secrets.compare_digest(token, self.server.csrf_token):
            raise HTTPError(403, 'Sessao local expirada. Atualize a pagina antes de salvar.')
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            raise HTTPError(415, 'Use um corpo JSON.')
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError as exc:
            raise HTTPError(400, 'Tamanho de requisicao invalido.') from exc
        if not 0 < length <= 32768:
            raise HTTPError(413, 'Requisicao vazia ou muito grande.')
        try:
            data = json.loads(self.rfile.read(length).decode('utf-8'))
        except (ValueError, UnicodeDecodeError) as exc:
            raise HTTPError(400, 'JSON invalido.') from exc
        if not isinstance(data, dict):
            raise HTTPError(400, 'Informe um objeto JSON.')
        actor = ops.texto(data.get('ator'), 'Ator', maximo=100)
        with ops.database(self.server.dbpath) as db:
            if path == '/api/importar':
                result = ops.importar(db, ator=actor)
            elif match := re.fullmatch(r'/api/ocorrencias/(\d+)/acao', path):
                version = data.get('versao')
                if type(version) is not int or version < 1:
                    raise HTTPError(400, 'Informe uma versao inteira positiva.')
                action = data.get('acao')
                if action not in ('atribuir', 'analisar', 'observar', 'resolver', 'reabrir'):
                    raise HTTPError(400, 'Acao invalida.')
                result = ops.tratar(db, int(match[1]), action, actor, version,
                                    responsavel=data.get('responsavel'), nota=data.get('texto'),
                                    conclusao=data.get('conclusao'))
            else:
                raise HTTPError(404, 'Recurso nao encontrado.')
        self.send(200, result)


def create_server(dbpath=ops.DEFAULT_DB, port=8765, actor='Victor'):
    # Inicializa apenas o esquema. Nunca importa, apaga ou reconstroi o banco ao abrir.
    with ops.database(dbpath):
        pass
    server = LocalServer(('127.0.0.1', port), Handler)
    server.dbpath = Path(dbpath)
    server.default_actor = ops.texto(actor, 'Ator', maximo=100)
    server.csrf_token = secrets.token_urlsafe(32)
    return server


def main():
    parser = argparse.ArgumentParser(description='PJ Financial Operations — interface local.')
    parser.add_argument('--db', type=Path, default=ops.DEFAULT_DB)
    parser.add_argument('--porta', type=int, default=8765)
    parser.add_argument('--ator', default='Victor')
    args = parser.parse_args()
    if not 1 <= args.porta <= 65535:
        parser.error('A porta deve estar entre 1 e 65535.')
    logging.basicConfig(level=logging.WARNING)
    try:
        server = create_server(args.db, args.porta, args.ator)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f'Nao foi possivel iniciar: {exc}\nSe a porta estiver ocupada, use --porta 8766.\n')
    print(f'PJ Financial Operations\nAbra http://127.0.0.1:{args.porta}\nBanco: {args.db.resolve()}\nDados simulados. Para encerrar o servidor: Ctrl+C.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor encerrado; banco preservado.')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
