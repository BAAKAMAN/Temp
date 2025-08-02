# Save this as generate_learning_gap_data.py in your project's root folder
import pandas as pd
import numpy as np

def generate_learning_gap_data(num_samples=1000):
    np.random.seed(42) # for reproducibility

    data = {
        'quiz_score_prev_topic': np.random.randint(30, 100, num_samples),
        'time_spent_on_prev_lesson_minutes': np.random.randint(10, 120, num_samples),
        'num_attempts_on_prev_quiz': np.random.randint(1, 5, num_samples),
        # 'previous_module_grade': np.random.randint(40, 100, num_samples) # <-- REMOVE THIS LINE
    }
    df = pd.DataFrame(data)

    # Define a simple rule for 'struggle_next_concept' for synthetic data
    # Students struggle if prev quiz score is low AND time spent is low OR many attempts
    df['struggle_next_concept'] = ((df['quiz_score_prev_topic'] < 60) &
                                   (df['time_spent_on_prev_lesson_minutes'] < 45)).astype(int) | \
                                  (df['num_attempts_on_prev_quiz'] > 3).astype(int) # <-- SIMPLIFIED RULE

    # Add some randomness to make it not perfectly clean
    noise_idx = np.random.choice(df.index, size=int(num_samples * 0.05), replace=False)
    df.loc[noise_idx, 'struggle_next_concept'] = 1 - df.loc[noise_idx, 'struggle_next_concept']

    return df

if __name__ == "__main__":
    df = generate_learning_gap_data()
    df.to_csv('models/learning_gap_data.csv', index=False)
    print(f"Generated {len(df)} samples of learning gap data with 3 features to learning_gap_data.csv")
    print(df.head())