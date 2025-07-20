from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class MonkeyDetection(db.Model):
    __tablename__ = 'monkey_detections'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    location_x = db.Column(db.Float, nullable=True)
    location_y = db.Column(db.Float, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    video_source = db.Column(db.String(100), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
            'location_x': self.location_x,
            'location_y': self.location_y,
            'image_path': self.image_path,
            'video_source': self.video_source
        } 