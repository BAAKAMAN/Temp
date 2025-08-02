from urllib import response
from flask import Flask, request, jsonify, render_template, g, redirect, url_for
import sqlite3
import joblib
import os
import random
from datetime import datetime

# --- Gemini API Imports ---
import google.generativeai as genai # Add this line
from dotenv import load_dotenv # Add this line if using .env file

# --- Configuration ---
DATABASE = 'database.db'
MODELS_DIR = 'models'
os.makedirs(MODELS_DIR, exist_ok=True)

app = Flask(__name__)

# --- Load Environment Variables (if using .env) ---
load_dotenv() # Call this early to load variables from .env file

# --- Database Helper Functions (unchanged) ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
    print("Database initialized/updated.")

# --- Model Loading (Updated for Gemini) ---
learning_gap_model = None
recommender_model = None
gemini_chat_model = None # New variable for Gemini model

def load_models():
    global learning_gap_model, recommender_model, gemini_chat_model

    # Configure Gemini API
    # Get API key from environment variable
    gemini_api_key = os.getenv("GOOGLE_API_KEY")
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        try:
            # Initialize the Gemini model for chat (e.g., 'gemini-pro')
            gemini_chat_model = genai.GenerativeModel('gemini-2.5-flash')
            print("Gemini API configured and model loaded successfully.")
            
        except Exception as e:
            print(f"Error configuring Gemini API or loading model: {e}")
            print("Chatbot will use rule-based fallback.")
    else:
        print("GOOGLE_API_KEY environment variable not set. Chatbot will use rule-based fallback.")

    # --- Learning Gap Model (unchanged from previous version) ---
    try:
        learning_gap_model_path = os.path.join(MODELS_DIR, 'learning_gap_model.pkl')
        if os.path.exists(learning_gap_model_path):
            learning_gap_model = joblib.load(learning_gap_model_path)
            print("Learning Gap Model loaded successfully.")
        else:
            print(f"Learning Gap Model not found at {learning_gap_model_path}. Using dummy.")
            def dummy_learning_gap_predictor(features):
                if features[0][0] < 60:
                    return [1]
                return [0]
            learning_gap_model = dummy_learning_gap_predictor
    except Exception as e:
        print(f"Error loading learning gap model: {e}")
        # Ensure dummy function is assigned even on error
        def dummy_learning_gap_predictor(features): return [0]
        learning_gap_model = dummy_learning_gap_predictor


    # --- Recommender Model (unchanged from previous version) ---
    try:
        # Dummy recommender for hackathon if not present
        def dummy_recommender(student_id, completed_topics, current_topic):
            all_content_titles = []
            cur = get_db().cursor()
            for row in cur.execute("SELECT title FROM content"):
                all_content_titles.append(row['title'])

            if current_topic:
                suggested = [c for c in all_content_titles if current_topic.lower() in c.lower() and c not in completed_topics]
                if suggested:
                    return random.sample(suggested, min(len(suggested), 3))

            available = [c for c in all_content_titles if c not in completed_topics]
            return random.sample(available, min(len(available), 3))

        recommender_model = dummy_recommender
        print("Recommender Model (dummy) loaded successfully.")

    except Exception as e:
        print(f"Error loading recommender model: {e}")
        # Ensure dummy function is assigned even on error
        def dummy_recommender(student_id, completed_topics, current_topic): return ["Dummy Recommendation 1"]
        recommender_model = dummy_recommender

# --- Routes (unchanged) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    db = get_db()
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()

        if not username or not password:
            return "Missing username or password", 400

        # Check if student already exists
        student = db.execute("SELECT * FROM students WHERE name = ?", (username,)).fetchone()

        if student:
            if student['name'] == 'admin' and student['password'] == password:
                return redirect(url_for('admin_dashboard'))
            # Check password for existing student
            elif student['password'] == password:
                return redirect(url_for('student_dashboard', student_id=student['id']))
            else:
                return "Incorrect password", 403
        else:
            # Create new student
            db.execute("INSERT INTO students (name, password) VALUES (?, ?)", (username, password))
            db.commit()
            
            # Get the new ID safely
            student_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            return redirect(url_for('student_dashboard', student_id=student_id))

    return render_template('login.html')


@app.route('/dashboard/<int:student_id>')
def student_dashboard(student_id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    if not student:
        return "Student not found", 404

    recent_interactions = db.execute(
        '''SELECT i.score, i.time_spent_seconds, i.completed, i.timestamp, c.title, c.topic, c.type
           FROM interactions i JOIN content c ON i.content_id = c.id
           WHERE i.student_id = ?
           ORDER BY i.timestamp DESC LIMIT 5''',
        (student_id,)
    ).fetchall()

    completed_topics_query = db.execute(
        '''SELECT DISTINCT c.topic
           FROM interactions i JOIN content c ON i.content_id = c.id
           WHERE i.student_id = ? AND i.completed = 1''',
        (student_id,)
    ).fetchall()
    completed_topics = [row['topic'] for row in completed_topics_query]

    current_content = db.execute(
        '''SELECT c.id, c.title, c.topic, i.score, i.time_spent_seconds
           FROM content c LEFT JOIN interactions i ON c.id = i.content_id AND i.student_id = ?
           ORDER BY RANDOM() LIMIT 1''',
        (student_id,)
    ).fetchone()

    try:
        features = [[
            current_content['score'] if current_content else 0,
            current_content['time_spent_seconds'] if current_content else 0,
            len(completed_topics)
        ]]

        prediction = learning_gap_model.predict(features)[0]
        learning_gap_prediction = "Likely to struggle" if prediction == 1 else "Doing well"
    except Exception as e:
        learning_gap_prediction = f"Error predicting: {e}"
   
    recommended_content_titles = []
    if recommender_model and current_content:
        try:
            recommended_content_titles = recommender_model(
                student_id,
                completed_topics,
                current_content['topic'] if current_content else None
            )
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            cur = db.execute("SELECT title FROM content ORDER BY RANDOM() LIMIT 3")
            recommended_content_titles = [row['title'] for row in cur.fetchall()]


    return render_template(
        'dashboard.html',
        student=student,
        recent_interactions=recent_interactions,
        learning_gap_prediction=learning_gap_prediction,
        recommended_content=recommended_content_titles
    )

@app.route('/admin')
def admin_dashboard():
    db = get_db()
    students = db.execute('SELECT * FROM students').fetchall()
    content = db.execute('SELECT * FROM content').fetchall()
    return render_template('admin.html', students=students, content=content)

@app.route('/chatbot')
def chatbot_page():
    return render_template('chatbot_ui.html')

# --- API Endpoints for Frontend Interaction ---

@app.route('/api/predict_learning_gap', methods=['POST'])
def api_predict_learning_gap():
    if not learning_gap_model:
        return jsonify({"error": "Learning gap model not loaded or configured."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input: No JSON data provided."}), 400

    try:
        features = [[
            data.get('quiz_score', 0),
            data.get('time_spent', 0),
            data.get('attempts', 0)
        ]]

        prediction = learning_gap_model.predict(features)[0]
        result = "Likely to struggle" if prediction == 1 else "Doing well"
        return jsonify({"status": "success", "prediction": result})
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {e}"}), 500

@app.route('/api/recommend_content', methods=['POST'])
def api_recommend_content():
    if not recommender_model:
        return jsonify({"error": "Recommender model not loaded or configured."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input: No JSON data provided."}), 400

    student_id = data.get('student_id')
    completed_topics = data.get('completed_topics', [])
    current_topic = data.get('current_topic')

    if student_id is None:
        return jsonify({"error": "student_id is required."}), 400

    try:
        recommended_lessons = recommender_model(student_id, completed_topics, current_topic)
        return jsonify({"status": "success", "recommendations": recommended_lessons})
    except Exception as e:
        return jsonify({"error": f"Recommendation failed: {e}"}), 500

@app.route('/api/chatbot', methods=['POST'])
def api_chatbot_response():
    """
    API endpoint for chatbot interaction, now potentially using Gemini.
    Expects JSON data: {"query": "What is the Pythagorean theorem?", "chat_history": []}
    """
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Invalid input: 'query' field missing."}), 400

    user_query = data['query']
    chat_history = data.get('chat_history', []) # Expects history as a list of {"role": "user/model", "parts": [{"text": "..."}]}

    response_text = "I'm sorry, I don't quite understand that. Can you rephrase?" # Default fallback

    if gemini_chat_model:
        try:
            # Start a chat session with the history
            convo = gemini_chat_model.start_chat(history=chat_history)
            
            # Send the new message
            convo.send_message(user_query)
            
            # Get the response
            gemini_response = convo.last.text
            response_text = gemini_response

        except Exception as e:
            print(f"Gemini API error: {e}")
            response_text = "I'm having trouble connecting to my knowledge base right now. Please try again later."
    else:
        # Fallback to rule-based if Gemini model is not loaded
        user_query_lower = user_query.lower()
        if "hello" in user_query_lower or "hi" in user_query_lower:
            response_text = "Hello! How can I help you with your learning today?"
        elif "pythagorean theorem" in user_query_lower:
            response_text = "The Pythagorean theorem states that in a right-angled triangle, the square of the hypotenuse (the side opposite the right angle) is equal to the sum of the squares of the other two sides: a² + b² = c²."
        elif "history of india" in user_query_lower:
            response_text = "India has a rich history! Are you interested in ancient, medieval, or modern history?"
        elif "who are you" in user_query_lower or "what can you do" in user_query_lower:
            response_text = "I am your adaptive learning assistant. I can help you find learning materials, predict areas where you might struggle, and answer basic questions."
        elif "thank you" in user_query_lower or "thanks" in user_query_lower:
            response_text = "You're welcome! Happy learning!"

    return jsonify({"status": "success", "response": response_text})


@app.route('/api/log_interaction', methods=['POST'])
def log_interaction():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input: No JSON data provided."}), 400

    student_id = data.get('student_id')
    content_id = data.get('content_id')
    score = data.get('score')
    time_spent_seconds = data.get('time_spent_seconds')
    completed = data.get('completed', False)

    if not all([student_id, content_id]):
        return jsonify({"error": "student_id and content_id are required."}), 400

    try:
        db = get_db()
        db.execute(
            'INSERT INTO interactions (student_id, content_id, score, time_spent_seconds, completed) VALUES (?, ?, ?, ?, ?)',
            (student_id, content_id, score, time_spent_seconds, int(completed))
        )
        db.commit()
        return jsonify({"status": "success", "message": "Interaction logged."}), 201
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to log interaction: {e}"}), 500


# --- CLI Commands for Database Init (unchanged) ---
@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')

# --- Main Run Block ---
if __name__ == '__main__':

    # Load models on startup, including Gemini
    load_models()

    app.run(debug=True, host='0.0.0.0', port=5000)