from flask import Flask, render_template, request, redirect, url_for, flash, abort
import sqlite3, re
import git

app = Flask(__name__)
app.secret_key = "change-me"  # needed for flash messages

DB_PATH = "SU7.sqlite3"

@app.route('/product/<int:id>')
def product(id):

    conn = sqlite3.connect('SU7.sqlite3')
    conn.row_factory = sqlite3.Row  # dict-like access
    cur = conn.cursor()

    row = cur.execute(
        'SELECT id, name, category, description, price, image FROM product WHERE id = ?',
        (id,)
    ).fetchone()
    product = cur.execute(
        "SELECT * FROM product WHERE id != ?",
        (id,)
    ).fetchall()
    all = []
    for i in product:
        p = {
            'id': i[0],
            'name': i[1],
            'category': i[2],
            'description': i[3],
            'price': i[4],
            'image': i[5],
        }
        all.append(p)

    conn.close()

    if row is None:
        return abort(404)

    data = dict(row)  # {'id':..., 'name':..., ...}
    return render_template('detailpage.html', data=data,all=all)
@app.route('/')
@app.route('/getProduct')
def getProduct():
    connection=sqlite3.connect('SU7.sqlite3')
    cursor=connection.cursor()
    product=cursor.execute('SELECT * FROM product').fetchall()
    data=[]
    for i in product:
        p={
            'id': i[0],
            'name': i[1],
            'category': i[2],
            'description': i[3],
            'price': i[4],
            'image': i[5],
        }
        data.append(p)
    return render_template('master.html', data=data)
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
@app.route("/admin/dashboard")
def admin_dashboard():
    conn = get_db()
    stats = {}
    stats["total"] = conn.execute("SELECT COUNT(*) FROM product").fetchone()[0] or 0
    stats["avg_price"] = conn.execute("SELECT COALESCE(AVG(price),0) FROM product").fetchone()[0]
    stats["max_price"] = conn.execute("SELECT COALESCE(MAX(price),0) FROM product").fetchone()[0]
    stats["categories"] = conn.execute("SELECT COUNT(DISTINCT category) FROM product").fetchone()[0] or 0

    # sales by category (fake counts from DB rows)
    cat_rows = conn.execute("""
        SELECT category, COUNT(*) AS cnt
        FROM product
        GROUP BY category
        ORDER BY cnt DESC
    """).fetchall()

    # recent products
    recent = conn.execute("""
        SELECT id, name, category, price, image
        FROM product
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()
    conn.close()

    # build chart data structures (category labels + counts)
    cat_labels = [r["category"] for r in cat_rows]
    cat_counts = [r["cnt"] for r in cat_rows]

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        cat_labels=cat_labels,
        cat_counts=cat_counts,
        recent=recent
    )

@app.route("/admin")
def admin_list():
    conn = get_db()
    rows = conn.execute("SELECT id,name,category,description,price,image FROM product ORDER BY id").fetchall()
    conn.close()
    return render_template("admin_list.html", rows=rows)

# ---------- Admin: Add ----------
@app.route("/admin/add", methods=["GET", "POST"])
def admin_add():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        category = request.form.get("category","").strip()
        description = request.form.get("description","").strip()
        price = request.form.get("price","").strip()
        image = request.form.get("image","").strip()

        # Basic validation
        if not name or not category or not description or not price or not image:
            flash("All fields are required.", "danger")
            return redirect(url_for("admin_add"))

        # Image must be URL (http/https)
        if not re.match(r"^https?://", image):
            flash("Image must be a URL starting with http:// or https://", "warning")
            return redirect(url_for("admin_add"))

        try:
            price_val = float(price)
        except ValueError:
            flash("Price must be a number.", "warning")
            return redirect(url_for("admin_add"))

        conn = get_db()
        conn.execute(
            "INSERT INTO product (name,category,description,price,image) VALUES (?,?,?,?,?)",
            (name, category, description, price_val, image)
        )
        conn.commit()
        conn.close()
        flash("Product added.", "success")
        return redirect(url_for("admin_list"))

    return render_template("admin_form.html", mode="add", item=None)

# ---------- Admin: Edit ----------
@app.route("/admin/edit/<int:pid>", methods=["GET", "POST"])
def admin_edit(pid):
    conn = get_db()
    row = conn.execute("SELECT * FROM product WHERE id = ?", (pid,)).fetchone()
    if row is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        name = request.form.get("name","").strip()
        category = request.form.get("category","").strip()
        description = request.form.get("description","").strip()
        price = request.form.get("price","").strip()
        image = request.form.get("image","").strip()

        if not name or not category or not description or not price or not image:
            flash("All fields are required.", "danger")
            return redirect(url_for("admin_edit", pid=pid))

        if not re.match(r"^https?://", image):
            flash("Image must be a URL starting with http:// or https://", "warning")
            return redirect(url_for("admin_edit", pid=pid))

        try:
            price_val = float(price)
        except ValueError:
            flash("Price must be a number.", "warning")
            return redirect(url_for("admin_edit", pid=pid))

        conn.execute(
            "UPDATE product SET name=?, category=?, description=?, price=?, image=? WHERE id=?",
            (name, category, description, price_val, image, pid)
        )
        conn.commit()
        conn.close()
        flash("Product updated.", "success")
        return redirect(url_for("admin_list"))

    conn.close()
    return render_template("admin_form.html", mode="edit", item=dict(row))

# ---------- Admin: Delete (POST) ----------
@app.route("/admin/delete/<int:pid>", methods=["POST"])
def admin_delete(pid):
    conn = get_db()
    conn.execute("DELETE FROM product WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    flash("Product deleted.", "info")
    return redirect(url_for("admin_list"))

# (Optional) Home route
@app.route("/")
def home():
    return redirect(url_for("admin_list"))

if __name__ == '__main__':
    app.run()
