from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class FactoryComponent(db.Model):
    __tablename__ = 'factory_components'

    id = db.Column(db.Integer, primary_key=True)
    component_name = db.Column(db.String(120), nullable=False)
    component_type = db.Column(db.String(60), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default='Active')
    location = db.Column(db.String(120), default='Unknown')

    def to_dict(self):
        return {
            'id': self.id,
            'component_name': self.component_name,
            'component_type': self.component_type,
            'level': self.level,
            'status': self.status,
            'location': self.location,
        }
