from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///civic_reports.db'
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'your_email@example.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'
app.config['MAIL_USE_TLS'] = True
db = SQLAlchemy(app)
mail = Mail(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    image = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Pending')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    complaints = Complaint.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', complaints=complaints)

@app.route('/submit_complaint', methods=['GET', 'POST'])
def submit_complaint():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        location = request.form['location']
        description = request.form['description']
        image = None
        upload_folder = os.path.join('static', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        if 'image' in request.files:
            img = request.files['image']
            if img and img.filename:
                image = os.path.join(upload_folder, img.filename)
                img.save(image)
        complaint = Complaint(user_id=session['user_id'], location=location, description=description, image=image)
        db.session.add(complaint)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('submit_complaint.html')

@app.route('/admin')
def admin():
    # Simple admin check
    if session.get('user_id') != 1:
        return redirect(url_for('login'))
    complaints = Complaint.query.all()
    return render_template('admin_dashboard.html', complaints=complaints)

@app.route('/update_status/<int:cid>', methods=['POST'])
def update_status(cid):
    complaint = Complaint.query.get(cid)
    complaint.status = request.form['status']
    db.session.commit()
    user = User.query.get(complaint.user_id)
    msg = Message('Complaint Status Updated', sender=app.config['MAIL_USERNAME'], recipients=[user.email])
    msg.body = f"Your complaint status is now: {complaint.status}"
    mail.send(msg)
    return redirect(url_for('admin'))

@app.route('/delete_complaint/<int:cid>', methods=['POST'])
def delete_complaint(cid):
    complaint = Complaint.query.get(cid)
    if complaint:
        # Remove image file if exists
        if complaint.image and os.path.exists(complaint.image):
            os.remove(complaint.image)
        db.session.delete(complaint)
        db.session.commit()
        flash('Complaint deleted successfully.', 'success')
    else:
        flash('Complaint not found.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/edit_complaint/<int:cid>', methods=['GET', 'POST'])
def edit_complaint(cid):
    complaint = Complaint.query.get(cid)
    if not complaint or complaint.user_id != session.get('user_id'):
        flash('Complaint not found or unauthorized.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        location = request.form['location']
        description = request.form['description']
        # Only update image if a new one is uploaded
        upload_folder = os.path.join('static', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        image = complaint.image
        if 'image' in request.files:
            img = request.files['image']
            if img and img.filename:
                image = os.path.join(upload_folder, img.filename)
                img.save(image)
        complaint.location = location
        complaint.description = description
        complaint.image = image
        db.session.commit()
        flash('Complaint updated successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_complaint.html', complaint=complaint)

# Utility function to add a user (e.g., Donald Trump)
def add_special_user():
    if not User.query.filter_by(username='donaldtrump').first():
        user = User(username='donaldtrump', email='donald.trump@example.com', password=generate_password_hash('MakeAmericaClean'))
        db.session.add(user)
        db.session.commit()

# Call this function once at startup
with app.app_context():
    add_special_user()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
