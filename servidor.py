"""Servidor local do CRM demonstrativo, com API JSON e SQLite."""
import argparse
import json
import re
import sqlite3
from contextlib import closing
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STAGES = ("Novo contato", "Qualificação", "Proposta enviada", "Fechado")


def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def initialize(path):
    with closing(connect(path)) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL,
            stage TEXT NOT NULL, date TEXT NOT NULL
        )""")


def validated(data):
    if not isinstance(data, dict) or not all(isinstance(data.get(k), str) for k in ("title", "stage", "date")):
        raise ValueError("Informe título, etapa e data.")
    title, stage, deadline = data["title"].strip(), data["stage"], data["date"]
    if not 1 <= len(title) <= 100 or stage not in STAGES:
        raise ValueError("Título ou etapa inválida.")
    try:
        return title, stage, date.fromisoformat(deadline).isoformat()
    except ValueError:
        raise ValueError("Informe uma data válida.") from None


class CRMHandler(BaseHTTPRequestHandler):
    def send_data(self, status, body, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, value):
        self.send_data(status, json.dumps(value, ensure_ascii=False).encode("utf-8"))

    def dispatch(self):
        port = self.server.server_port
        host = self.headers.get("Host")
        if host not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            return self.send_json(403, {"erro": "Origem local obrigatória."})
        origin = self.headers.get("Origin")
        if self.command != "GET" and origin and origin != f"http://{host}":
            return self.send_json(403, {"erro": "Origem não autorizada."})
        if self.command == "GET" and self.path == "/":
            return self.send_data(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        item = re.fullmatch(r"/api/leads/([1-9][0-9]{0,14})", self.path)
        if self.path != "/api/leads" and not item:
            return self.send_json(404, {"erro": "Rota inexistente."})
        with closing(connect(self.server.db_path)) as db, db:
            if self.command == "GET" and not item:
                rows = db.execute("SELECT * FROM leads ORDER BY date, id").fetchall()
                return self.send_json(200, [dict(row) for row in rows])
            if self.command in {"POST", "PATCH"} and bool(item) == (self.command == "PATCH"):
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if self.headers.get_content_type() != "application/json" or not 0 < length <= 4096:
                        raise ValueError("Envie JSON de até 4 KiB.")
                    values = validated(json.loads(self.rfile.read(length)))
                except (UnicodeError, ValueError) as exc:
                    return self.send_json(400, {"erro": str(exc)})
                if item:
                    lead_id = int(item[1])
                    count = db.execute("UPDATE leads SET title=?, stage=?, date=? WHERE id=?",
                                       (*values, lead_id)).rowcount
                    if not count:
                        return self.send_json(404, {"erro": "Oportunidade não encontrada."})
                else:
                    lead_id = db.execute("INSERT INTO leads(title, stage, date) VALUES (?, ?, ?)", values).lastrowid
                db.commit()
                return self.send_json(200 if item else 201, dict(zip(("id", "title", "stage", "date"), (lead_id, *values))))
            if self.command == "DELETE" and item:
                count = db.execute("DELETE FROM leads WHERE id=?", (int(item[1]),)).rowcount
                db.commit()
                return self.send_json(200 if count else 404, {"excluido": bool(count)})
        self.send_json(405, {"erro": "Método não permitido nesta rota."})

    do_GET = do_POST = do_PATCH = do_DELETE = dispatch


def create_server(db_path, port):
    initialize(db_path)
    server = ThreadingHTTPServer(("127.0.0.1", port), CRMHandler)
    server.db_path = db_path
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--banco", type=Path, default=ROOT / "crm.sqlite3")
    args = parser.parse_args()
    with create_server(args.banco, args.porta) as server:
        print(f"Abra http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
