import os
import uuid
import threading

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename

from extensions import app, db, login_manager
from models import User, Business
from generate_report import generate_and_send_report


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with that email already exists.", "error")
            return redirect(url_for("register"))

        new_user = User(email=email)
        new_user.password = password
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash("Account created!", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    login_user(user)
    flash("Logged in successfully!", "success")
    next_page = request.args.get("next")
    return redirect(next_page or url_for("dashboard"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", businesses=current_user.businesses)


def _is_local_upload(path_or_url):
    """True if this sales_file_path is one of our own saved uploads (not a live link)."""
    return path_or_url.startswith(app.config["UPLOAD_FOLDER"])


def _save_uploaded_file(uploaded_file):
    safe_name = secure_filename(uploaded_file.filename)
    unique_filename = f"{uuid.uuid4()}_{safe_name}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    uploaded_file.save(save_path)
    return save_path


@app.route("/add-business", methods=["POST"])
@login_required
def add_business():
    name = request.form["name"]
    recipient_email = request.form["recipient_email"]
    uploaded_file = request.files.get("file")
    link = request.form.get("link", "").strip()

    if uploaded_file and uploaded_file.filename:
        sales_file_path = _save_uploaded_file(uploaded_file)
    elif link:
        sales_file_path = link
    else:
        flash("Please upload a file or paste a live link.", "error")
        return redirect(url_for("dashboard"))

    business = Business(
        user_id=current_user.id,
        name=name,
        recipient_email=recipient_email,
        sales_file_path=sales_file_path,
    )
    db.session.add(business)
    db.session.commit()

    # Pull plain values out now -- the background thread must NOT touch the
    # SQLAlchemy object itself, since it has no Flask app context of its own.
    business_sales_file_path = business.sales_file_path
    business_recipient_email = business.recipient_email
    business_token = business.unsubscribe_token
    business_id = business.id
    business_name = business.name

    def send_first_report():
        try:
            generate_and_send_report(business_sales_file_path, business_recipient_email, business_token)
        except Exception as e:
            print(f"Failed to send first report for business {business_id} ({business_name}): {e}")

    threading.Thread(target=send_first_report).start()

    flash(f'"{name}" added! Your first report is on its way.', "success")
    return redirect(url_for("dashboard"))


@app.route("/business/<int:business_id>/update", methods=["POST"])
@login_required
def update_business(business_id):
    business = Business.query.get_or_404(business_id)

    # Ownership check -- without this, anyone logged in could update ANY
    # business just by guessing its numeric ID in the URL.
    if business.user_id != current_user.id:
        flash("You don't have permission to update that business.", "error")
        return redirect(url_for("dashboard"))

    uploaded_file = request.files.get("file")
    link = request.form.get("link", "").strip()

    if uploaded_file and uploaded_file.filename:
        old_path = business.sales_file_path
        business.sales_file_path = _save_uploaded_file(uploaded_file)
        if _is_local_upload(old_path) and os.path.exists(old_path):
            os.remove(old_path)
    elif link:
        old_path = business.sales_file_path
        business.sales_file_path = link
        if _is_local_upload(old_path) and os.path.exists(old_path):
            os.remove(old_path)
    else:
        flash("Please upload a file or paste a link to update.", "error")
        return redirect(url_for("dashboard"))

    db.session.commit()
    flash(f'"{business.name}"\'s data source has been updated.', "success")
    return redirect(url_for("dashboard"))


@app.route("/unsubscribe/<token>")
def unsubscribe(token):
    business = Business.query.filter_by(unsubscribe_token=token).first()
    if not business:
        return render_template("unsubscribed.html", found=False)

    business.active = False
    db.session.commit()
    return render_template("unsubscribed.html", found=True, business_name=business.name)


if __name__ == "__main__":
    app.run(debug=True)
