from flask import request
from datetime import date, datetime
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
import hashlib
import os
import smtplib
from dotenv import load_dotenv
import bleach
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm , CommentForm , RegisterForm , LoginForm

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
ckeditor = CKEditor(app)
Bootstrap5(app)

# Add context processor to make 'now' available in all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# TODO: Configure Flask-Login
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('get_all_posts'))
        return f(*args, **kwargs)
    return decorated_function

# CREATE DATABASE
class Base(DeclarativeBase):
    pass

# Use PostgreSQL on Render, fallback to SQLite for local development
database_url = os.environ.get("DATABASE_URL", "sqlite:///posts.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://")

# Add SSL mode for Render PostgreSQL (avoid duplicate query parameters)
if "postgresql" in database_url and "?" not in database_url:
    database_url = database_url + "?sslmode=require"
elif "postgresql" in database_url and "?" in database_url:
    database_url = database_url + "&sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

db = SQLAlchemy(model_class=Base, engine_options={
    "pool_pre_ping": True, 
    "pool_recycle": 300,
    "connect_args": {"connect_timeout": 10} if "postgresql" in database_url else {}
})
db.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # author: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    author=relationship("User",back_populates="posts")
    comments=relationship("Comment",back_populates="post",cascade="all, delete-orphan")


    # TODO: Create a User table for all your registered users. 
class User(UserMixin,db.Model):
    __tablename__="users"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    name:Mapped[str]=mapped_column(String(250), nullable=False)
    email:Mapped[str]=mapped_column(String(250), nullable=False)
    password:Mapped[str]=mapped_column(String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments=relationship("Comment",back_populates="author")
    def avatar_url(self):
        email_hash = hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s=150"

class Comment(db.Model):
    __tablename__="comments"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    comment:Mapped[str]=mapped_column(Text,nullable=False)
    date:Mapped[str]=mapped_column(String(250), nullable=False)
    author_id:Mapped[int]=mapped_column(Integer,db.ForeignKey("users.id"))
    author=relationship("User",back_populates="comments")
    post_id:Mapped[int]=mapped_column(Integer,db.ForeignKey("blog_posts.id"))
    post=relationship("BlogPost",back_populates="comments")

# Initialize database after models are defined
try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print(f"Database initialization error: {e}")


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register',methods=['GET','POST'])
def register():
    form=RegisterForm()
    if form.validate_on_submit():
        name=form.name.data
        email=form.email.data
        user=db.session.execute(db.select(User).where(User.email==email)).scalar()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        password=generate_password_hash(form.password.data,method='pbkdf2:sha256',salt_length=8)
        new_user=User(
            name=name,
            email=email,
            password=password,
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template("register.html",form=form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login',methods=['GET','POST'])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        email=form.email.data
        password=form.password.data
        user=db.session.execute(db.select(User).where(User.email==email)).scalar()
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        if check_password_hash(user.password,password):
            login_user(user)
            return redirect(url_for('get_all_posts'))
        else:
            flash("Password incorrect, please try again.")
            return redirect(url_for('login'))
    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    page = request.args.get('page', 1, type=int)
    pagination = db.paginate(db.select(BlogPost).order_by(BlogPost.id.desc()), page=page, per_page=5)
    return render_template("index.html", all_posts=pagination.items, pagination=pagination)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>",methods=["GET","POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    form=CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login to comment!")
            return redirect(url_for("login"))
        clean_comment = bleach.clean(form.comment.data, tags=['p', 'strong', 'em', 'a', 'b', 'i', 'u'])
        new_comment=Comment(
            comment=clean_comment,
            date=date.today().strftime("%B %d, %Y"),
            author=current_user,
            post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post", post_id=post_id))
    return render_template("post.html", post=requested_post,form=form)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/delete_comment/<int:comment_id>/<int:post_id>")
def delete_comment(comment_id,post_id):
    if not current_user.is_authenticated:
        flash("You need to login to delete comments.", "danger")
        return redirect(url_for('login'))
    comment_to_delete=db.get_or_404(Comment,comment_id)
    if current_user.id == 1 or current_user.id == comment_to_delete.author_id:
        db.session.delete(comment_to_delete)
        db.session.commit()
        return redirect(url_for('show_post',post_id=post_id))
    flash("You do not have permission to delete this comment.", "danger")
    return redirect(url_for('show_post', post_id=post_id))

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    msg_sent = False
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")
        
        
        email_address = os.environ.get("EMAIL_ADDRESS")
        email_password = os.environ.get("EMAIL_PASSWORD")
        if email_address and email_password:
            try:
                with smtplib.SMTP("smtp.gmail.com", 587) as connection:
                    connection.ehlo()
                    connection.starttls()
                    connection.ehlo()
                    connection.login(email_address, email_password)
                    connection.sendmail(
                        from_addr=email_address,
                        to_addrs=email_address,
                        msg=f"Subject:New Message from {name}\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage: {message}"
                    )
                flash("Successfully sent your message!", "success")
                msg_sent = True
            except Exception as e:
                flash(f"Error sending message: {e}", "danger")
        else:
            flash("Email credentials not configured in .env", "danger")
        return render_template("contact.html", msg_sent=msg_sent)
    return render_template("contact.html", msg_sent=msg_sent)


if __name__ == "__main__":
    app.run(debug=False, port=5002)


# Error handlers for debugging
@app.errorhandler(404)
def not_found(error):
    try:
        return render_template('404.html'), 404
    except:
        return "<h1>404 - Page Not Found</h1>", 404


@app.errorhandler(500)
def internal_error(error):
    try:
        db.session.rollback()
    except:
        pass
    try:
        return render_template('500.html'), 500
    except:
        return "<h1>500 - Internal Server Error</h1>", 500
