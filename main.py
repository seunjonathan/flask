from turtle import title
from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
#from models import create_post, get_posts
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators   #this is to handle the forms
from passlib.hash import sha256_crypt   #this is for encypting our passwords

app = Flask(__name__)

#Config MysQL
app.config['MYSQL_HOST'] = 'containers-us-west-90.railway.app'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'railway'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'   #by default it returns a tuple, but we want it as dictionary

#init MYSQL

mysql = MySQL(app)



#Articles = Articles()


#Articles
@app.route('/articles')
def articles():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)
    
    cur.close()


#Single Article
@app.route('/article_id/<string:id>/')
def articles_id(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()

    return render_template('article_id.html', article=article)

#Home
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

#Registration Form class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username  = StringField('Username', [validators.Length(min=4, max=25)])
    email  = StringField('Email', [validators.Length(min=6, max=50)])
    password  = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm password')

@app.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

#create cursor
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))
        mysql.connection.commit()
        cur.close()

        flash('You are now registered and can log in', 'success')

        
        return redirect(url_for('index'))


    return render_template('register.html', form=form)


#user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET' and 'logged_in' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0: #if any row is found
            #get a stored hash
            data =  cur.fetchone()
            password = data['password']  #fetching from the dictionary we specified, default was tuple

            #compare passwords
            if sha256_crypt.verify(password_candidate, password):
                app.logger.info('Passowrd Matched')
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))

            else:
                error = 'Invalid login'
                app.logger.info('Wrong Password')
                return render_template('login.html', error=error)
            cur.close()

        else:
            error = 'Username not found'
            app.logger.info('No User')
            return render_template('login.html', error=error)



    return render_template('login.html')

#check if user logged in
from functools import wraps

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')    
            return redirect(url_for('login'))
    return wrap



#logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


#dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)
    
    cur.close()


#Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body  = TextAreaField('Body', [validators.Length(min=20)])

#Add article route
@app.route('/add_article', methods = ['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO articles(title, body,author) VALUES(%s, %s, %s)", (title, body, session['username']))
        mysql.connection.commit()
        cur.close()
        flash('Article Created', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)


#Edit article route
@app.route('/edit_article/<string:id>', methods = ['GET', 'POST'])
@is_logged_in
def edit_article(id):
        cur = mysql.connection.cursor()

        #get article by id
        result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
        article = cur.fetchone()

        #get form
        form = ArticleForm(request.form)

        #populate articlulate from fields
        form.title.data = article['title']
        form.body.data = article['body']

        if request.method == 'POST' and form.validate():
            title = request.form['title']   #update with new data
            body = request.form['body']     #update with new data

            cur = mysql.connection.cursor()

            cur.execute("UPDATE articles SET title=%s, body=%s WHERE id = %s", (title, body, id))
            mysql.connection.commit()
            cur.close()
            flash('Article Updated', 'success')

            return redirect(url_for('dashboard'))

        return render_template('edit_article.html', form=form)


#Delete Article route
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
        cur = mysql.connection.cursor()

        cur.execute("DELETE FROM articles WHERE id = %s", [id])
        mysql.connection.commit()
        cur.close()

        flash('Article Deleted', 'success')

        return redirect(url_for('dashboard'))




if __name__ == '__main__':    #saying if this flie was selected to run, execute whats below, but if it was ref as a library, dont run
    app.secret_key='secret123'
    app.run(debug=True)
