import requests
import easyocr
from openai import OpenAI  # Import OpenAI for API calls


def extract_text_from_receipt(image_path):
    """
    Extracts text from a receipt image using EasyOCR and enhances it with the Gemini API.
    


    :param image_path: Path to the receipt image.
    :return: Extracted text from the image.
    """
    try:
        # Open the image file
        with open(image_path, 'rb') as image_file:
            # Use EasyOCR to extract text from the image
            reader = easyocr.Reader(['en', 'ru'], gpu=True)
            result = reader.readtext(image_path)
            extracted_text = ' '.join([text[1] for text in result])

            # Prepare the request to the Gemini API for enhancement
            client = OpenAI(
                api_key="AIzaSyDw3G8cGlm13Qua3HV_3Bx3V2v1R2t1RJA",  # Replace with your actual API key
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )

            response = client.chat.completions.create(
                model="gemini-2.0-flash",
                n=1,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {
                        "role": "user",
                        "content": f'Enhance this text to more readable: {extracted_text}'
                    }
                ]
            )

            enhanced_text = response.choices[0].message.content  # Correctly access the content attribute


        return enhanced_text  # Return the enhanced text instead of the extracted text

    except Exception as e:
        return f"Error processing image: {str(e)}"  # Handle errors gracefully
