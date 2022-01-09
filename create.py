from main import db, User, Item, session

db.create_all()
# us = User(password='123456', email='step@sa.com',
#           firstName='Ivan', lastName='Vanko')
# db.session.add(us)
# db.session.commit()
# print(User.query.filter_by(email='step@sacom').first())