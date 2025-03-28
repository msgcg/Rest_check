import os
import os
import google.generativeai as genai
import mimetypes


def process_image_with_gemini(filepath):
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
    # Determine the MIME type of the file
    mime_type, _ = mimetypes.guess_type(filepath)
    
    # Upload the file with the determined MIME type
    sample_file = genai.upload_file(path=filepath, mime_type=mime_type)


    
    model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-002")
    text = "OCR this image"
    response = model.generate_content([text, sample_file])
    response.text
    return response.text
