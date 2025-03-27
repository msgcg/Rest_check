from flask import Flask, request, render_template
from ocr_module import extract_text_from_receipt
from flask import jsonify
from openai import OpenAI  # Import OpenAI for API calls

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'receipt' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['receipt']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save the uploaded file
    file_path = f'uploads/{file.filename}'
    file.save(file_path)
    
    # Extract text from the receipt
    extracted_text = extract_text_from_receipt(file_path)
    
    # Call the Gemini API for bill-splitting recommendations
    num_people_str = request.form.get('num_people', '')  # Get number of people from form
    try:
        num_people = int(num_people_str) if num_people_str else None
    except ValueError:
        num_people = None  # Handle case where conversion fails

    client = OpenAI(
        api_key="AIzaSyDw3G8cGlm13Qua3HV_3Bx3V2v1R2t1RJA",  # Using the provided API key
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        n=1,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"Split the bill: {extracted_text} for {num_people} people. Use Russian to answer."
            }
        ]
    )
    recommendations = response.choices[0].message.content  # Correctly access the content attribute
    popa ='penis'



    return jsonify({'recommendations': recommendations}), 200

if __name__ == '__main__':
    app.run(debug=True)
