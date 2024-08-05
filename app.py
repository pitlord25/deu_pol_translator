import streamlit as st
from streamlit_modal import Modal
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import pandas as pd
from dotenv import load_dotenv
import os
from openai import OpenAI
import subprocess
import mysql.connector
from mysql.connector import Error

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
        st.error(f"Error: {e}")
        return None
    
def create_table_if_not_exists(connection):
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tbl_rules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            `case` TEXT NOT NULL,
            instruction TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tbl_feedbacks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            `feedback` TEXT NOT NULL
        )
    """)
    connection.commit()
    cursor.close()

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

def add_rule(connection, case, instruction):
    cursor = connection.cursor()
    cursor.execute("INSERT INTO tbl_rules (`case`, instruction) VALUES (%s, %s)", (case, instruction))
    connection.commit()
    cursor.close()
    
def add_feedback(connection, feedback):
    cursor = connection.cursor()
    cursor.execute("INSERT INTO tbl_feedbacks (`feedback`) VALUES (%s)", (feedback, ))
    connection.commit()
    cursor.close()
 
def update_rule(connection, rule_id, case, instruction):
    cursor = connection.cursor()
    cursor.execute("UPDATE tbl_rules SET `case` = %s, instruction = %s WHERE id = %s", (case, instruction, rule_id))
    connection.commit()
    cursor.close()

def delete_rule(connection, rule_id):
    cursor = connection.cursor()
    cursor.execute("DELETE FROM tbl_rules WHERE id = %s", (rule_id,))
    connection.commit()
    cursor.close()
    
# Helper functions for dialogs
def show_update_dialog(selected_rule):
    st.session_state['show_update_dialog'] = True
    st.session_state['selected_rule'] = selected_rule

def show_delete_dialog(selected_rule):
    st.session_state['show_delete_dialog'] = True
    st.session_state['selected_rule'] = selected_rule

# Function to display update dialog
def update_rule_dialog(connection):
    if 'selected_rule' in st.session_state:
        selected_rule = st.session_state['selected_rule']
        updated_case = st.text_input("Updated Case", selected_rule["Case"], key="update_case")
        updated_instruction = st.text_input("Updated Instruction", selected_rule["Instruction"], key="update_instruction")
        if st.button("Update Rule"):
            update_rule(connection, selected_rule["No"], updated_case, updated_instruction)
            st.success("Rule updated successfully!")
            st.session_state['show_update_dialog'] = False
            st.experimental_rerun()

# Function to display delete confirmation dialog
def delete_rule_dialog(connection):
    if 'selected_rule' in st.session_state:
        selected_rule = st.session_state['selected_rule']
        st.write(f"Are you sure you want to delete rule: {selected_rule['Case']}?")
        if st.button("Delete"):
            delete_rule(connection, selected_rule["No"])
            st.success("Rule deleted successfully!")
            st.session_state['show_delete_dialog'] = False
            st.experimental_rerun()
        if st.button("Cancel"):
            st.session_state['show_delete_dialog'] = False
            
def load_text_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        return text
    except FileNotFoundError:
        return f"The file {file_path} does not exist."
    except Exception as e:
        return str(e)
    
def save_text_to_file(file_path, text):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(text)
        return f"Text successfully saved to {file_path}."
    except Exception as e:
        return str(e)

# Load environment variables
load_dotenv()

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
OPENAI_MODEL = os.getenv('OPENAI_MODEL')
STREAMLIT_PORT = os.getenv("STREAMLIT_PORT", 8501)  # Default port is 8501

openAIClient = OpenAI()

connection = create_connection()

# Set OpenAI API key
# openai.api_key = OPENAI_API_KEY

# Streamlit app
st.title("Basic Web App Interface")

# Define tabs
tabs = st.tabs(["Translator", "Rules", "Main Prompt"])
file_path = 'system_prompt.txt'
prompt = load_text_from_file(file_path)

modal = Modal(key="Feedback_Modal", title="feedback")

with tabs[0]:
    st.header("Translator")
    text = st.text_area("Enter text to translate:")
    # target_language = st.selectbox("Select target language:", ["es", "fr", "de", "zh"])
    
    if st.button("Translate"):
        if text:
            # response = openai.Completion.create(
            #     engine="gpt-4o",
            #     prompt=f"Translate this text to {target_language}: {text}",
            #     max_tokens=60
            # )
            # translation = response.choices[0].text.strip()
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
                    "text" : prompt + text + rulesContent + feedbacksContent
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
            st.write("Translation:", translation.choices[0].message.content)
        else:
            st.write("Please enter text to translate.")
        
    # Add new rule
    st.write("Add New Feedback")
    # new_case = st.text_input("Case", key="input1")
    new_instruction = st.text_input("Instruction", key='instruction1')
    if st.button("Give feedback", key="button1"):
        add_feedback(connection, new_instruction)
        # st.success("Rule added successfully!")
        # st.rerun()

with tabs[1]:
    st.header("Rules")
    if connection:
        # Ensure the table exists
        create_table_if_not_exists(connection)
        
        # Fetch and display rules
        rules = get_rules(connection)
        if rules:
            df_rules = pd.DataFrame(rules)
            df_rules.columns = ["No", "Case", "Instruction"]

            gb = GridOptionsBuilder.from_dataframe(df_rules)
            gb.configure_pagination()
            gb.configure_column("Control", editable=False, cellRenderer='function(params) { return `<button>Edit</button><button>Delete</button>` }')
            gridOptions = gb.build()

            response = AgGrid(
                df_rules,
                gridOptions=gridOptions,
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=True
            )

            selected_rows = response['selected_rows']
            if selected_rows:
                for selected_rule in selected_rows:
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button(f"Edit {selected_rule['No']}"):
                            # Provide input fields for editing the selected rule
                            updated_case = st.text_input("Updated Case", selected_rule["Case"], key=f"updated_case_{selected_rule['No']}")
                            updated_instruction = st.text_input("Updated Instruction", selected_rule["Instruction"], key=f"updated_instruction_{selected_rule['No']}")
                            if st.button(f"Update Rule {selected_rule['No']}"):
                                update_rule(connection, selected_rule["No"], updated_case, updated_instruction)
                                st.success("Rule updated successfully!")
                                st.rerun()
                    with col2:
                        if st.button(f"Delete {selected_rule['No']}"):
                            delete_rule(connection, selected_rule["No"])
                            st.success("Rule deleted successfully!")
                            st.rerun()
        else:
            st.write("No rules found.")

        # Add new rule
        st.write("Add New Rule")
        new_case = st.text_input("Case")
        new_instruction = st.text_input("Instruction")
        if st.button("Add Rule"):
            add_rule(connection, new_case, new_instruction)
            st.success("Rule added successfully!")
            st.rerun()

        connection.close()
    else:
        st.error("Failed to connect to the database.")
        
with tabs[2]:
    st.header("Set System Prompt")
    prompt = st.text_area("Enter text to translate:", value=prompt, key="prompt")
    # target_language = st.selectbox("Select target language:", ["es", "fr", "de", "zh"])
    
    if st.button("Save prompt", key="save prompt"):
        save_text_to_file(file_path, prompt)
        
# You can add database connection and operations here using DB_USER, DB_PASSWORD, DB_HOST, DB_NAME

# Function to run the Streamlit app on the specified port
# with tabs[2]:

def run_streamlit():
    subprocess.run(["streamlit", "run", "app.py", "--server.port", STREAMLIT_PORT])


if __name__ == "__main__":
    run_streamlit()
