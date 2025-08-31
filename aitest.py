from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from flask_socketio import SocketIO
import os
from flask_cors import CORS
import openai



load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app)


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    prompt = data.get("prompt", "Say something smart")  # Combined prompt handling
    
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt},  # Using the actual prompt from request
        ],
        stream=False
    )

    # Correct way to access the response content
    response_content = response.choices[0].message.content
    print(response_content)
    
    return jsonify({
        'response': response_content
    })

if __name__ == '__main__':
    app.run(debug=True)
