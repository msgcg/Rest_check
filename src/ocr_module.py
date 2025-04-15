import os
import google.generativeai as genai
import mimetypes
import logging 

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_image_with_gemini(filepath):
    """
    Processes an image file using Google Gemini for OCR.

    Args:
        filepath (str): The path to the image file.

    Returns:
        str: The extracted text from the image, or None if an error occurs.
    """
    try:
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("GOOGLE_API_KEY environment variable not set.")
            return None
        genai.configure(api_key=api_key)

        # Определяем MIME-тип файла
        mime_type, _ = mimetypes.guess_type(filepath)
        if not mime_type or not mime_type.startswith('image/'):
             logger.error(f"Invalid or unsupported MIME type: {mime_type} for file {filepath}")
             mime_type = 'application/octet-stream'
             logger.warning(f"Could not determine image MIME type for {filepath}. Trying {mime_type}.")

        logger.info(f"Uploading file: {filepath} with MIME type: {mime_type}")
        # Загружаем файл
        sample_file = genai.upload_file(path=filepath, mime_type=mime_type)
        logger.info(f"File uploaded successfully: {sample_file.name}")

        model = genai.GenerativeModel(model_name="models/gemini-2.0-flash") # Используем стандартное имя
        prompt = "Выполни OCR для этого изображения. Верни только извлеченный текст без дополнительных комментариев."
        logger.info("Generating content with Gemini...")
        response = model.generate_content([prompt, sample_file])

        # Проверяем наличие текста в ответе
        if response.text:
            logger.info("OCR successful.")
            return response.text
        else:
            logger.warning("OCR completed, but no text was extracted.")
            # Проверим, есть ли ошибки в кандидатах
            if response.candidates and response.candidates[0].finish_reason != 'STOP':
                 logger.error(f"Gemini generation finished with reason: {response.candidates[0].finish_reason}")
            return "" # Возвращаем пустую строку, если текст не извлечен

    except Exception as e:
        logger.error(f"Error processing image with Gemini: {e}", exc_info=True)
        return None
