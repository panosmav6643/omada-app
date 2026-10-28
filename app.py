from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)
app.secret_key = "allaxe_me_ena_polu_dyskolo_kleidi_omada_2025"

DATABASE = "team.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            birth_date TEXT,
            parent_name TEXT,
            parent_phone TEXT,
            parent_email TEXT,
            address TEXT,
            notes TEXT,
            health_allergies TEXT,
            health_conditions TEXT,
            health_medications TEXT,
            health_doctor TEXT,
            health_notes TEXT,
            monthly_fee REAL DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            date TEXT,
            present INTEGER DEFAULT 1,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            amount REAL,
            payment_date TEXT,
            period TEXT,
            method TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    ''')

    conn.commit()
    conn.close()

def send_receipt_email(to_email, child_name, amount, period, payment_date):
    # === ΑΛΛΑΞΕ ΑΥΤΑ ΜΕ ΤΑ ΔΙΚΑ ΣΟΥ ===
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "to_email_sou@gmail.com"
    SENDER_PASSWORD = "xxxx xxxx xxxx xxxx"   # App Password

    subject = f"Απόδειξη πληρωμής - {child_name}"
    body = f"""Αγαπητοί γονείς,

Σας ενημερώνουμε ότι καταχωρήθηκε η πληρωμή για το παιδί σας:

Παιδί: {child_name}
Ποσό: {amount:.2f} €
Περίοδος: {period}
Ημερομηνία πληρωμής: {payment_date}

Ευχαριστούμε πολύ!
Η Ομάδα
"""

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Σφάλμα email:", e)
        return False

@app.route("/")
def index():
    init_db()
    conn = get_db()
    total_members = conn.execute("SELECT COUNT(*) FROM members WHERE active=1").fetchone()[0]
    
    greek_months = {
        "January": "Ιανουάριος", "February": "Φεβρουάριος", "March": "Μάρτιος",
        "April": "Απρίλιος", "May": "Μάιος", "June": "Ιούνιος",
        "July": "Ιούλιος", "August": "Αύγουστος", "September": "Σεπτέμβριος",
        "October": "Οκτώβριος", "November": "Νοέμβριος", "December": "Δεκέμβριος"
    }
    eng = datetime.now().strftime("%B")
    current_period = f"{greek_months.get(eng, eng)} {datetime.now().year}"
    
    unpaid = conn.execute('''
        SELECT COUNT(DISTINCT m.id) 
        FROM members m
        LEFT JOIN payments p ON m.id = p.member_id AND p.period = ?
        WHERE m.active=1 AND p.id IS NULL
    ''', (current_period,)).fetchone()[0]
    conn.close()
    return render_template("index.html", total=total_members, unpaid=unpaid, period=current_period)

@app.route("/members")
def members():
    conn = get_db()
    members = conn.execute("SELECT * FROM members WHERE active=1 ORDER BY last_name, first_name").fetchall()
    conn.close()
    return render_template("members.html", members=members)

@app.route("/member/add", methods=["GET", "POST"])
def add_member():
    if request.method == "POST":
        conn = get_db()
        conn.execute('''
            INSERT INTO members (
                first_name, last_name, birth_date, parent_name, parent_phone, parent_email,
                address, notes, health_allergies, health_conditions, health_medications,
                health_doctor, health_notes, monthly_fee, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            request.form["first_name"],
            request.form["last_name"],
            request.form.get("birth_date"),
            request.form.get("parent_name"),
            request.form.get("parent_phone"),
            request.form.get("parent_email"),
            request.form.get("address"),
            request.form.get("notes"),
            request.form.get("health_allergies"),
            request.form.get("health_conditions"),
            request.form.get("health_medications"),
            request.form.get("health_doctor"),
            request.form.get("health_notes"),
            float(request.form.get("monthly_fee") or 0),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        flash("Το παιδί προστέθηκε επιτυχώς!", "success")
        return redirect(url_for("members"))
    return render_template("member_form.html", member=None)

@app.route("/member/<int:id>")
def member_detail(id):
    conn = get_db()
    member = conn.execute("SELECT * FROM members WHERE id=?", (id,)).fetchone()
    payments = conn.execute("SELECT * FROM payments WHERE member_id=? ORDER BY payment_date DESC", (id,)).fetchall()
    attendance = conn.execute("SELECT * FROM attendance WHERE member_id=? ORDER BY date DESC LIMIT 20", (id,)).fetchall()
    conn.close()
    return render_template("member_detail.html", member=member, payments=payments, attendance=attendance)

@app.route("/member/<int:id>/edit", methods=["GET", "POST"])
def edit_member(id):
    conn = get_db()
    member = conn.execute("SELECT * FROM members WHERE id=?", (id,)).fetchone()
    if request.method == "POST":
        conn.execute('''
            UPDATE members SET
                first_name=?, last_name=?, birth_date=?, parent_name=?, parent_phone=?, parent_email=?,
                address=?, notes=?, health_allergies=?, health_conditions=?, health_medications=?,
                health_doctor=?, health_notes=?, monthly_fee=?
            WHERE id=?
        ''', (
            request.form["first_name"],
            request.form["last_name"],
            request.form.get("birth_date"),
            request.form.get("parent_name"),
            request.form.get("parent_phone"),
            request.form.get("parent_email"),
            request.form.get("address"),
            request.form.get("notes"),
            request.form.get("health_allergies"),
            request.form.get("health_conditions"),
            request.form.get("health_medications"),
            request.form.get("health_doctor"),
            request.form.get("health_notes"),
            float(request.form.get("monthly_fee") or 0),
            id
        ))
        conn.commit()
        conn.close()
        flash("Ενημερώθηκε!", "success")
        return redirect(url_for("member_detail", id=id))
    conn.close()
    return render_template("member_form.html", member=member)

@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    today = date.today().isoformat()
    selected_date = request.args.get("date", today)

    conn = get_db()
    members = conn.execute("SELECT * FROM members WHERE active=1 ORDER BY last_name").fetchall()

    if request.method == "POST":
        selected_date = request.form["date"]
        for member in members:
            present = 1 if request.form.get(f"present_{member['id']}") else 0
            notes = request.form.get(f"notes_{member['id']}", "")
            conn.execute("DELETE FROM attendance WHERE member_id=? AND date=?", (member["id"], selected_date))
            conn.execute("INSERT INTO attendance (member_id, date, present, notes) VALUES (?,?,?,?)",
                         (member["id"], selected_date, present, notes))
        conn.commit()
        flash("Οι παρουσίες αποθηκεύτηκαν!", "success")
        return redirect(url_for("attendance", date=selected_date))

    existing = {}
    rows = conn.execute("SELECT * FROM attendance WHERE date=?", (selected_date,)).fetchall()
    for r in rows:
        existing[r["member_id"]] = r

    conn.close()
    return render_template("attendance.html", members=members, selected_date=selected_date, existing=existing)

@app.route("/payments", methods=["GET", "POST"])
def payments():
    conn = get_db()
    members = conn.execute("SELECT * FROM members WHERE active=1 ORDER BY last_name").fetchall()

    if request.method == "POST":
        member_id = int(request.form["member_id"])
        amount = float(request.form["amount"])
        period = request.form["period"]
        method = request.form.get("method", "Μετρητά")
        notes = request.form.get("notes", "")
        payment_date = request.form.get("payment_date") or date.today().isoformat()

        conn.execute('''
            INSERT INTO payments (member_id, amount, payment_date, period, method, notes)
            VALUES (?,?,?,?,?,?)
        ''', (member_id, amount, payment_date, period, method, notes))
        conn.commit()

        if request.form.get("send_email"):
            member = conn.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
            if member and member["parent_email"]:
                success = send_receipt_email(
                    member["parent_email"],
                    f"{member['first_name']} {member['last_name']}",
                    amount, period, payment_date
                )
                if success:
                    flash("Η πληρωμή καταχωρήθηκε και στάλθηκε email!", "success")
                else:
                    flash("Η πληρωμή καταχωρήθηκε αλλά το email απέτυχε.", "warning")
            else:
                flash("Η πληρωμή καταχωρήθηκε (δεν υπάρχει email γονέα).", "info")
        else:
            flash("Η πληρωμή καταχωρήθηκε!", "success")

        conn.close()
        return redirect(url_for("payments"))

    recent = conn.execute('''
        SELECT p.*, m.first_name, m.last_name 
        FROM payments p 
        JOIN members m ON p.member_id = m.id 
        ORDER BY p.payment_date DESC LIMIT 30
    ''').fetchall()
    conn.close()
    return render_template("payments.html", members=members, recent=recent)

@app.route("/unpaid")
def unpaid():
    greek_months = {
        "January": "Ιανουάριος", "February": "Φεβρουάριος", "March": "Μάρτιος",
        "April": "Απρίλιος", "May": "Μάιος", "June": "Ιούνιος",
        "July": "Ιούλιος", "August": "Αύγουστος", "September": "Σεπτέμβριος",
        "October": "Οκτώβριος", "November": "Νοέμβριος", "December": "Δεκέμβριος"
    }
    eng = datetime.now().strftime("%B")
    current_period = f"{greek_months.get(eng, eng)} {datetime.now().year}"

    conn = get_db()
    unpaid_members = conn.execute('''
        SELECT m.* 
        FROM members m
        LEFT JOIN payments p ON m.id = p.member_id AND p.period = ?
        WHERE m.active = 1 AND p.id IS NULL
        ORDER BY m.last_name
    ''', (current_period,)).fetchall()
    conn.close()
    return render_template("unpaid.html", members=unpaid_members, period=current_period)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
