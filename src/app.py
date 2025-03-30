from flask import Flask, request, render_template, jsonify
import os
from google import genai
from ocr_module import process_image_with_gemini
from pydantic import BaseModel

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # Set the upload folder from environment variable

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_receipt', methods=['POST'])
def upload_receipt():
    image_file = request.files.get('receipt_image')
    if not image_file:
        return jsonify({'error': 'No image file provided'}), 400

    # Get the original filename
    original_filename = image_file.filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)  # Save with original filename

    image_bytes = image_file.read()  # Read the file content into bytes

    # Save the uploaded image temporarily
    with open(filepath, 'wb') as f:
        f.write(image_bytes)

    try:
        # Process the image with Google Gemini
        extracted_text = process_image_with_gemini(filepath)

        if not extracted_text:
            return jsonify({'error': 'No extracted text provided'}), 400  
    finally:
        # Delete the file after processing
        if os.path.exists(filepath):
            os.remove(filepath)  

    # Extract number of people
    num_people_str = request.form.get('num_people', '')  
    try:
        num_people = int(num_people_str) if num_people_str else None
    except ValueError:
        num_people = None  

    # Get recommendations without needing a recommendation_type
    recommendations = get_recommendations(extracted_text, num_people)
    return jsonify(recommendations)

class Recommendation(BaseModel):
    equally: str
    who_more_eat_then_more_pay: str
    who_more_cost_then_more_pay: str

def get_recommendations(extracted_text, num_people):  
    prompt = f"""Приведи различные варианты распределения счета в ресторане на {num_people} человек.

    Сам текст счета: {extracted_text}.

    Приведи очень подробные красиво оформленные отступами рекомендации с конкретными цифрами и блюдами(при необхожимости).
    """

    client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': list[Recommendation],
        },
    )
    # Use instantiated objects.
    recs: list[Recommendation] = response.parsed
    startelem = recs[0]
    return {
        "equally": startelem.equally,
        "who_more_cost_then_more_pay": startelem.who_more_cost_then_more_pay,
        "who_more_eat_then_more_pay": startelem.who_more_eat_then_more_pay
    }

if __name__ == '__main__':
    app.run(debug=True)
