from fastapi import FastAPI
from pydantic import BaseModel
import os
from openai import OpenAI
import mysql.connector
from mysql.connector import Error

app = FastAPI()

# Function to create a database connection

def create_connection():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None
    
def get_rules(connection):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tbl_rules")
    rows = cursor.fetchall()
    cursor.close()
    return rows

def get_feedbacks(connection):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tbl_feedbacks")
    rows = cursor.fetchall()
    cursor.close()
    return rows

def load_text_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        return text
    except FileNotFoundError:
        return f"The file {file_path} does not exist."
    except Exception as e:
        return str(e)
    
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
OPENAI_MODEL = os.getenv('OPENAI_MODEL')
STREAMLIT_PORT = os.getenv("STREAMLIT_PORT", 8501)  # Default port is 8501

openAIClient = OpenAI()

connection = create_connection()
class TextRequest(BaseModel):
    text: str
    
file_path = 'system_prompt.txt'
prompt = load_text_from_file(file_path)

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI application!"}

@app.post("/translate")
def get_text(request: TextRequest):
    rawRules = get_rules(connection)
    rulesContent = "Dodatkowe zasady, których należy przestrzegać:\n"
    idx = 1
    for rawRule in rawRules :
        rulesContent += f"Sprawa {idx}: {rawRule['case']} -> {rawRule['instruction']}\n"
        idx = idx + 1
        
    rawFeedbacks = get_feedbacks(connection)
    feedbacksContent = "Noted Feedbacks:"
    idx = 1
    for rawFeedback in rawFeedbacks :
        feedbacksContent += f"Sprawa {idx}: {rawFeedback['feedback']}\n"
        idx = idx + 1
    
    content = [
        {
            "type" : "text",
            "text" : prompt + request.text + rulesContent + feedbacksContent
        }
    ]
    translation = openAIClient.chat.completions.create(
        model=OPENAI_MODEL,
        messages = [
            {
                "role" : "user",
                "content" : content
            }
        ]
    )
    return {"translation": translation.choices[0].message.content}
