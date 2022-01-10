import json
import random
import string

from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import InputRequired, Length, ValidationError

app = Flask(__name__)
app.secret_key = 'random string'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(26), nullable=False, unique=True)
    password = db.Column(db.Text(), nullable=False)
    email = db.Column(db.String(128), nullable=False, unique=True)
    firstName = db.Column(db.String(26), nullable=True)
    lastName = db.Column(db.String(26), nullable=True)
    orders = db.relationship('Order', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'{self.firstName} {self.lastName}'


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_list = db.Column(db.Text(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    all_total_quantity = db.Column(db.Integer)
    all_total_price = db.Column(db.Integer)
    status = db.Column(db.Boolean, default=False)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, default=0)
    isActive = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'{self.title}'


class RegisterForm(FlaskForm):
    email = StringField(validators=[InputRequired(), Length(min=4, max=128)],
                        render_kw={'placeholder': 'Email'})
    firstName = StringField(validators=[Length(min=4, max=26)],
                            render_kw={'placeholder': 'First Name'})
    lastName = StringField(validators=[Length(min=4, max=26)],
                           render_kw={'placeholder': 'Last Name'})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                             render_kw={'placeholder': 'Password'})
    submit = SubmitField('Register')

    def validate_email(self, email):
        existing = User.query.filter_by(email=email.data).first()
        if existing:
            raise ValidationError('email is registered')


class LoginForm(FlaskForm):
    login = StringField(validators=[InputRequired(), Length(min=4, max=26)],
                        render_kw={'placeholder': 'Login'})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                             render_kw={'placeholder': 'Password'})
    submit = SubmitField('Login')


@app.route('/')
def index():
    logged_in, first_name, kia = get_login_details()
    items = Item.query.order_by(Item.price).all()
    return render_template('index.html', products=items, logged_in=logged_in, first_name=first_name, kia=kia)


@app.route('/add_to_cart', methods=['POST', 'GET'])
def add_product_to_cart():
    _quantity = int(request.form['quantity'])
    _code = request.form['code']

    if _quantity and _code and request.method == 'POST':
        row = Item.query.filter_by(id=_code).first()
        kia = get_cart_key()

        item_array = {str(row.id): {'title': row.title, 'code': row.id, 'quantity': _quantity, 'price': row.price,
                                    'total_price': _quantity * row.price}}

        all_total_price = 0
        all_total_quantity = 0

        session.modified = True
        if kia in session:
            if row.id in session[kia]:
                for key, value in session[kia].items():
                    if row.id == key:
                        old_quantity = session[kia][key]['quantity']
                        total_quantity = old_quantity + _quantity
                        session[kia][key]['quantity'] = total_quantity
                        session[kia][key]['total_price'] = total_quantity * row.price
            else:
                session[kia] = array_merge(session[kia], item_array)

            for key, value in session[kia].items():
                individual_quantity = int(session[kia][key]['quantity'])
                individual_price = float(session[kia][key]['total_price'])
                all_total_quantity = all_total_quantity + individual_quantity
                all_total_price = all_total_price + individual_price
        else:
            session[kia] = item_array
            all_total_quantity = all_total_quantity + _quantity
            all_total_price = all_total_price + _quantity * row.price

        session['all_total_quantity'] = all_total_quantity
        session['all_total_price'] = all_total_price

        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))


@app.route('/empty')
def empty_cart():
    try:
        kia = get_cart_key()
        session.pop(kia)
        return redirect(url_for('index'))
    except Exception as e:
        return redirect(url_for('index'))


@app.route('/delete/<string:code>')
def delete_product(code):
    all_total_price = 0
    all_total_quantity = 0
    session.modified = True
    cart_item = get_cart_key()

    for item in session[cart_item].items():
        if item[0] == code:
            session[cart_item].pop(item[0], None)
            if cart_item in session:
                for key, value in session[cart_item].items():
                    individual_quantity = int(session[cart_item][key]['quantity'])
                    individual_price = float(session[cart_item][key]['total_price'])
                    all_total_quantity = all_total_quantity + individual_quantity
                    all_total_price = all_total_price + individual_price
            break

    if all_total_quantity == 0:
        session.pop(cart_item)
    else:
        session['all_total_quantity'] = all_total_quantity
        session['all_total_price'] = all_total_price

    return redirect(url_for('index'))


@app.route('/add', methods=['POST', 'GET'])
def add_product():
    if request.method == 'POST':
        title = request.form['title']
        price = request.form['price']

        item = Item(title=title, price=price)

        try:
            db.session.add(item)
            db.session.commit()
            return redirect('/')
        except Exception as ex:
            return str(ex)
    else:
        return render_template('add_product.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(login=form.login.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            if session.get(get_cart_key()):
                return redirect(url_for('order'))
            return redirect(url_for('index'))
    return render_template('login.html', form=form, login=request.values.get('login'),
                           password=request.values.get('password'))


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hash_pass = bcrypt.generate_password_hash(form.password.data)
        rand_str = "".join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(10))
        login = f'{form.email.data.split("@")[0]}_{rand_str}'
        new_user = User(email=form.email.data, password=hash_pass, login=login,
                        lastName=form.lastName.data, firstName=form.firstName.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login', login=login, password=form.password.data))
    return render_template('register.html', form=form)


@app.route('/order', methods=['POST', 'GET'])
@login_required
def order():
    logged_in, first_name, kia = get_login_details()
    user_id = session.get('_user_id')
    if session.get(get_cart_key()):
        user = User.query.filter_by(id=int(user_id)).first()
        order_list = json.dumps(session.get(get_cart_key()))
        all_total_price = int(session.get('all_total_price'))
        all_total_quantity = int(session.get('all_total_quantity'))
        _order = Order(user_id=int(user.id), order_list=order_list,
                       all_total_quantity=all_total_quantity, all_total_price=all_total_price)
        db.session.add(_order)
        db.session.commit()
        session.update({'_order_id': _order.id})

    return render_template('order.html', logged_in=logged_in, first_name=first_name, kia=kia)


@app.route('/buy', methods=['POST', 'GET'])
@login_required
def buy():
    order_id = session.get('_order_id')
    if session.get(get_cart_key()):
        _order = Order.query.filter_by(id=order_id).first()
        _order.id = True
        db.session.add(_order)
        db.session.commit()
        return redirect(url_for('empty_cart'))
    return redirect(url_for('index'))


def array_merge(first_array, second_array):
    if isinstance(first_array, dict) and isinstance(second_array, dict):
        return dict(list(first_array.items()) + list(second_array.items()))
    return False


def get_cart_key():
    return 'cart_items'


def get_login_details():
    logged_in = False
    first_name = ''
    kia = get_cart_key()
    if session.get('_user_id'):
        user = User.query.filter_by(id=int(session.get('_user_id'))).first()
        if user:
            logged_in = True
            first_name = user.firstName
    return logged_in, first_name, kia


if __name__ == '__main__':
    app.run(debug=True)
