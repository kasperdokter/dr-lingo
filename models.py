from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String

db = SQLAlchemy()

class Pair(db.Model):
    __tablename__ = 'pairs'

    id = Column(Integer, primary_key=True)
    english_word = Column(String, nullable=False)
    dutch_word = Column(String, nullable=False)

    english_asked_count = Column(Integer, default=0)
    english_correct_count = Column(Integer, default=0)
    dutch_asked_count = Column(Integer, default=0)
    dutch_correct_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<Pair(english_word='{self.english_word}', dutch_word='{self.dutch_word}')>"