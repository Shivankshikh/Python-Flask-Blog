import math
import os
from datetime import datetime

from flask import Flask, render_template, request, session, redirect, flash, url_for
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

# create the extension
import json

from werkzeug.utils import secure_filename

with open('config.json',mode='r') as c:
    params=json.load(c)["params"]

app=Flask(__name__)
app.secret_key='secret-key'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = params['uploader_path']
app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
db=SQLAlchemy(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



class Contacts(db.Model):
    contact_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    message = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(12), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    subheading = db.Column(db.String(12), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    img_name=db.Column(db.String(40),nullable=False)

'''backend=flask, front=bootstrap'''
@app.route("/")
def home():
    posts=Posts.query.all()
    # [0:params['no_of_post']]
    last=math.ceil(len(posts)/params['no_of_post'])
    # print(f"Total possible pages {last}")
    page = request.args.get('page')
    # print(f"page value:{page},{str(page)}")
    if(not str(page).isnumeric()):
        page=1
    page=int(page)
    show_posts=posts[(page-1)*params['no_of_post']:(page-1)*params['no_of_post']+params['no_of_post']]
    if page==1:
        prev="#"
        next="/?page="+str(page+1)
    elif page>=last:
        prev="/?page="+str(page-1)
        next="#"
    else:
        prev="/?page=" + str(page + 1)
        next="/?page=" + str(page-1)

    return render_template("index.html",params=params,posts=show_posts,prev=prev,next=next)

@app.route("/about")
def about():
    return render_template("about.html",params=params)

@app.route("/dashboard",methods=["GET","POST"])
def dashboard():
    result = "Hello Admin Portal"
    posts = Posts.query.all()
    if ('user' in session and session['user']==params['admin_user']):
        return render_template("dashboard.html",params=params,posts=posts)
    if request.method=='POST':
        uname=request.form.get('uname')
        password=request.form.get('pass')

        if(uname==params['admin_user'] and password==params['admin_pass']):
            session['user']=uname
            # If admin logged in then show all the existing posts
            return render_template("dashboard.html",params=params,posts=posts)
        else:
            result="Incorrect Username or Password"
            return render_template("login.html", params=params,result=result)
    return render_template("login.html",params=params,result=result)

@app.route("/contact", methods=['GET','POST'])
def contact():
    if request.method== 'POST':
        '''Add entry to the database'''
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(name=name, phone_num = phone, message = message, date= datetime.now(),email = email )
        db.session.add(entry)
        db.session.commit()
        # mail.send_message('New message from ' + name,
        #                   sender=email,
        #                   recipients=params['gmail-user'],
        #                   body="message",
        #                   )
    return render_template("contact.html",params=params)


@app.route("/post/<string:post_slug>",methods=['GET'])
def post_route(post_slug):
    # print("IN POST ROUTE CALL")
    post=Posts.query.filter_by(slug=post_slug).first()
    print(post.title,post.slug,post.img_name)
    return render_template("post.html",params=params,post=post)

@app.route("/delete/<string:post_sno>")
def delete_post(post_sno):
    if ('user' in session and session['user'] == params['admin_user']):
        post = Posts.query.filter_by(sno=post_sno).first()
        db.session.delete(post)
        db.session.commit()
        return redirect("/dashboard")
    else:
        return redirect(('/dashboard'))

@app.route("/edit/<string:post_sno>",methods=['GET','POST'])
def edit_post(post_sno):
    if ('user' in session and session['user'] == params['admin_user']):
        if request.method=='POST':
            box_title = request.form.get('title')
            subheading = request.form.get('subheading')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_name = request.form.get('img_name')
            date = datetime.now()
            if post_sno=='0':
                post=Posts(title=box_title,slug=slug,content=content,subheading=subheading,date=date,img_name=img_name)
                db.session.add(post)
                db.session.commit()
            else:
                post=Posts.query.filter_by(sno=post_sno).first()
                post.title=box_title
                post.subheading=subheading
                post.slug=slug
                post.content=content
                db.session.commit()
                return redirect('/edit/'+post_sno)
        # if it's a get request then we will view the edit.html template with values extracted from post query
        post=Posts.query.filter_by(sno=post_sno).first()
        # if I don't pass sno, for sno=0 there will be no post in db and 'edit/' will be hitted and give error
        return render_template("edit.html",params=params,post=post,sno=post_sno)
    else:
        return redirect('/dashboard')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        # if we don't define enctype="multipart/form-data" in form then it will run on below if loop
        if 'file' not in request.files:
            print('No file part')
            return redirect('/dashboard')
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            print('No selected file')
            return redirect('/dashboard')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print("file received")
            return redirect('/dashboard')
    return redirect(request.url)

@app.route("/logout")
def logout():
    if ('user' in session and session['user'] == params['admin_user']):
        session.pop('user')
    return redirect('/dashboard')

@app.route("/test")
def test():
    # session.pop('user')
    return "TESTING STRING RETURN"

app.run(debug=True)