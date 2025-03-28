from flask import Flask, request, render_template
from openai import OpenAI
import requests
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-receipt', methods=['POST'])
def upload_receipt():
    # Handle receipt image upload and OCR processing
    image_file = request.files.get('receipt_image')
    if not image_file:
        return {'error': 'No image file provided'}, 400

    # Call the OCR API to extract text from the image file
    data = request.get_json()  # Get JSON data from the request
    extracted_text = data.get('extracted_text', '')  # Extract the text from the request
    if not extracted_text:
        return {'error': 'No extracted text provided'}, 400  # Return 400 if no text is provided

    # Improve the readability of the extracted text
    improved_text_response = good_text(extracted_text)  # Improve the readability of the extracted text
    improved_text = improved_text_response['text']

    # Get number of people from form
    num_people_str = request.form.get('num_people', '')  
    try:
        num_people = int(num_people_str) if num_people_str else None
    except ValueError:
        num_people = None  # Handle case where conversion fails

    # Get recommendations for splitting the bill
    recommendations = get_recommendations(improved_text, num_people)
    return recommendations

def ocr_api_extract_text(image_file):
    # Call the OCR API to extract text from the image file
    # Implement the actual API call here
    # Example implementation of calling the OCR API
    response = requests.post('YOUR_OCR_API_ENDPOINT', files={'file': image_file})
    if response.status_code == 200:
        return response.json().get('extracted_text', '')
    else:
        return None  # Return None if the API call fails

def good_text(extracted_text):  # Accept extracted text as an argument
    client = OpenAI(
        api_key="AIzaSyDw3G8cGlm13Qua3HV_3Bx3V2v1R2t1RJA",  
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        n=1,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"Make this restaurant summary more readable: {extracted_text}."
            }
        ]
    )
    text = response.choices[0].message.content  # Access the content attribute
    return {'text': text}

def get_recommendations(extracted_text, num_people):  # Accept extracted text and number of people as arguments
    client = OpenAI(
        api_key="AIzaSyDw3G8cGlm13Qua3HV_3Bx3V2v1R2t1RJA",  
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
    recommendations = response.choices[0].message.content  # Access the content attribute
    return {'text': recommendations}

if __name__ == '__main__':
    app.run(debug=True)
