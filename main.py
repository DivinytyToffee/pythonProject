from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
db = SQLAlchemy(app)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, default=0)
    isActive = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'{self.title}'


@app.route('/')
def index():
    items = Item.query.order_by(Item.price).all()
    return render_template('index.html', products=items)


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


@app.route('/login')
def login():
    return render_template('add_product.html')


if __name__ == '__main__':
    app.run(debug=True)