import random
import os
import logging 

from flask import Flask, redirect, render_template, request, url_for

from models import Pair, db



def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app


app = create_app()

app.logger.setLevel(logging.DEBUG)

@app.route('/', methods=['GET', 'POST'])
def index():

    feedback = None

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
            feedback = 'Correct!'
        else:
            feedback = f'The correct translation of {word_to_translate} is {correct_answer}'

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
    if not pairs:
        # Handle the case where there are no pairs in the database
        return "No word pairs available", 404

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

    # Determine the word to translate and the correct answer
    if language == 'english':
        word_to_translate = random_pair.english_word
        correct_answer = random_pair.dutch_word
    else:
        word_to_translate = random_pair.dutch_word
        correct_answer = random_pair.english_word

    return render_template('game.html', feedback=feedback, word_to_translate=word_to_translate, correct_answer=correct_answer, pair_id=random_pair.id, language=language)


@app.route('/words')
def words():
    pairs = Pair.query.all()
    return render_template('words.html', pairs=pairs)


@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    pair: Pair = Pair.query.get_or_404(id)
    if request.method == 'POST':
        pair.english_word = request.form['english']
        pair.dutch_word = request.form['dutch']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('update.html', pair=pair)


@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        new_pair = Pair(
            english_word=request.form['english'],
            dutch_word=request.form['dutch']
        )
        db.session.add(new_pair)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('create.html')


if __name__ == '__main__':
    app.run(debug=True)
