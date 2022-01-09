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
    password = db.Column(db.Text(), nullable=False)
    email = db.Column(db.String(128), nullable=False, unique=True)
    firstName = db.Column(db.String(26), nullable=True)
    lastName = db.Column(db.String(26), nullable=True)

    def __repr__(self):
        return f'{self.firstName} {self.lastName}'


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
    email = StringField(validators=[InputRequired(), Length(min=4, max=128)],
                        render_kw={'placeholder': 'Email'})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                             render_kw={'placeholder': 'Password'})
    submit = SubmitField('Login')


def getLoginDetails():
    loggedIn = False
    firstName = ''
    noOfItems = 0
    if session.get('email'):
        user = User.query.filter_by(email=session.get('email')).first()
        loggedIn = True
        userId, firstName = user.id, user.firstName
    return (loggedIn, firstName, noOfItems)


@app.route('/')
def index():
    logged_in, first_name, no_of_items = getLoginDetails()
    items = Item.query.order_by(Item.price).all()
    return render_template('index.html', products=items, logged_in=logged_in, first_name=first_name)


@app.route('/add_to_cart', methods=['POST', 'GET'])
def add_product_to_cart():
    _quantity = int(request.form['quantity'])
    _code = request.form['code']
    # validate the received values
    if _quantity and _code and request.method == 'POST':
        row = Item.query.filter_by(id=_code).first()

        itemArray = {str(row.id): {'title': row.title, 'code': row.id, 'quantity': _quantity, 'price': row.price,
                     'total_price': _quantity * row.price}}

        all_total_price = 0
        all_total_quantity = 0

        # session.modified = True
        if 'cart_item' in session:
            if row.id in session['cart_item']:
                for key, value in session['cart_item'].items():
                    if row.id == key:
                        old_quantity = session['cart_item'][key]['quantity']
                        total_quantity = old_quantity + _quantity
                        session['cart_item'][key]['quantity'] = total_quantity
                        session['cart_item'][key]['total_price'] = total_quantity * row.price
            else:
                session['cart_item'] = array_merge(session['cart_item'], itemArray)

            for key, value in session['cart_item'].items():
                individual_quantity = int(session['cart_item'][key]['quantity'])
                individual_price = float(session['cart_item'][key]['total_price'])
                all_total_quantity = all_total_quantity + individual_quantity
                all_total_price = all_total_price + individual_price
        else:
            session['cart_item'] = itemArray
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
        session.clear()
        return redirect(url_for('index'))
    except Exception as e:
        print(e)


@app.route('/delete/<string:code>')
def delete_product(code):
    all_total_price = 0
    all_total_quantity = 0
    session.modified = True

    for item in session['cart_item'].items():
        if item[0] == code:
            session['cart_item'].pop(item[0], None)
            if 'cart_item' in session:
                for key, value in session['cart_item'].items():
                    individual_quantity = int(session['cart_item'][key]['quantity'])
                    individual_price = float(session['cart_item'][key]['total_price'])
                    all_total_quantity = all_total_quantity + individual_quantity
                    all_total_price = all_total_price + individual_price
            break

    if all_total_quantity == 0:
        session.clear()
    else:
        session['all_total_quantity'] = all_total_quantity
        session['all_total_price'] = all_total_price

    # return redirect('/')
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
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html', form=form)


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hash_pass = bcrypt.generate_password_hash(form.password.data)
        new_user = User(email=form.email.data, password=hash_pass,
                        lastName=form.lastName.data, firstName=form.firstName.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


def array_merge(first_array, second_array):
    if isinstance(first_array, dict) and isinstance(second_array, dict):
        return dict(list(first_array.items()) + list(second_array.items()))
    return False


if __name__ == '__main__':
    app.run(debug=True)
