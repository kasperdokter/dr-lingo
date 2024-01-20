import csv
import logging
import os
import random

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.utils import secure_filename

from models import Pair, db


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get('SECRET_KEY')

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app


app = create_app()

app.logger.setLevel(logging.DEBUG)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == os.getenv('WEB_PASSWORD'):
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash("Incorrect password. Let's hope it is just a typo... 😉", 'error')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Handle the previous answer
    if request.method == 'POST':
        data = request.form

        word_to_translate = data.get('word_to_translate')
        correct_answer = data.get('correct_answer')
        pair_id = data.get('pair_id')
        language = data.get('language')

        # Check the answer
        is_correct = data['user_answer'] == data['correct_answer']

        # Set the feedback
        if is_correct:
            flash('Correct! 🥰', 'success')
        else:
            flash(
                f'👎 The correct translation of <em>{word_to_translate}</em> is <em>{correct_answer}</em>', 'error')

        # Update the counters
        pair: Pair = Pair.query.get_or_404(int(pair_id))

        if language == 'english':
            pair.english_asked_count += 1
            if is_correct:
                pair.english_correct_count += 1
        else:
            pair.dutch_asked_count += 1
            if is_correct:
                pair.dutch_correct_count += 1

        db.session.commit()

    # Query all pairs and randomly select one
    pairs = Pair.query.all()

    has_pairs = len(pairs) > 0

    if has_pairs:
        questions = [
            (pair, language)
            for pair in pairs
            for language in ['english', 'dutch']
        ]

        def get_weight(pair: Pair, language: str) -> int:
            if language == 'english':
                if pair.english_asked_count == 0:
                    return 1
                return 1 - pair.english_correct_count / pair.english_asked_count
            else:
                if pair.dutch_asked_count == 0:
                    return 1
                return 1 - pair.dutch_correct_count / pair.dutch_asked_count

        weights = [
            get_weight(pair, language) + 0.001
            for (pair, language) in questions
        ]

        # Select a random question
        random_question = random.choices(questions, weights)[0]
        random_pair, language = random_question
        pair_id=random_pair.id

        # Determine the word to translate and the correct answer
        if language == 'english':
            word_to_translate = random_pair.english_word
            correct_answer = random_pair.dutch_word
        else:
            word_to_translate = random_pair.dutch_word
            correct_answer = random_pair.english_word
    else:
        word_to_translate = ''
        correct_answer = ''
        pair_id = ''
        language = ''

    return render_template('game.html', has_pairs=has_pairs, word_to_translate=word_to_translate, correct_answer=correct_answer, pair_id=pair_id, language=language)


@app.route('/words')
def words():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    pairs = Pair.query.all()
    return render_template('words.html', pairs=pairs)


@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    pair: Pair = Pair.query.get_or_404(id)
    if request.method == 'POST':
        pair.english_word = request.form['english']
        pair.dutch_word = request.form['dutch']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('update.html', pair=pair)


@app.route('/create', methods=['GET', 'POST'])
def create():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_pair = Pair(
            english_word=request.form['english'],
            dutch_word=request.form['dutch']
        )
        db.session.add(new_pair)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('create.html')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'


def process_file(file):
    reader = csv.DictReader(file.read().decode('utf-8').splitlines())
    for row in reader:
        english_word = row.get('en')
        dutch_word = row.get('nl')
        if english_word and dutch_word:
            pair = Pair.query.filter_by(english_word=english_word, dutch_word=dutch_word).first()
            if not pair:
                new_pair = Pair(
                    english_word=english_word,
                    dutch_word=dutch_word,
                    english_asked_count=0,
                    english_correct_count=0,
                    dutch_asked_count=0,
                    dutch_correct_count=0
                )
                db.session.add(new_pair)
    db.session.commit()


@app.route('/upload', methods=['GET', 'POST'])
def upload_csv():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            process_file(file)
            return redirect(url_for('words'))
    return redirect(url_for('words'))


if __name__ == '__main__':
    app.run(debug=True)
