from flask import Flask, render_template, request
from flask import redirect, url_for
import fitz 
import json
import os
import boto3
app = Flask(__name__)

def search(query, json_content):
    prompt_data = f"""You are a proficient AI lawyer and content retrieval specialist tasked with finding the following topic from the given JSON content {json_content} against the provided query: {query}.
    Once you find the desired result, please stop the search. Please be specific and concise, and avoid repeating the content. ONLY GIVE ANSWER FROM THE JSON FILE CONTENT OTHERWISE SAY SORRY."""
    prompt = "[INST]" + prompt_data + "[/INST]"

    bedrock = boto3.client(service_name="bedrock-runtime")
    payload = {
        "prompt": prompt,
        "temperature": 0.1,
        "top_p": 0.9
    }
    body = json.dumps(payload)
    model_id = "mistral.mixtral-8x7b-instruct-v0:1"
    response = bedrock.invoke_model(
        body=body,
        modelId=model_id,
        accept="application/json",
        contentType="application/json"
    )
    response_body = json.loads(response.get("body").read())
    return response_body['outputs'][0]['text']

# Function to append text to JSON file with key-value pairs
def append_to_json_with_key_value(key, value, json_path):
    try:
        with open(json_path, 'r+') as json_file:
            data = json.load(json_file)
            data[key] = value  # Add key-value pair to existing data
            json_file.seek(0)  # Move the file pointer to the beginning
            json.dump(data, json_file, indent=4)  # Dump updated data to JSON file with indentation
            json_file.truncate()  # Truncate the file to remove remaining data
    except FileNotFoundError:
        save_to_json_with_key_value(key, value, json_path)  # If file not found, create a new JSON file

# Function to save text to JSON file with key-value pairs
def save_to_json_with_key_value(key, value, json_path):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w') as json_file:
        json.dump({key: value}, json_file, indent=4)  # Save data as key-value pair with indentation

# Function to extract text from PDF using PyMuPDF

def extract_text_from_pdf(uploaded_file):
    text = ""
    pdf_contents = uploaded_file.read()
    pdf_document = fitz.open(stream=pdf_contents, filetype="pdf")
    for page in pdf_document:
        text += page.get_text()
    return text

# Function to fetch result from JSON based on query
def fetch_result_from_json(json_path, query):
    try:
        with open(json_path, 'r') as json_file:
            data = json.load(json_file)
            if query in data:
                return data[query]
            else:
                return "Query not found in JSON file"
    except FileNotFoundError:
        return "JSON file not found"
    except Exception as e:
        return f"Error reading JSON file: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
        pdf_contents = extract_text_from_pdf(uploaded_file)
        append_to_json_with_key_value("pdf_text", pdf_contents, "output/result.json")
        return redirect(url_for('ask'))  # Redirect to the ask route
    return "No file selected!"

@app.route('/ask', methods=['GET', 'POST'])
def ask():
    if request.method == 'POST':
        query = request.form['query']
        result = fetch_result_from_json("output/result.json", "pdf_text")
        answer = search(query, result)
        return answer
    return render_template('ask.html')

if __name__ == '__main__':
    app.run(debug=True)
