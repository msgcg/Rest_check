from flask import Flask, request, render_template


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('ocr.html')

@app.route('/process-image', methods=['POST'])
def process_image():
    image_url = request.form.get('image-url')
    extracted_text = extract_text_from_image(image_url)
    return {'text': extracted_text}

if __name__ == '__main__':
    app.run(debug=True)
