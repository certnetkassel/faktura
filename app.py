import os
import smtplib
import sqlite3
from datetime import datetime, date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, send_file, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash

from werkzeug.utils import secure_filename

from config import DATABASE, SECRET_KEY, UPLOAD_FOLDER, OUTPUT_FOLDER
from database import get_db, init_db

LOGO_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'logos')

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ── Helpers ──

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def get_settings():
    db = get_db()
    s = db.execute("SELECT * FROM settings WHERE id=1").fetchone()
    db.close()
    return s


def generate_doc_nr(prefix, seq_nr):
    """Generate document number in format PREFIX-YYMM### (e.g. RE-2603001)."""
    now = date.today()
    yymm = now.strftime('%y%m')
    return f"{prefix}-{yymm}{seq_nr:03d}"


def fmt_date(d):
    if not d:
        return ''
    try:
        return datetime.strptime(d, '%Y-%m-%d').strftime('%d.%m.%Y')
    except (ValueError, TypeError):
        return d


app.jinja_env.filters['fmt_date'] = fmt_date


# ── Word-Platzhalter-Ersetzung (robust) ──

def _replace_in_paragraph(paragraph, replacements):
    """Ersetzt Platzhalter in einem Absatz – auch wenn Word den Platzhalter
    über mehrere Runs zerrissen hat (z.B. '{{rechnung' + '_nr}}').

    Word teilt Platzhalter beim Bearbeiten oft auf mehrere Runs auf. Eine
    Ersetzung pro Run (key in run.text) scheitert dann. Daher wird der
    komplette Absatztext zusammengesetzt, ersetzt und – nur wenn sich etwas
    geändert hat – in den ersten Run geschrieben; die übrigen Runs werden
    geleert. Die Formatierung des ersten Runs bleibt erhalten.
    """
    if '{{' not in paragraph.text:
        return
    original = paragraph.text
    new_text = original
    for key, value in replacements.items():
        if key in new_text:
            new_text = new_text.replace(key, value if value is not None else '')
    if new_text == original:
        return
    if paragraph.runs:
        paragraph.runs[0].text = new_text
        for run in paragraph.runs[1:]:
            run.text = ''
    else:
        paragraph.text = new_text


def _replace_in_tables(tables, replacements):
    """Ersetzt Platzhalter in allen Tabellenzellen, rekursiv (verschachtelte Tabellen)."""
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _replace_in_paragraph(paragraph, replacements)
                if cell.tables:
                    _replace_in_tables(cell.tables, replacements)


def replace_placeholders(doc, replacements):
    """Ersetzt alle Platzhalter im gesamten Dokument: Body, Tabellen sowie
    Kopf- und Fußzeilen aller Abschnitte (inkl. First-Page/Even-Page)."""
    for paragraph in doc.paragraphs:
        _replace_in_paragraph(paragraph, replacements)
    _replace_in_tables(doc.tables, replacements)
    for section in doc.sections:
        for hf in (section.header, section.first_page_header, section.even_page_header,
                   section.footer, section.first_page_footer, section.even_page_footer):
            for paragraph in hf.paragraphs:
                _replace_in_paragraph(paragraph, replacements)
            _replace_in_tables(hf.tables, replacements)


LOGO_PLACEHOLDER = '{{logo}}'
LOGO_WIDTH_CM = 4.0  # Breite des eingefügten Logos im Dokument


def _insert_logo_in_paragraph(paragraph, image_path, width):
    """Ersetzt den Marker {{logo}} in einem Absatz durch ein Inline-Bild.
    Funktioniert auch run-übergreifend (Word zerreißt Marker beim Bearbeiten).
    Reihenfolge Text-vor-Marker / Bild / Text-nach-Marker bleibt erhalten."""
    if LOGO_PLACEHOLDER not in paragraph.text:
        return
    if not paragraph.runs:
        return
    before, _, after = paragraph.text.partition(LOGO_PLACEHOLDER)
    run = paragraph.runs[0]
    run.text = before
    for r in paragraph.runs[1:]:
        r.text = ''
    run.add_picture(image_path, width=width)
    if after:
        run.add_text(after)


def _insert_logo_in_tables(tables, image_path, width):
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _insert_logo_in_paragraph(paragraph, image_path, width)
                if cell.tables:
                    _insert_logo_in_tables(cell.tables, image_path, width)


def insert_logo(doc, image_path, width_cm=LOGO_WIDTH_CM):
    """Fügt das Logo überall dort ein, wo der Marker {{logo}} steht –
    Body, Tabellen sowie Kopf-/Fußzeilen aller Abschnitte."""
    from docx.shared import Cm
    width = Cm(width_cm)
    for paragraph in doc.paragraphs:
        _insert_logo_in_paragraph(paragraph, image_path, width)
    _insert_logo_in_tables(doc.tables, image_path, width)
    for section in doc.sections:
        for hf in (section.header, section.first_page_header, section.even_page_header,
                   section.footer, section.first_page_footer, section.even_page_footer):
            for paragraph in hf.paragraphs:
                _insert_logo_in_paragraph(paragraph, image_path, width)
            _insert_logo_in_tables(hf.tables, image_path, width)


def get_logo_path(s, prefer='light'):
    """Liefert den Dateipfad des hinterlegten Logos (Dokumente: helle Variante
    für weißen Hintergrund), oder None wenn keins existiert."""
    order = ['logo_light', 'logo_dark'] if prefer == 'light' else ['logo_dark', 'logo_light']
    for field in order:
        name = s[field] if s[field] else ''
        if name:
            path = os.path.join(LOGO_FOLDER, name)
            if os.path.exists(path):
                return path
    return None


@app.context_processor
def inject_settings():
    """Make settings available in all templates (for logo display)."""
    try:
        s = get_settings()
        return {'settings': s}
    except Exception:
        return {'settings': {}}


# ── Auth ──

@app.route('/login', methods=['GET', 'POST'])
def login():
    s = get_settings()
    if not s['password_hash']:
        # First run: set password
        if request.method == 'POST':
            pw = request.form.get('password', '')
            if len(pw) < 4:
                flash('Passwort muss mindestens 4 Zeichen haben.', 'error')
                return render_template('login.html')
            db = get_db()
            db.execute("UPDATE settings SET password_hash=? WHERE id=1",
                       [generate_password_hash(pw)])
            db.commit()
            db.close()
            session['logged_in'] = True
            flash('Passwort gesetzt. Willkommen!', 'success')
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    if request.method == 'POST':
        pw = request.form.get('password', '')
        if check_password_hash(s['password_hash'], pw):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('Falsches Passwort.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


# ── Dashboard ──

@app.route('/')
@login_required
def dashboard():
    db = get_db()
    today = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()

    stats = {
        'customers': db.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
        'open_invoices': db.execute(
            "SELECT COUNT(*) FROM invoices WHERE status IN ('Gesendet','Überfällig')").fetchone()[0],
        'overdue_invoices': db.execute(
            "SELECT COUNT(*) FROM invoices WHERE status='Überfällig' OR (status='Gesendet' AND due_date < ?)",
            [today]).fetchone()[0],
        'monthly_revenue': db.execute(
            "SELECT COALESCE(SUM(total),0) FROM invoices WHERE status='Bezahlt' AND date >= ?",
            [month_start]).fetchone()[0],
    }

    # Update overdue status
    db.execute(
        "UPDATE invoices SET status='Überfällig' WHERE status='Gesendet' AND due_date < ?",
        [today])
    db.commit()

    open_invoices = db.execute('''
        SELECT i.*, c.last_name, c.company FROM invoices i
        JOIN customers c ON i.customer_id=c.id
        WHERE i.status IN ('Gesendet','Überfällig')
        ORDER BY i.due_date ASC LIMIT 10
    ''').fetchall()

    # Recent items
    recent_items = []
    for inv in db.execute(
            "SELECT i.*, c.last_name FROM invoices i JOIN customers c ON i.customer_id=c.id ORDER BY i.created_at DESC LIMIT 5").fetchall():
        recent_items.append({'type': 'Rechnung', 'badge': 'blue', 'nr': inv['invoice_nr'],
                             'customer': inv['last_name'], 'date': fmt_date(inv['date'])})
    for off in db.execute(
            "SELECT o.*, c.last_name FROM offers o JOIN customers c ON o.customer_id=c.id ORDER BY o.created_at DESC LIMIT 5").fetchall():
        recent_items.append({'type': 'Angebot', 'badge': 'green', 'nr': off['offer_nr'],
                             'customer': off['last_name'], 'date': fmt_date(off['date'])})
    recent_items.sort(key=lambda x: x['date'], reverse=True)

    db.close()
    return render_template('dashboard.html', stats=stats, open_invoices=open_invoices,
                           recent_items=recent_items[:10])


# ── Settings ──

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        db = get_db()
        fields = ['company_name', 'owner_name', 'street', 'zip', 'city', 'phone', 'email',
                  'tax_number', 'bank_name', 'iban', 'bic', 'smtp_host', 'smtp_port',
                  'smtp_user', 'smtp_pass', 'smtp_from', 'kleinunternehmer_text',
                  'invoice_prefix', 'offer_prefix', 'credit_prefix',
                  'next_invoice_nr', 'next_offer_nr', 'next_credit_nr']
        vals = {}
        for f in fields:
            vals[f] = request.form.get(f, '')
        sets = ', '.join(f"{f}=?" for f in fields)
        db.execute(f"UPDATE settings SET {sets} WHERE id=1", list(vals.values()))

        # Handle logo uploads
        os.makedirs(LOGO_FOLDER, exist_ok=True)
        for logo_field in ['logo_dark', 'logo_light']:
            file = request.files.get(logo_field)
            if file and file.filename:
                filename = secure_filename(f"{logo_field}_{file.filename}")
                file.save(os.path.join(LOGO_FOLDER, filename))
                db.execute(f"UPDATE settings SET {logo_field}=? WHERE id=1", [filename])

        new_pw = request.form.get('new_password', '')
        if new_pw:
            db.execute("UPDATE settings SET password_hash=? WHERE id=1",
                       [generate_password_hash(new_pw)])
        db.commit()
        db.close()
        flash('Einstellungen gespeichert.', 'success')
        return redirect(url_for('settings'))

    s = get_settings()
    return render_template('settings.html', s=s)


# ── Customers ──

@app.route('/customers')
@login_required
def customers():
    db = get_db()
    custs = db.execute("SELECT * FROM customers ORDER BY last_name").fetchall()
    db.close()
    return render_template('customers.html', customers=custs)


@app.route('/customers/new', methods=['GET', 'POST'])
@login_required
def customer_form():
    if request.method == 'POST':
        db = get_db()
        nr = request.form['customer_nr']
        db.execute('''INSERT INTO customers (customer_nr, company, salutation, first_name, last_name,
                      street, zip, city, email, phone, notes)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                   [nr, request.form.get('company',''), request.form.get('salutation',''),
                    request.form.get('first_name',''), request.form['last_name'],
                    request.form.get('street',''), request.form.get('zip',''),
                    request.form.get('city',''), request.form.get('email',''),
                    request.form.get('phone',''), request.form.get('notes','')])
        db.commit()
        db.close()
        flash('Kunde angelegt.', 'success')
        return redirect(url_for('customers'))
    # Generate next customer nr
    db = get_db()
    last = db.execute("SELECT customer_nr FROM customers ORDER BY id DESC LIMIT 1").fetchone()
    next_nr = 'K-0001'
    if last:
        try:
            num = int(last['customer_nr'].split('-')[1]) + 1
            next_nr = f"K-{num:04d}"
        except (ValueError, IndexError):
            pass
    db.close()
    return render_template('customer_form.html', c=None, next_nr=next_nr)


@app.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def customer_edit(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('''UPDATE customers SET customer_nr=?, company=?, salutation=?, first_name=?,
                      last_name=?, street=?, zip=?, city=?, email=?, phone=?, notes=? WHERE id=?''',
                   [request.form['customer_nr'], request.form.get('company',''),
                    request.form.get('salutation',''), request.form.get('first_name',''),
                    request.form['last_name'], request.form.get('street',''),
                    request.form.get('zip',''), request.form.get('city',''),
                    request.form.get('email',''), request.form.get('phone',''),
                    request.form.get('notes',''), id])
        db.commit()
        db.close()
        flash('Kunde aktualisiert.', 'success')
        return redirect(url_for('customers'))
    c = db.execute("SELECT * FROM customers WHERE id=?", [id]).fetchone()
    db.close()
    return render_template('customer_form.html', c=c, next_nr=None)


@app.route('/customers/<int:id>/delete', methods=['POST'])
@login_required
def customer_delete(id):
    db = get_db()
    db.execute("DELETE FROM customers WHERE id=?", [id])
    db.commit()
    db.close()
    flash('Kunde gelöscht.', 'success')
    return redirect(url_for('customers'))


# ── Articles ──

@app.route('/articles')
@login_required
def articles():
    db = get_db()
    arts = db.execute("SELECT * FROM articles ORDER BY name").fetchall()
    db.close()
    return render_template('articles.html', articles=arts)


@app.route('/articles/new', methods=['GET', 'POST'])
@login_required
def article_form():
    if request.method == 'POST':
        db = get_db()
        db.execute('''INSERT INTO articles (article_nr, name, description, unit, price)
                      VALUES (?,?,?,?,?)''',
                   [request.form['article_nr'], request.form['name'],
                    request.form.get('description',''), request.form.get('unit','Stunde'),
                    float(request.form.get('price', 0))])
        db.commit()
        db.close()
        flash('Artikel angelegt.', 'success')
        return redirect(url_for('articles'))
    db = get_db()
    last = db.execute("SELECT article_nr FROM articles ORDER BY id DESC LIMIT 1").fetchone()
    next_nr = 'A-0001'
    if last:
        try:
            num = int(last['article_nr'].split('-')[1]) + 1
            next_nr = f"A-{num:04d}"
        except (ValueError, IndexError):
            pass
    db.close()
    return render_template('article_form.html', a=None, next_nr=next_nr)


@app.route('/articles/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def article_edit(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('''UPDATE articles SET article_nr=?, name=?, description=?, unit=?, price=?
                      WHERE id=?''',
                   [request.form['article_nr'], request.form['name'],
                    request.form.get('description',''), request.form.get('unit','Stunde'),
                    float(request.form.get('price', 0)), id])
        db.commit()
        db.close()
        flash('Artikel aktualisiert.', 'success')
        return redirect(url_for('articles'))
    a = db.execute("SELECT * FROM articles WHERE id=?", [id]).fetchone()
    db.close()
    return render_template('article_form.html', a=a, next_nr=None)


@app.route('/articles/<int:id>/delete', methods=['POST'])
@login_required
def article_delete(id):
    db = get_db()
    db.execute("DELETE FROM articles WHERE id=?", [id])
    db.commit()
    db.close()
    flash('Artikel gelöscht.', 'success')
    return redirect(url_for('articles'))


# ── Offers ──

@app.route('/offers')
@login_required
def offers():
    db = get_db()
    offs = db.execute('''SELECT o.*, c.last_name, c.company FROM offers o
                         JOIN customers c ON o.customer_id=c.id ORDER BY o.date DESC''').fetchall()
    db.close()
    return render_template('offers.html', offers=offs)


@app.route('/offers/new', methods=['GET', 'POST'])
@login_required
def offer_form():
    db = get_db()
    if request.method == 'POST':
        s = get_settings()
        offer_nr = generate_doc_nr(s['offer_prefix'], s['next_offer_nr'])
        customer_id = int(request.form['customer_id'])
        offer_date = request.form['date']
        valid_until = request.form.get('valid_until', '')
        notes = request.form.get('notes', '')

        db.execute("INSERT INTO offers (offer_nr,customer_id,date,valid_until,status,notes) VALUES(?,?,?,?,?,?)",
                   [offer_nr, customer_id, offer_date, valid_until, 'Entwurf', notes])
        offer_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        descriptions = request.form.getlist('item_desc')
        quantities = request.form.getlist('item_qty')
        units = request.form.getlist('item_unit')
        prices = request.form.getlist('item_price')

        total = 0
        for i, desc in enumerate(descriptions):
            if not desc.strip():
                continue
            qty = float(quantities[i] or 1)
            price = float(prices[i] or 0)
            item_total = qty * price
            total += item_total
            db.execute('''INSERT INTO offer_items (offer_id,position,description,quantity,unit,price,total)
                          VALUES(?,?,?,?,?,?,?)''',
                       [offer_id, i+1, desc, qty, units[i], price, item_total])

        db.execute("UPDATE offers SET total=? WHERE id=?", [total, offer_id])
        db.execute("UPDATE settings SET next_offer_nr=next_offer_nr+1 WHERE id=1")
        db.commit()
        db.close()
        flash('Angebot erstellt.', 'success')
        return redirect(url_for('offers'))

    customers = db.execute("SELECT * FROM customers ORDER BY last_name").fetchall()
    articles_list = db.execute("SELECT * FROM articles ORDER BY name").fetchall()
    db.close()
    return render_template('offer_form.html', o=None, customers=customers, articles=articles_list, items=[])


@app.route('/offers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def offer_edit(id):
    db = get_db()
    if request.method == 'POST':
        customer_id = int(request.form['customer_id'])
        db.execute("UPDATE offers SET customer_id=?,date=?,valid_until=?,notes=? WHERE id=?",
                   [customer_id, request.form['date'], request.form.get('valid_until',''),
                    request.form.get('notes',''), id])
        db.execute("DELETE FROM offer_items WHERE offer_id=?", [id])

        descriptions = request.form.getlist('item_desc')
        quantities = request.form.getlist('item_qty')
        units = request.form.getlist('item_unit')
        prices = request.form.getlist('item_price')

        total = 0
        for i, desc in enumerate(descriptions):
            if not desc.strip():
                continue
            qty = float(quantities[i] or 1)
            price = float(prices[i] or 0)
            item_total = qty * price
            total += item_total
            db.execute('''INSERT INTO offer_items (offer_id,position,description,quantity,unit,price,total)
                          VALUES(?,?,?,?,?,?,?)''',
                       [id, i+1, desc, qty, units[i], price, item_total])

        db.execute("UPDATE offers SET total=? WHERE id=?", [total, id])
        db.commit()
        db.close()
        flash('Angebot aktualisiert.', 'success')
        return redirect(url_for('offers'))

    o = db.execute("SELECT * FROM offers WHERE id=?", [id]).fetchone()
    items = db.execute("SELECT * FROM offer_items WHERE offer_id=? ORDER BY position", [id]).fetchall()
    customers = db.execute("SELECT * FROM customers ORDER BY last_name").fetchall()
    articles_list = db.execute("SELECT * FROM articles ORDER BY name").fetchall()
    db.close()
    return render_template('offer_form.html', o=o, customers=customers, articles=articles_list, items=items)


@app.route('/offers/<int:id>/delete', methods=['POST'])
@login_required
def offer_delete(id):
    db = get_db()
    db.execute("DELETE FROM offers WHERE id=?", [id])
    db.commit()
    db.close()
    flash('Angebot gelöscht.', 'success')
    return redirect(url_for('offers'))


@app.route('/offers/<int:id>/status/<status>', methods=['POST'])
@login_required
def offer_status(id, status):
    db = get_db()
    db.execute("UPDATE offers SET status=? WHERE id=?", [status, id])
    db.commit()
    db.close()
    flash(f'Status auf "{status}" gesetzt.', 'success')
    return redirect(url_for('offers'))


@app.route('/offers/<int:id>/to-invoice', methods=['POST'])
@login_required
def offer_to_invoice(id):
    db = get_db()
    s = get_settings()
    offer = db.execute("SELECT * FROM offers WHERE id=?", [id]).fetchone()
    items = db.execute("SELECT * FROM offer_items WHERE offer_id=? ORDER BY position", [id]).fetchall()

    invoice_nr = generate_doc_nr(s['invoice_prefix'], s['next_invoice_nr'])
    today = date.today().isoformat()
    due = (date.today() + timedelta(days=14)).isoformat()

    db.execute('''INSERT INTO invoices (invoice_nr,customer_id,offer_id,date,due_date,status,notes,total)
                  VALUES(?,?,?,?,?,?,?,?)''',
               [invoice_nr, offer['customer_id'], id, today, due, 'Entwurf',
                offer['notes'], offer['total']])
    inv_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    for item in items:
        db.execute('''INSERT INTO invoice_items (invoice_id,position,description,quantity,unit,price,total)
                      VALUES(?,?,?,?,?,?,?)''',
                   [inv_id, item['position'], item['description'], item['quantity'],
                    item['unit'], item['price'], item['total']])

    db.execute("UPDATE offers SET status='Angenommen' WHERE id=?", [id])
    db.execute("UPDATE settings SET next_invoice_nr=next_invoice_nr+1 WHERE id=1")
    db.commit()
    db.close()
    flash(f'Rechnung {invoice_nr} aus Angebot erstellt.', 'success')
    return redirect(url_for('invoices'))


# ── Invoices ──

@app.route('/invoices')
@login_required
def invoices():
    db = get_db()
    today = date.today().isoformat()
    db.execute("UPDATE invoices SET status='Überfällig' WHERE status='Gesendet' AND due_date < ?", [today])
    db.commit()
    invs = db.execute('''SELECT i.*, c.last_name, c.company FROM invoices i
                         JOIN customers c ON i.customer_id=c.id ORDER BY i.date DESC''').fetchall()
    db.close()
    return render_template('invoices.html', invoices=invs)


@app.route('/invoices/new', methods=['GET', 'POST'])
@login_required
def invoice_form():
    db = get_db()
    if request.method == 'POST':
        s = get_settings()
        invoice_nr = generate_doc_nr(s['invoice_prefix'], s['next_invoice_nr'])
        customer_id = int(request.form['customer_id'])
        inv_date = request.form['date']
        due_date = request.form['due_date']
        notes = request.form.get('notes', '')

        db.execute('''INSERT INTO invoices (invoice_nr,customer_id,date,due_date,status,notes)
                      VALUES(?,?,?,?,?,?)''',
                   [invoice_nr, customer_id, inv_date, due_date, 'Entwurf', notes])
        inv_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        descriptions = request.form.getlist('item_desc')
        quantities = request.form.getlist('item_qty')
        units = request.form.getlist('item_unit')
        prices = request.form.getlist('item_price')

        total = 0
        for i, desc in enumerate(descriptions):
            if not desc.strip():
                continue
            qty = float(quantities[i] or 1)
            price = float(prices[i] or 0)
            item_total = qty * price
            total += item_total
            db.execute('''INSERT INTO invoice_items (invoice_id,position,description,quantity,unit,price,total)
                          VALUES(?,?,?,?,?,?,?)''',
                       [inv_id, i+1, desc, qty, units[i], price, item_total])

        db.execute("UPDATE invoices SET total=? WHERE id=?", [total, inv_id])
        db.execute("UPDATE settings SET next_invoice_nr=next_invoice_nr+1 WHERE id=1")
        db.commit()
        db.close()
        flash('Rechnung erstellt.', 'success')
        return redirect(url_for('invoices'))

    customers = db.execute("SELECT * FROM customers ORDER BY last_name").fetchall()
    articles_list = db.execute("SELECT * FROM articles ORDER BY name").fetchall()
    db.close()
    today = date.today().isoformat()
    due = (date.today() + timedelta(days=14)).isoformat()
    return render_template('invoice_form.html', inv=None, customers=customers,
                           articles=articles_list, items=[], today=today, due=due)


@app.route('/invoices/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def invoice_edit(id):
    db = get_db()
    if request.method == 'POST':
        db.execute("UPDATE invoices SET customer_id=?,date=?,due_date=?,notes=? WHERE id=?",
                   [int(request.form['customer_id']), request.form['date'],
                    request.form['due_date'], request.form.get('notes',''), id])
        db.execute("DELETE FROM invoice_items WHERE invoice_id=?", [id])

        descriptions = request.form.getlist('item_desc')
        quantities = request.form.getlist('item_qty')
        units = request.form.getlist('item_unit')
        prices = request.form.getlist('item_price')

        total = 0
        for i, desc in enumerate(descriptions):
            if not desc.strip():
                continue
            qty = float(quantities[i] or 1)
            price = float(prices[i] or 0)
            item_total = qty * price
            total += item_total
            db.execute('''INSERT INTO invoice_items (invoice_id,position,description,quantity,unit,price,total)
                          VALUES(?,?,?,?,?,?,?)''',
                       [id, i+1, desc, qty, units[i], price, item_total])

        db.execute("UPDATE invoices SET total=? WHERE id=?", [total, id])
        db.commit()
        db.close()
        flash('Rechnung aktualisiert.', 'success')
        return redirect(url_for('invoices'))

    inv = db.execute("SELECT * FROM invoices WHERE id=?", [id]).fetchone()
    items = db.execute("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY position", [id]).fetchall()
    customers = db.execute("SELECT * FROM customers ORDER BY last_name").fetchall()
    articles_list = db.execute("SELECT * FROM articles ORDER BY name").fetchall()
    db.close()
    return render_template('invoice_form.html', inv=inv, customers=customers,
                           articles=articles_list, items=items, today=None, due=None)


@app.route('/invoices/<int:id>/delete', methods=['POST'])
@login_required
def invoice_delete(id):
    db = get_db()
    db.execute("DELETE FROM invoices WHERE id=?", [id])
    db.commit()
    db.close()
    flash('Rechnung gelöscht.', 'success')
    return redirect(url_for('invoices'))


@app.route('/invoices/<int:id>/status/<status>', methods=['POST'])
@login_required
def invoice_status(id, status):
    db = get_db()
    db.execute("UPDATE invoices SET status=? WHERE id=?", [status, id])
    db.commit()
    db.close()
    flash(f'Status auf "{status}" gesetzt.', 'success')
    return redirect(url_for('invoices'))


# ── Credits ──

@app.route('/credits')
@login_required
def credits_list():
    db = get_db()
    creds = db.execute('''SELECT cr.*, c.last_name, c.company FROM credits cr
                          JOIN customers c ON cr.customer_id=c.id ORDER BY cr.date DESC''').fetchall()
    db.close()
    return render_template('credits.html', credits=creds)


@app.route('/credits/new', methods=['GET', 'POST'])
@login_required
def credit_form():
    db = get_db()
    if request.method == 'POST':
        s = get_settings()
        credit_nr = generate_doc_nr(s['credit_prefix'], s['next_credit_nr'])
        customer_id = int(request.form['customer_id'])
        invoice_id = request.form.get('invoice_id') or None
        cr_date = request.form['date']
        notes = request.form.get('notes', '')

        db.execute('''INSERT INTO credits (credit_nr,customer_id,invoice_id,date,notes)
                      VALUES(?,?,?,?,?)''',
                   [credit_nr, customer_id, invoice_id, cr_date, notes])
        cr_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        descriptions = request.form.getlist('item_desc')
        quantities = request.form.getlist('item_qty')
        units = request.form.getlist('item_unit')
        prices = request.form.getlist('item_price')

        total = 0
        for i, desc in enumerate(descriptions):
            if not desc.strip():
                continue
            qty = float(quantities[i] or 1)
            price = float(prices[i] or 0)
            item_total = qty * price
            total += item_total
            db.execute('''INSERT INTO credit_items (credit_id,position,description,quantity,unit,price,total)
                          VALUES(?,?,?,?,?,?,?)''',
                       [cr_id, i+1, desc, qty, units[i], price, item_total])

        db.execute("UPDATE credits SET total=? WHERE id=?", [total, cr_id])
        db.execute("UPDATE settings SET next_credit_nr=next_credit_nr+1 WHERE id=1")
        db.commit()
        db.close()
        flash('Gutschrift erstellt.', 'success')
        return redirect(url_for('credits_list'))

    customers = db.execute("SELECT * FROM customers ORDER BY last_name").fetchall()
    articles_list = db.execute("SELECT * FROM articles ORDER BY name").fetchall()
    invoices_list = db.execute("SELECT id, invoice_nr FROM invoices ORDER BY date DESC").fetchall()
    db.close()
    return render_template('credit_form.html', cr=None, customers=customers,
                           articles=articles_list, invoices=invoices_list, items=[])


@app.route('/credits/<int:id>/delete', methods=['POST'])
@login_required
def credit_delete(id):
    db = get_db()
    db.execute("DELETE FROM credits WHERE id=?", [id])
    db.commit()
    db.close()
    flash('Gutschrift gelöscht.', 'success')
    return redirect(url_for('credits_list'))


# ── Reminders ──

@app.route('/reminders')
@login_required
def reminders():
    db = get_db()
    rems = db.execute('''SELECT r.*, i.invoice_nr, i.total as inv_total, c.last_name, c.company
                         FROM reminders r
                         JOIN invoices i ON r.invoice_id=i.id
                         JOIN customers c ON i.customer_id=c.id
                         ORDER BY r.date DESC''').fetchall()
    overdue = db.execute('''SELECT i.*, c.last_name, c.company FROM invoices i
                            JOIN customers c ON i.customer_id=c.id
                            WHERE i.status='Überfällig' ORDER BY i.due_date''').fetchall()
    db.close()
    return render_template('reminders.html', reminders=rems, overdue=overdue)


@app.route('/reminders/new/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
def reminder_form(invoice_id):
    db = get_db()
    if request.method == 'POST':
        level = int(request.form.get('level', 1))
        rem_date = request.form['date']
        due_date = request.form['due_date']
        fee = float(request.form.get('fee', 0))
        notes = request.form.get('notes', '')

        db.execute('''INSERT INTO reminders (invoice_id,level,date,due_date,fee,notes)
                      VALUES(?,?,?,?,?,?)''',
                   [invoice_id, level, rem_date, due_date, fee, notes])
        db.commit()
        db.close()
        flash(f'{level}. Mahnung erstellt.', 'success')
        return redirect(url_for('reminders'))

    invoice = db.execute('''SELECT i.*, c.last_name, c.company FROM invoices i
                            JOIN customers c ON i.customer_id=c.id WHERE i.id=?''',
                         [invoice_id]).fetchone()
    last_reminder = db.execute(
        "SELECT MAX(level) as max_level FROM reminders WHERE invoice_id=?",
        [invoice_id]).fetchone()
    next_level = (last_reminder['max_level'] or 0) + 1
    db.close()
    today = date.today().isoformat()
    due = (date.today() + timedelta(days=7)).isoformat()
    return render_template('reminder_form.html', invoice=invoice, level=next_level,
                           today=today, due=due)


@app.route('/reminders/<int:id>/delete', methods=['POST'])
@login_required
def reminder_delete(id):
    db = get_db()
    db.execute("DELETE FROM reminders WHERE id=?", [id])
    db.commit()
    db.close()
    flash('Mahnung gelöscht.', 'success')
    return redirect(url_for('reminders'))


# ── Document Generation (Word) ──

@app.route('/generate/<doc_type>/<int:doc_id>')
@login_required
def generate_doc(doc_type, doc_id):
    try:
        from docx import Document
    except ImportError:
        flash('python-docx ist nicht installiert.', 'error')
        return redirect(url_for('dashboard'))

    template_map = {
        'invoice': 'vorlage_rechnung.docx',
        'offer': 'vorlage_angebot.docx',
        'credit': 'vorlage_gutschrift.docx',
        'reminder': 'vorlage_mahnung.docx',
    }

    template_file = os.path.join(UPLOAD_FOLDER, template_map.get(doc_type, ''))
    if not os.path.exists(template_file):
        flash(f'Vorlage "{template_map.get(doc_type)}" nicht gefunden im Ordner "vorlagen/".', 'error')
        return redirect(url_for('dashboard'))

    db = get_db()
    s = get_settings()

    # Build replacement dict
    replacements = {
        '{{firma}}': s['company_name'],
        '{{inhaber}}': s['owner_name'],
        '{{firma_strasse}}': s['street'],
        '{{firma_plz}}': s['zip'],
        '{{firma_stadt}}': s['city'],
        '{{firma_telefon}}': s['phone'],
        '{{firma_email}}': s['email'],
        '{{steuernummer}}': s['tax_number'],
        '{{bank}}': s['bank_name'],
        '{{iban}}': s['iban'],
        '{{bic}}': s['bic'],
        '{{kleinunternehmer}}': s['kleinunternehmer_text'],
    }

    output_name = ''

    if doc_type == 'invoice':
        inv = db.execute("SELECT * FROM invoices WHERE id=?", [doc_id]).fetchone()
        cust = db.execute("SELECT * FROM customers WHERE id=?", [inv['customer_id']]).fetchone()
        items = db.execute("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY position", [doc_id]).fetchall()
        replacements.update({
            '{{rechnung_nr}}': inv['invoice_nr'],
            '{{rechnung_datum}}': fmt_date(inv['date']),
            '{{faellig_datum}}': fmt_date(inv['due_date']),
            '{{kunde_firma}}': cust['company'],
            '{{kunde_anrede}}': cust['salutation'],
            '{{kunde_vorname}}': cust['first_name'],
            '{{kunde_nachname}}': cust['last_name'],
            '{{kunde_strasse}}': cust['street'],
            '{{kunde_plz}}': cust['zip'],
            '{{kunde_stadt}}': cust['city'],
            '{{kunde_nr}}': cust['customer_nr'],
            '{{kunde_email}}': cust['email'],
            '{{kunde_telefon}}': cust['phone'],
            '{{gesamtbetrag}}': f"{inv['total']:.2f} €",
            '{{notizen}}': inv['notes'] or '',
        })
        output_name = f"{inv['invoice_nr']}.docx"

    elif doc_type == 'offer':
        off = db.execute("SELECT * FROM offers WHERE id=?", [doc_id]).fetchone()
        cust = db.execute("SELECT * FROM customers WHERE id=?", [off['customer_id']]).fetchone()
        items = db.execute("SELECT * FROM offer_items WHERE offer_id=? ORDER BY position", [doc_id]).fetchall()
        replacements.update({
            '{{angebot_nr}}': off['offer_nr'],
            '{{angebot_datum}}': fmt_date(off['date']),
            '{{gueltig_bis}}': fmt_date(off['valid_until']),
            '{{kunde_firma}}': cust['company'],
            '{{kunde_anrede}}': cust['salutation'],
            '{{kunde_vorname}}': cust['first_name'],
            '{{kunde_nachname}}': cust['last_name'],
            '{{kunde_strasse}}': cust['street'],
            '{{kunde_plz}}': cust['zip'],
            '{{kunde_stadt}}': cust['city'],
            '{{kunde_nr}}': cust['customer_nr'],
            '{{kunde_email}}': cust['email'],
            '{{kunde_telefon}}': cust['phone'],
            '{{gesamtbetrag}}': f"{off['total']:.2f} €",
            '{{notizen}}': off['notes'] or '',
        })
        output_name = f"{off['offer_nr']}.docx"

    elif doc_type == 'credit':
        cr = db.execute("SELECT * FROM credits WHERE id=?", [doc_id]).fetchone()
        cust = db.execute("SELECT * FROM customers WHERE id=?", [cr['customer_id']]).fetchone()
        items = db.execute("SELECT * FROM credit_items WHERE credit_id=? ORDER BY position", [doc_id]).fetchall()
        replacements.update({
            '{{gutschrift_nr}}': cr['credit_nr'],
            '{{gutschrift_datum}}': fmt_date(cr['date']),
            '{{kunde_firma}}': cust['company'],
            '{{kunde_anrede}}': cust['salutation'],
            '{{kunde_vorname}}': cust['first_name'],
            '{{kunde_nachname}}': cust['last_name'],
            '{{kunde_strasse}}': cust['street'],
            '{{kunde_plz}}': cust['zip'],
            '{{kunde_stadt}}': cust['city'],
            '{{kunde_nr}}': cust['customer_nr'],
            '{{kunde_email}}': cust['email'],
            '{{kunde_telefon}}': cust['phone'],
            '{{gesamtbetrag}}': f"{cr['total']:.2f} €",
            '{{notizen}}': cr['notes'] or '',
        })
        output_name = f"{cr['credit_nr']}.docx"

    elif doc_type == 'reminder':
        rem = db.execute('''SELECT r.*, i.invoice_nr, i.total as inv_total FROM reminders r
                            JOIN invoices i ON r.invoice_id=i.id WHERE r.id=?''', [doc_id]).fetchone()
        inv = db.execute("SELECT * FROM invoices WHERE id=?", [rem['invoice_id']]).fetchone()
        cust = db.execute("SELECT * FROM customers WHERE id=?", [inv['customer_id']]).fetchone()
        # Positionen der gemahnten Rechnung laden, damit {{positionen}} auch in der Mahnung funktioniert
        items = db.execute("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY position", [rem['invoice_id']]).fetchall()
        replacements.update({
            '{{mahnung_stufe}}': str(rem['level']),
            '{{mahnung_datum}}': fmt_date(rem['date']),
            '{{mahnung_frist}}': fmt_date(rem['due_date']),
            '{{mahngebuehr}}': f"{rem['fee']:.2f} €",
            '{{rechnung_nr}}': inv['invoice_nr'],
            '{{rechnung_datum}}': fmt_date(inv['date']),
            '{{rechnung_faellig_datum}}': fmt_date(inv['due_date']),
            '{{rechnung_betrag}}': f"{inv['total']:.2f} €",
            '{{gesamtbetrag}}': f"{inv['total'] + rem['fee']:.2f} €",
            '{{kunde_firma}}': cust['company'],
            '{{kunde_anrede}}': cust['salutation'],
            '{{kunde_vorname}}': cust['first_name'],
            '{{kunde_nachname}}': cust['last_name'],
            '{{kunde_strasse}}': cust['street'],
            '{{kunde_plz}}': cust['zip'],
            '{{kunde_stadt}}': cust['city'],
            '{{kunde_nr}}': cust['customer_nr'],
            '{{kunde_email}}': cust['email'],
            '{{kunde_telefon}}': cust['phone'],
            '{{notizen}}': rem['notes'] or '',
        })
        output_name = f"Mahnung_{rem['level']}_{inv['invoice_nr']}.docx"

    db.close()

    # Process Word template
    doc = Document(template_file)

    # Platzhalter robust ersetzen (Body, Tabellen, Kopf-/Fußzeilen, run-übergreifend)
    replace_placeholders(doc, replacements)

    # Logo einfügen, wo {{logo}}-Marker steht (helle Variante für weißen Hintergrund);
    # ohne hinterlegtes Logo Marker entfernen, damit kein {{logo}}-Text stehen bleibt
    logo_path = get_logo_path(s, prefer='light')
    if logo_path:
        insert_logo(doc, logo_path)
    else:
        replace_placeholders(doc, {LOGO_PLACEHOLDER: ''})

    # Handle items table — look for {{positionen}} marker
    for table in doc.tables:
        for i, row in enumerate(table.rows):
            for cell in row.cells:
                if '{{positionen}}' in cell.text:
                    # Clear marker
                    cell.text = ''
                    # Add item rows
                    for item in items:
                        new_row = table.add_row()
                        cells = new_row.cells
                        if len(cells) >= 5:
                            cells[0].text = str(item['position'])
                            cells[1].text = item['description']
                            cells[2].text = str(item['quantity'])
                            cells[3].text = item['unit']
                            cells[4].text = f"{item['price']:.2f} €"
                            if len(cells) >= 6:
                                cells[5].text = f"{item['total']:.2f} €"

    output_path = os.path.join(OUTPUT_FOLDER, output_name)
    doc.save(output_path)
    return send_file(output_path, as_attachment=True, download_name=output_name)


# ── Email ──

@app.route('/send-email/<doc_type>/<int:doc_id>', methods=['POST'])
@login_required
def send_email(doc_type, doc_id):
    s = get_settings()
    if not s['smtp_host']:
        flash('SMTP nicht konfiguriert. Bitte in Einstellungen hinterlegen.', 'error')
        return redirect(request.referrer or url_for('dashboard'))

    db = get_db()

    # Determine recipient and subject
    if doc_type == 'invoice':
        doc = db.execute("SELECT * FROM invoices WHERE id=?", [doc_id]).fetchone()
        cust = db.execute("SELECT * FROM customers WHERE id=?", [doc['customer_id']]).fetchone()
        subject = f"Rechnung {doc['invoice_nr']}"
        filename = f"{doc['invoice_nr']}.docx"
    elif doc_type == 'offer':
        doc = db.execute("SELECT * FROM offers WHERE id=?", [doc_id]).fetchone()
        cust = db.execute("SELECT * FROM customers WHERE id=?", [doc['customer_id']]).fetchone()
        subject = f"Angebot {doc['offer_nr']}"
        filename = f"{doc['offer_nr']}.docx"
    elif doc_type == 'credit':
        doc = db.execute("SELECT * FROM credits WHERE id=?", [doc_id]).fetchone()
        cust = db.execute("SELECT * FROM customers WHERE id=?", [doc['customer_id']]).fetchone()
        subject = f"Gutschrift {doc['credit_nr']}"
        filename = f"{doc['credit_nr']}.docx"
    elif doc_type == 'reminder':
        rem = db.execute("SELECT * FROM reminders WHERE id=?", [doc_id]).fetchone()
        inv = db.execute("SELECT * FROM invoices WHERE id=?", [rem['invoice_id']]).fetchone()
        cust = db.execute("SELECT * FROM customers WHERE id=?", [inv['customer_id']]).fetchone()
        subject = f"Zahlungserinnerung zu Rechnung {inv['invoice_nr']}"
        filename = f"Mahnung_{rem['level']}_{inv['invoice_nr']}.docx"
    else:
        flash('Unbekannter Dokumenttyp.', 'error')
        return redirect(url_for('dashboard'))

    recipient = cust['email']
    if not recipient:
        flash('Kunde hat keine E-Mail-Adresse hinterlegt.', 'error')
        db.close()
        return redirect(request.referrer or url_for('dashboard'))

    filepath = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(filepath):
        flash('Dokument nicht gefunden. Bitte zuerst generieren.', 'error')
        db.close()
        return redirect(request.referrer or url_for('dashboard'))

    try:
        msg = MIMEMultipart()
        msg['From'] = s['smtp_from']
        msg['To'] = recipient
        msg['Subject'] = subject

        body = f"Sehr geehrte(r) {cust['salutation']} {cust['last_name']},\n\n"
        body += f"anbei erhalten Sie {subject}.\n\n"
        body += f"Mit freundlichen Grüßen\n{s['owner_name']}\n{s['company_name']}"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with open(filepath, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

        with smtplib.SMTP(s['smtp_host'], int(s['smtp_port'])) as server:
            server.starttls()
            server.login(s['smtp_user'], s['smtp_pass'])
            server.send_message(msg)

        # Log email
        db.execute("INSERT INTO email_log (doc_type,doc_id,recipient,subject) VALUES(?,?,?,?)",
                   [doc_type, doc_id, recipient, subject])

        # Update status if applicable
        if doc_type == 'invoice':
            db.execute("UPDATE invoices SET status='Gesendet' WHERE id=? AND status='Entwurf'", [doc_id])
        elif doc_type == 'offer':
            db.execute("UPDATE offers SET status='Gesendet' WHERE id=? AND status='Entwurf'", [doc_id])

        db.commit()
        flash(f'E-Mail an {recipient} gesendet.', 'success')
    except Exception as e:
        flash(f'E-Mail-Fehler: {str(e)}', 'error')

    db.close()
    return redirect(request.referrer or url_for('dashboard'))


# ── API for article data ──

@app.route('/api/article/<int:id>')
@login_required
def api_article(id):
    db = get_db()
    a = db.execute("SELECT * FROM articles WHERE id=?", [id]).fetchone()
    db.close()
    if a:
        return jsonify({'name': a['name'], 'description': a['description'],
                        'unit': a['unit'], 'price': a['price']})
    return jsonify({}), 404


# ── Init & Run ──


@app.route('/vorlagen/muster/<doc_type>')
@login_required
def vorlage_muster(doc_type):
    try:
        from docx import Document as DocxDocument
    except ImportError:
        flash('python-docx ist nicht installiert.', 'error')
        return redirect(url_for('vorlagen'))

    template_map = {
        'rechnung': 'vorlage_rechnung.docx',
        'angebot': 'vorlage_angebot.docx',
        'gutschrift': 'vorlage_gutschrift.docx',
        'mahnung': 'vorlage_mahnung.docx',
    }
    if doc_type not in template_map:
        flash('Unbekannter Dokumenttyp.', 'error')
        return redirect(url_for('vorlagen'))

    template_file = os.path.join(UPLOAD_FOLDER, template_map[doc_type])
    if not os.path.exists(template_file):
        flash(f'Vorlage "{template_map[doc_type]}" nicht gefunden.', 'error')
        return redirect(url_for('vorlagen'))

    # Beispieldaten
    beispiel = {
        '{{firma}}': 'Dirk Hildebrand - App Entwicklung',
        '{{inhaber}}': 'Dirk Hildebrand',
        '{{firma_strasse}}': 'Hirschbergstr. 4',
        '{{firma_plz}}': '34123',
        '{{firma_stadt}}': 'Kassel',
        '{{firma_telefon}}': '+49 1512 8225666',
        '{{firma_email}}': 'dirk@dirkhildebrand.de',
        '{{steuernummer}}': '026 123 45678',
        '{{bank}}': 'Stadtsparkasse Grebenstein',
        '{{iban}}': 'DE89 3704 0044 0532 0130 00',
        '{{bic}}': 'COBADEFFXXX',
        '{{kleinunternehmer}}': 'Gemäß §19 UStG wird keine Umsatzsteuer berechnet.',
        '{{kunde_firma}}': 'Mustermann GmbH',
        '{{kunde_anrede}}': 'Herr',
        '{{kunde_vorname}}': 'Max',
        '{{kunde_nachname}}': 'Mustermann',
        '{{kunde_strasse}}': 'Beispielweg 42',
        '{{kunde_plz}}': '34117',
        '{{kunde_stadt}}': 'Kassel',
        '{{kunde_nr}}': 'K-0001',
        '{{kunde_email}}': 'max.mustermann@example.com',
        '{{kunde_telefon}}': '+49 561 1234567',
        '{{notizen}}': '',
    }

    if doc_type == 'rechnung':
        beispiel.update({
            '{{rechnung_nr}}': 'RE-2604001',
            '{{rechnung_datum}}': '10.04.2026',
            '{{faellig_datum}}': '24.04.2026',
            '{{gesamtbetrag}}': '2.850,00 €',
        })
        output_name = 'Muster_Rechnung.docx'
    elif doc_type == 'angebot':
        beispiel.update({
            '{{angebot_nr}}': 'AN-2604001',
            '{{angebot_datum}}': '10.04.2026',
            '{{gueltig_bis}}': '10.05.2026',
            '{{gesamtbetrag}}': '2.850,00 €',
        })
        output_name = 'Muster_Angebot.docx'
    elif doc_type == 'gutschrift':
        beispiel.update({
            '{{gutschrift_nr}}': 'GU-2604001',
            '{{gutschrift_datum}}': '10.04.2026',
            '{{gesamtbetrag}}': '500,00 €',
        })
        output_name = 'Muster_Gutschrift.docx'
    elif doc_type == 'mahnung':
        beispiel.update({
            '{{mahnung_stufe}}': '1',
            '{{mahnung_datum}}': '10.04.2026',
            '{{mahnung_frist}}': '17.04.2026',
            '{{mahngebuehr}}': '5,00 €',
            '{{rechnung_nr}}': 'RE-2603001',
            '{{rechnung_datum}}': '01.03.2026',
            '{{rechnung_faellig_datum}}': '15.03.2026',
            '{{rechnung_betrag}}': '1.200,00 €',
            '{{gesamtbetrag}}': '1.205,00 €',
        })
        output_name = 'Muster_Mahnung.docx'

    doc = DocxDocument(template_file)

    # Platzhalter robust ersetzen (Body, Tabellen, Kopf-/Fußzeilen, run-übergreifend)
    replace_placeholders(doc, beispiel)

    # Logo einfügen, wo {{logo}}-Marker steht (helle Variante für weißen Hintergrund);
    # ohne hinterlegtes Logo Marker entfernen, damit kein {{logo}}-Text stehen bleibt
    logo_path = get_logo_path(get_settings(), prefer='light')
    if logo_path:
        insert_logo(doc, logo_path)
    else:
        replace_placeholders(doc, {LOGO_PLACEHOLDER: ''})

    # Positionen einfügen (falls vorhanden)
    if doc_type in ['rechnung', 'angebot', 'gutschrift', 'mahnung']:
        muster_positionen = [
            {'position': 1, 'description': 'Power Apps Entwicklung', 'quantity': 10, 'unit': 'Stunde(n)', 'price': 85.00, 'total': 850.00},
            {'position': 2, 'description': 'Datenbank-Design und Einrichtung', 'quantity': 1, 'unit': 'Pauschale', 'price': 500.00, 'total': 500.00},
            {'position': 3, 'description': 'Monatliche Wartung & Support', 'quantity': 3, 'unit': 'pro Monat', 'price': 500.00, 'total': 1500.00},
        ]
        for table in doc.tables:
            for i, row in enumerate(table.rows):
                for cell in row.cells:
                    if '{{positionen}}' in cell.text:
                        cell.text = ''
                        for item in muster_positionen:
                            new_row = table.add_row()
                            cells = new_row.cells
                            if len(cells) >= 5:
                                cells[0].text = str(item['position'])
                                cells[1].text = item['description']
                                cells[2].text = str(item['quantity'])
                                cells[3].text = item['unit']
                                cells[4].text = f"{item['price']:.2f} €"
                                if len(cells) >= 6:
                                    cells[5].text = f"{item['total']:.2f} €"

    output_path = os.path.join(OUTPUT_FOLDER, output_name)
    doc.save(output_path)
    return send_file(output_path, as_attachment=True, download_name=output_name)

# ── Vorlagen ──

@app.route('/vorlagen')
@login_required
def vorlagen():
    templates = [
        {'label': 'Rechnung', 'filename': 'vorlage_rechnung.docx', 'type': 'rechnung'},
        {'label': 'Angebot', 'filename': 'vorlage_angebot.docx', 'type': 'angebot'},
        {'label': 'Gutschrift', 'filename': 'vorlage_gutschrift.docx', 'type': 'gutschrift'},
        {'label': 'Mahnung', 'filename': 'vorlage_mahnung.docx', 'type': 'mahnung'},
    ]
    for t in templates:
        t['exists'] = os.path.exists(os.path.join(UPLOAD_FOLDER, t['filename']))
    return render_template('vorlagen.html', vorlagen=templates)


@app.route('/vorlagen/download/<filename>')
@login_required
def vorlage_download(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    flash('Vorlage nicht gefunden.', 'error')
    return redirect(url_for('vorlagen'))


@app.route('/vorlagen/upload', methods=['POST'])
@login_required
def vorlage_upload():
    target = request.form.get('target', '')
    allowed = ['vorlage_rechnung.docx', 'vorlage_angebot.docx',
               'vorlage_gutschrift.docx', 'vorlage_mahnung.docx']
    if target not in allowed:
        flash('Ungültiger Dateiname.', 'error')
        return redirect(url_for('vorlagen'))
    file = request.files.get('file')
    if not file or not file.filename.endswith('.docx'):
        flash('Bitte eine .docx-Datei auswählen.', 'error')
        return redirect(url_for('vorlagen'))
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file.save(os.path.join(UPLOAD_FOLDER, target))
    flash(f'Vorlage "{target}" hochgeladen.', 'success')
    return redirect(url_for('vorlagen'))

if __name__ == '__main__':
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
