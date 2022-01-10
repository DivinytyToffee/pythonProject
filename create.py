from main import db, User, Item, session

db.create_all()
us1 = Item(title='first', price=25)
us2 = Item(title='second', price=50)
us3 = Item(title='third', price=100)
db.session.add(us1)
db.session.add(us2)
db.session.add(us3)
db.session.commit()
