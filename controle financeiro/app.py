from flask import Flask, render_template, request, redirect, send_file
import sqlite3
from fpdf import FPDF
import io
import tempfile
from datetime import datetime


app = Flask(__name__)
app.secret_key = "segredo123"

def init_db():
    conn = sqlite3.connect("gastos.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transacoes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tipo TEXT,
                  valor REAL,
                  descricao TEXT)''')  # só descrição
    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = sqlite3.connect("gastos.db")
    c = conn.cursor()
    c.execute("SELECT * FROM transacoes")
    transacoes = c.fetchall()

    c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='receita'")
    receitas = c.fetchone()[0] or 0
    c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='despesa'")
    despesas = c.fetchone()[0] or 0

    lucro_bruto = receitas
    lucro_liquido = receitas - despesas

    conn.close()
    return render_template("index.html", transacoes=transacoes,
                           lucro_bruto=lucro_bruto,
                           lucro_liquido=lucro_liquido)

@app.route("/relatorio")
def relatorio():
    conn = sqlite3.connect("gastos.db")
    c = conn.cursor()
    c.execute("SELECT * FROM transacoes")
    transacoes = c.fetchall()

    # Totais gerais
    c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='receita'")
    receitas = c.fetchone()[0] or 0
    c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='despesa'")
    despesas = c.fetchone()[0] or 0

    lucro_bruto = receitas
    lucro_liquido = receitas - despesas

    # Totais por categoria de despesa
    categorias = ["Gasolina", "Ferramentas", "Outros gastos"]
    totais_categorias = {}
    for cat in categorias:
        c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='despesa' AND categoria=?", (cat,))
        totais_categorias[cat] = c.fetchone()[0] or 0

    conn.close()

    return render_template("relatorio.html", transacoes=transacoes,
                           lucro_bruto=lucro_bruto,
                           lucro_liquido=lucro_liquido,
                           totais_categorias=totais_categorias)

@app.route("/adicionar", methods=["GET", "POST"])
def adicionar():
    if request.method == "POST":
        tipo = request.form["tipo"]
        valor = float(request.form["valor"])
        descricao = request.form["descricao"]

        conn = sqlite3.connect("gastos.db")
        c = conn.cursor()
        c.execute("INSERT INTO transacoes (tipo, valor, descricao) VALUES (?, ?, ?)",
                  (tipo, valor, descricao))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("adicionar.html")

@app.route("/exportar_pdf")
def exportar_pdf():
    conn = sqlite3.connect("gastos.db")
    c = conn.cursor()
    c.execute("SELECT * FROM transacoes WHERE tipo='receita'")
    receitas = c.fetchall()
    c.execute("SELECT * FROM transacoes WHERE tipo='despesa'")
    despesas = c.fetchall()

    # Totais
    c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='receita'")
    total_receitas = c.fetchone()[0] or 0
    c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='despesa'")
    total_despesas = c.fetchone()[0] or 0

    lucro_bruto = total_receitas
    diminuicao = total_despesas
    lucro_liquido = total_receitas - total_despesas
    conn.close()

    # Data atual
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Relatório Financeiro", 0, 1, "C")

    # Data logo abaixo do título
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Data: {data_atual}", 0, 1, "C")

    # ------------------ RECEITAS ------------------
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Receitas", 0, 1, "L")

    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(50, 10, "Valor (R$)", 1, 0, "C", fill=True)
    pdf.cell(140, 10, "Descrição", 1, 1, "C", fill=True)

    pdf.set_font("Arial", size=11)
    fill = False
    for r in receitas:
        descricao = r[3] if len(r) > 3 and r[3] else "-"
        pdf.cell(50, 10, f"{r[2]:.2f}", 1, 0, "C", fill=fill)
        pdf.cell(140, 10, descricao, 1, 1, "C", fill=fill)
        fill = not fill

    # ------------------ DESPESAS ------------------
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Despesas", 0, 1, "L")

    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(50, 10, "Valor (R$)", 1, 0, "C", fill=True)
    pdf.cell(140, 10, "Descrição", 1, 1, "C", fill=True)

    pdf.set_font("Arial", size=11)
    fill = False
    for d in despesas:
        descricao = d[3] if len(d) > 3 and d[3] else "-"
        pdf.cell(50, 10, f"{d[2]:.2f}", 1, 0, "C", fill=fill)
        pdf.cell(140, 10, descricao, 1, 1, "C", fill=fill)
        fill = not fill

    # ------------------ RESUMO FINAL ------------------
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Resumo Final", 0, 1, "L")

    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(70, 10, "Item", 1, 0, "C", fill=True)
    pdf.cell(120, 10, "Valor", 1, 1, "C", fill=True)

    pdf.set_font("Arial", size=11)
    pdf.cell(70, 10, "Lucro Bruto", 1, 0, "C")
    pdf.cell(120, 10, f"R$ {lucro_bruto:.2f}", 1, 1, "C")

    pdf.cell(70, 10, "Total de Despesas", 1, 0, "C")
    pdf.cell(120, 10, f"R$ {total_despesas:.2f}", 1, 1, "C")

    pdf.cell(70, 10, "Diminuição", 1, 0, "C")
    pdf.cell(120, 10, f"R$ {diminuicao:.2f}", 1, 1, "C")

    pdf.cell(70, 10, "Lucro Líquido", 1, 0, "C")
    pdf.cell(120, 10, f"R$ {lucro_liquido:.2f}", 1, 1, "C")

    # Salvar em arquivo temporário
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    temp_file.close()

    return send_file(temp_file.name,
                     as_attachment=True,
                     download_name="relatorio.pdf",
                     mimetype="application/pdf")

if __name__ == "__main__":
    init_db()

    app.run(debug=True)
