from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import csv
import io
from datetime import date, datetime

app = Flask(__name__)

DB_NAME = "budget.db"

CATEGORIES = [
    "Spesa",
    "Casa",
    "Trasporti",
    "Tabacco",
    "Sanità",
    "Bollette",
    "Sport",
    "Vestiti",
    "Abbonamenti",
    "Cibo fuori",
    "Intrattenimento",
    "Viaggi",
    "Regali",
    "Cultura",
    "Cura personale",
    "Altro extra",
    "Svaghi",
    "Stipendio",
    "Altre entrate"
]

PAYMENT_METHODS = [
    "Bancomat",
    "Carta di credito",
    "Cash",
    "Satispay",
    "Paypal",
    "Cripto"
]

MOVEMENT_TYPES = [
    "Spesa",
    "Entrata"
]


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS movimenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descrizione TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valore REAL NOT NULL,
            data_movimento TEXT NOT NULL,
            metodo_pagamento TEXT NOT NULL,
            note TEXT,
            tipo TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        descrizione = request.form.get("descrizione", "").strip()
        categoria = request.form.get("categoria", "").strip()
        valore_raw = request.form.get("valore", "").strip().replace(",", ".")
        data_movimento = request.form.get("data_movimento", "").strip()
        metodo_pagamento = request.form.get("metodo_pagamento", "").strip()
        note = request.form.get("note", "").strip()
        tipo = request.form.get("tipo", "").strip()

        error = None

        if not descrizione:
            error = "La descrizione è obbligatoria."
        elif categoria not in CATEGORIES:
            error = "Categoria non valida."
        elif metodo_pagamento not in PAYMENT_METHODS:
            error = "Metodo di pagamento non valido."
        elif tipo not in MOVEMENT_TYPES:
            error = "Tipo movimento non valido."
        else:
            try:
                valore = float(valore_raw)
                if valore < 0:
                    error = "Il valore deve essere positivo o zero."
            except ValueError:
                error = "Valore non valido."

        if not data_movimento:
            data_movimento = date.today().isoformat()

        if error is None:
            conn = get_connection()
            conn.execute("""
                INSERT INTO movimenti
                (descrizione, categoria, valore, data_movimento, metodo_pagamento, note, tipo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                descrizione,
                categoria,
                valore,
                data_movimento,
                metodo_pagamento,
                note,
                tipo,
                datetime.now().isoformat(timespec="seconds")
            ))
            conn.commit()
            conn.close()
            return redirect(url_for("index", ok=1))
        else:
            return render_template(
                "index.html",
                movimenti=[],
                categories=CATEGORIES,
                payment_methods=PAYMENT_METHODS,
                movement_types=MOVEMENT_TYPES,
                today=date.today().isoformat(),
                ok=None,
                error=error,
                totale_spese=0,
                totale_entrate=0,
                saldo=0
            )

    conn = get_connection()
    movimenti = conn.execute("""
        SELECT * FROM movimenti
        ORDER BY data_movimento DESC, id DESC
    """).fetchall()

    totale_spese = sum(m["valore"] for m in movimenti if m["tipo"] == "Spesa")
    totale_entrate = sum(m["valore"] for m in movimenti if m["tipo"] == "Entrata")
    saldo = totale_entrate - totale_spese

    conn.close()

    return render_template(
        "index.html",
        movimenti=movimenti,
        categories=CATEGORIES,
        payment_methods=PAYMENT_METHODS,
        movement_types=MOVEMENT_TYPES,
        today=date.today().isoformat(),
        ok=request.args.get("ok"),
        error=None,
        totale_spese=totale_spese,
        totale_entrate=totale_entrate,
        saldo=saldo
    )


@app.route("/delete/<int:movimento_id>", methods=["POST"])
def delete_movimento(movimento_id):
    conn = get_connection()
    conn.execute("DELETE FROM movimenti WHERE id = ?", (movimento_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/export-csv")
def export_csv():
    conn = get_connection()
    movimenti = conn.execute("""
        SELECT descrizione, categoria, valore, data_movimento, metodo_pagamento, note
        FROM movimenti
        ORDER BY data_movimento ASC, id ASC
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "Descrizione",
        "Categoria di spesa / entrata",
        "Valore",
        "Data",
        "Metodo di pagamento",
        "Note"
    ])

    for m in movimenti:
        data_excel = datetime.strptime(m["data_movimento"], "%Y-%m-%d").strftime("%d/%m/%Y")
        writer.writerow([
            m["descrizione"],
            m["categoria"],
            str(m["valore"]).replace(".", ","),
            data_excel,
            m["metodo_pagamento"],
            m["note"] or ""
        ])

    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    output.close()

    return send_file(
        mem,
        mimetype="text/csv",
        as_attachment=True,
        download_name="movimenti_budget.csv"
    )


init_db()

if __name__ == "__main__":
    app.run()
