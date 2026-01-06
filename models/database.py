from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()


# Table Users
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    date_created = Column(DateTime, default=datetime.now)
    is_admin = Column(Integer, default=0)
    is_approved = Column(Integer, default=0)
    alert_threshold = Column(Float, default=10.0)
    daily_goal = Column(Float, default=5.0)

    # Relations
    equipments = relationship('Equipment', back_populates='user', lazy='select')
    usages = relationship('Usage', back_populates='user', lazy='select')
    predictions = relationship('Prediction', back_populates='user', lazy='select')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# Table Equipments
class Equipment(Base):
    __tablename__ = 'equipments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    puissance_watts = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)
    date_added = Column(DateTime, default=datetime.now)

    # Relations
    user = relationship('User', back_populates='equipments')
    usages = relationship('Usage', back_populates='equipment', lazy='select')


# Table Usages
class Usage(Base):
    __tablename__ = 'usages'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    equipment_id = Column(Integer, ForeignKey('equipments.id'), nullable=False)
    date = Column(DateTime, default=datetime.now)
    duree_heures = Column(Float, nullable=False)
    consommation_kwh = Column(Float, nullable=False)

    # Relations
    user = relationship('User', back_populates='usages')
    equipment = relationship('Equipment', back_populates='usages')


# Table Predictions
class Prediction(Base):
    __tablename__ = 'predictions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    consommation_prevue = Column(Float, nullable=False)
    date_created = Column(DateTime, default=datetime.now)

    # Relations
    user = relationship('User', back_populates='predictions')


# Fonction d'initialisation de la base de données
def init_db():
    engine = create_engine('sqlite:///database.db', echo=False)
    Base.metadata.create_all(engine)
    print("Base de données créée avec succès!")
    return engine


# Fonction pour obtenir une session
def get_session():
    engine = create_engine('sqlite:///database.db', echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


# Table Alerts
class Alert(Base):
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message = Column(String(255), nullable=False)
    alert_type = Column(String(50), nullable=False)  # 'warning', 'danger', 'info'
    is_read = Column(Integer, default=0)  # 0 = non lu, 1 = lu
    date_created = Column(DateTime, default=datetime.now)

    # Relations
    user = relationship('User', backref='alerts', lazy='select')


# Exécuter si ce fichier est lancé directement
if __name__ == '__main__':
    init_db()