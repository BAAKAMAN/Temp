DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS content;
DROP TABLE IF EXISTS interactions;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    grade INTEGER,
    learning_style TEXT,
    last_login DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT,
    type TEXT, -- e.g., 'lesson', 'quiz', 'video'
    text_content TEXT,
    video_url TEXT
);

CREATE TABLE interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    content_id INTEGER NOT NULL,
    score INTEGER, -- For quizzes
    time_spent_seconds INTEGER,
    completed BOOLEAN DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (content_id) REFERENCES content(id)
);

-- Initial data for demonstration
INSERT INTO students (name, password, grade, learning_style) VALUES
('Alice Johnson', 12345, 10, 'visual'),
('Bob Smith', 12346, 9, 'auditory'),
('Charlie Brown', 12347, 11, 'kinesthetic'),
('admin', 0, 0, 'admin');   

INSERT INTO interactions (student_id, content_id, score, time_spent_seconds, completed) VALUES
(1, 1, 85, 300, 1),
(2, 2, 90, 600, 0),
(3, 3, 75, 450, 1),
(5, 4, 90, 1200, 0);

INSERT INTO content (title, topic, difficulty, type, text_content) VALUES
('Introduction to Algebra', 'Mathematics', 'easy', 'lesson', 'Algebra is the branch of mathematics that uses symbols...'),
('Quiz on Basic Algebra', 'Mathematics', 'easy', 'quiz', 'What is x in 2x + 5 = 15?'),
('Video: Understanding Geometry', 'Mathematics', 'medium', 'video', 'https://example.com/geometry_video'),
('History of India - Ancient Period', 'History', 'medium', 'lesson', 'The history of India begins with the Indus Valley Civilization...'),
('Quiz on Ancient India', 'History', 'medium', 'quiz', 'Which river was the Indus Valley Civilization located on?');