from app import app, db
from flask import render_template, url_for, redirect, flash, request, jsonify
from app.forms import TitleForm, PostForm, LoginForm, RegisterForm, ContactForm
from app.models import Post, User
from flask_login import current_user, login_user, logout_user, login_required
from app.email import send_email
import stripe

stripe.api_key = app.config['STRIPE_SECRET_KEY']



@app.route('/')
@app.route('/index')
@app.route('/index/<header>', methods=['GET'])
def index(header=''):
    products = [
        {
            'id': 1001,
            'title': 'Soap',
            'price': 3.98,
            'desc': 'Very clean soapy soap, descriptive text'
        },
        {
            'id': 1002,
            'title': 'Grapes',
            'price': 4.56,
            'desc': 'A bundle of grapey grapes, yummy'
        },
        {
            'id': 1003,
            'title': 'Pickles',
            'price': 5.67,
            'desc': 'A jar of pickles is pickly'
        },
        {
            'id': 1004,
            'title': 'Juice',
            'price': 2.68,
            'desc': 'Yummy orange juice'
        }
    ]

    return render_template('index.html', header=header, products=products, title='Home')


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    return render_template('checkout.html', title='Checkout')

@app.route('/pay', methods=['GET', 'POST'])
def pay():
    amount = request.args.get('amount')
    email = request.form['stripeEmail']
    customer = stripe.Customer.create(
        email=email,
        source=request.form['stripeToken']
    )

    charge = stripe.Charge.create(
        customer=customer.id,
        amount=amount,
        currency='usd',
        description='This was a test purchase.'
    )

    return redirect(url_for('thanks', amount=amount, email=email))

@app.route('/thanks/<amount>/<email>', methods=['GET'])
def thanks(amount, email):
    amount = int(amount) / 100
    return render_template('thanks.html', amount=amount, email=email, title='Thanks')

@login_required
@app.route('/posts/<username>', methods=['GET', 'POST'])
def posts(username):
    form = PostForm()

    # query database for proper person
    person = User.query.filter_by(username=username).first()

    # when form is submitted append to posts list, re-render posts page
    if form.validate_on_submit():
        tweet = form.tweet.data
        post = Post(tweet=tweet, user_id=current_user.id)

        # add post variable to database stage, then commit
        db.session.add(post)
        db.session.commit()

        return redirect(url_for('posts', username=username))

    return render_template('posts.html', person=person, title='Posts', form=form, username=username)


@app.route('/title', methods=['GET', 'POST'])
def title():
    form = TitleForm()

    # when form is submitted, redirect to home page, and pass title to change what the h1 tag says
    if form.validate_on_submit():
        header = form.title.data
        return redirect(url_for('index', header=header))

    return render_template('title.html', title='Title', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # if user is logged in already, do not let them access this page
    if current_user.is_authenticated:
        flash('You are already logged in!')
        return redirect(url_for('index'))

    form = LoginForm()

    # check if form is submitted, log user in if so
    if form.validate_on_submit():
        # query the database for the user trying to log in
        user = User.query.filter_by(username=form.username.data).first()

        # if user doesn't exist, reload page and flash message
        if user is None or not user.check_password(form.password.data):
            flash('Credentials are incorrect.')
            return redirect(url_for('login'))

        # if user does exist, and credentials are correct, log them in and send them to their profile page
        login_user(user, remember=form.remember_me.data)
        flash('You are now logged in!')
        return redirect(url_for('posts', username=current_user.username))


    return render_template('login.html', title='Login', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    # if user is logged in already, do not let them access this page
    if current_user.is_authenticated:
        flash('You are already logged in!')
        return redirect(url_for('index'))

    form = RegisterForm()

    if form.validate_on_submit():
        user = User(
            first_name = form.first_name.data,
            last_name = form.last_name.data,
            username = form.username.data,
            email = form.email.data,
            url = form.url.data,
            age = form.age.data,
            bio = form.bio.data
        )

        # set the password hash
        user.set_password(form.password.data)

        # add to stage and commit to db, then flash and return
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now registered!')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)



@app.route('/api/posts/', methods=['GET'])
def api():
    ####################################
    # for retrieving posts by a user
    ####################################
    try:
        username = request.args.get('username')
        user = User.query.filter_by(username=username).first()

        posts = Post.query.filter_by(user_id=user.id).all()

        data = {
            username: []
        }

        tweets = []

        for post in posts:
            tweets.append({
                'date_posted': str(post.date_posted.date()),
                'tweet' : post.tweet
            })

        data[username] = tweets

        return jsonify(data)

    except:
        return jsonify({
            'error #001': 'Incorrect Username'
        })


@app.route('/api/tweet/', methods=['GET', 'POST'])
def api_tweet():
    try:
        tweet = request.args.get('post')
        username = request.args.get('username')
        p = request.args.get('p')

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(p):
            return jsonify({ 'error #002': 'incorrect credentials'})

        # user credentials right, post to database and save
        post = Post(tweet=tweet, user_id=user.id)
        db.session.add(post)
        db.session.commit()

        return jsonify({ 'success': 'posted correctly for {}'.format(username)})

    except:
        return jsonify({ 'error #003': 'incorrect parameters'})


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()

    if form.validate_on_submit():
        send_email(
            subject = 'Contact Form',
            sender = 'cmilliken09@gmail.com',
            recipients = [form.email.data],
            text_body = render_template('email/contact_form.txt',
                name = form.name.data,
                message = form.message.data
            ),
            html_body = render_template('email/contact_form.html',
                name = form.name.data,
                message = form.message.data
            )
        )
        flash('Your email has been sent.')
        return redirect(url_for('index'))

    return render_template('contact.html', form=form, title='Contact')




@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))
