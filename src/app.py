# --- START OF FILE app.py ---

from flask import Flask, request, render_template, jsonify, send_from_directory
import os
import google.generativeai as genai
from google import genai as genai_module
from ocr_module import process_image_with_gemini
from pydantic import BaseModel, ValidationError  
from typing import Dict, List, Optional
import logging
import json # Для обработки данных от фронтенда

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Убедитесь, что папка uploads существует
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Упрощенные Pydantic Модели ---
# --- Новая Pydantic модель для проверки ---
class RestaurantCheckResult(BaseModel):
    is_restaurant: bool

class PositionItem(BaseModel):
    name: str
    price: int # <--- Изменено на int

class Positions(BaseModel):
    positions_list: List[PositionItem]
    total_amount_detected: int # <--- Изменено на int

class PersonShare(BaseModel):
    equally: int
    who_more_eat_then_more_pay: int
    who_more_cost_then_more_pay: int
    proportional_division_by_the_cost_of_orders: int

class PersonShareItem(BaseModel):
    name: str
    shares: PersonShare

class Recommendation(BaseModel):
    peoples_list: List[PersonShareItem]
    final_total_calculated: Optional[int] = 0



# --- Настройка Gemini (без изменений) ---
def get_gemini_model(model_name="models/gemini-2.0-flash"):
    # ... (код функции без изменений) ...
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set.")
        raise ValueError("API key not configured.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

# --- Новая функция для проверки ---
def is_restaurant_check(extracted_text: str) -> Optional[bool]:
    """
    Проверяет, является ли текст чеком из ресторана, используя Gemini.
    """
    if not extracted_text:
        logger.warning("No extracted text provided to is_restaurant_check.")
        return False # Считаем, что пустой текст - не чек

    prompt = f"""
Проанализируй следующий текст:
--- ТЕКСТ ---
{extracted_text}
--- КОНЕЦ ТЕКСТА --- """ + """


Является ли этот текст чеком из ресторана, кафе, бара или похожего заведения общепита?
Верни ответ СТРОГО в формате JSON с одним булевым полем 'is_restaurant'.
Пример: {{ "is_restaurant": true }} или {{ "is_restaurant": false }}
Не добавляй никаких других пояснений или текста вне JSON.
"""
    try:
        model = get_gemini_model() # Используем flash по умолчанию
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=RestaurantCheckResult # Используем новую простую модель
            )
        )

        # Парсинг и валидация
        if hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts') and response.candidates[0].content.parts:
             json_text = response.candidates[0].content.parts[0].text
             logger.info(f"Received JSON from Gemini for restaurant check: {json_text}")
             parsed_data = json.loads(json_text)
             try:
                 check_result = RestaurantCheckResult(**parsed_data)
                 logger.info(f"Restaurant check result: {check_result.is_restaurant}")
                 return check_result.is_restaurant
             except ValidationError as e:
                 logger.error(f"Pydantic validation failed for restaurant check: {e}. JSON: {json_text}")
                 return None # Ошибка валидации
        elif response.text: # Fallback
             try:
                 logger.info(f"Trying to parse restaurant check from response.text: {response.text}")
                 parsed_data = json.loads(response.text)
                 check_result = RestaurantCheckResult(**parsed_data)
                 logger.info(f"Restaurant check result from response.text: {check_result.is_restaurant}")
                 return check_result.is_restaurant
             except Exception as parse_err:
                 logger.error(f"Failed to parse JSON restaurant check from response.text: {parse_err}")
                 return None
        else:
             logger.error("No usable content found in Gemini response for restaurant check.")
             return None

    except Exception as e:
        logger.error(f"Error during Gemini API call for restaurant check: {e}", exc_info=True)
        return None

# --- Обновленная функция get_positions ---
def get_positions(extracted_text: str) -> Optional[Positions]:
    if not extracted_text:
        logger.warning("No extracted text provided to get_positions.")
        # Возвращаем объект с значениями по умолчанию int
        return Positions(positions_list=[], total_amount_detected=0) # Используем 0

    # Обновленный промпт
    prompt = f"""
Анализируй следующий текст, извлеченный из изображения чека:
--- ТЕКСТ ЧЕКА ---
{extracted_text}
--- КОНЕЦ ТЕКСТА ЧЕКА ---""" + """

Твоя задача:
1.  Извлеки все позиции (блюда, напитки) с их ценами. Игнорируй строки типа "Итого", "Скидка", "Обслуживание", "НДС", "Официант" и т.п. Формируй результат как СПИСОК объектов в поле 'positions_list'. Каждый объект в списке должен содержать два поля: 'name' (строка, название позиции) и 'price' (**целое число int**, округленная цена в рублях). Если позиций нет, верни ПУСТОЙ СПИСОК `[]` для 'positions_list'. Старайся нормализовать названия.
2.  Найди и извлеки итоговую сумму чека. **ВСЕГДА возвращай поле 'total_amount_detected' как целое число int (округленная сумма в рублях).** Если итоговая сумма найдена, верни ее значение. Если итоговая сумма НЕ найдена, верни `0`.
3.  Верни результат СТРОГО в формате JSON, соответствующем структуре: {{ "positions_list": [{{ "name": "...", "price": ЦЕЛОЕ_ЧИСЛО }}], "total_amount_detected": ЦЕЛОЕ_ЧИСЛО }}. **Оба поля ('positions_list', 'total_amount_detected') ДОЛЖНЫ присутствовать в ответе.** Не добавляй никаких других пояснений или текста вне JSON.
"""
    try:
        model = get_gemini_model()
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=Positions # Используем модель с int
            )
        )
        # ... (логика парсинга и валидации остается прежней, Pydantic обработает int) ...
        if hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts') and response.candidates[0].content.parts:
             json_text = response.candidates[0].content.parts[0].text
             logger.info(f"Received JSON from Gemini for positions/total: {json_text[:500]}...")
             parsed_data = json.loads(json_text)
             try:
                 positions_obj = Positions(**parsed_data)
                 if not isinstance(positions_obj.positions_list, list):
                     logger.warning("Parsed 'positions_list' is not a list. Setting to empty list.")
                     positions_obj.positions_list = []
                 logger.info(f"Successfully parsed positions/total: {len(positions_obj.positions_list)} items, total={positions_obj.total_amount_detected}")
                 return positions_obj
             except ValidationError as e:
                 logger.error(f"Pydantic validation failed for positions/total: {e}. JSON: {json_text}")
                 return None
        elif response.text: # Fallback
             try:
                 logger.info(f"Trying to parse positions/total from response.text: {response.text[:500]}...")
                 parsed_data = json.loads(response.text)
                 try:
                     positions_obj = Positions(**parsed_data)
                     if not isinstance(positions_obj.positions_list, list):
                         logger.warning("Parsed 'positions_list' from response.text is not a list. Setting to empty list.")
                         positions_obj.positions_list = []
                     logger.info(f"Successfully parsed positions/total from response.text: {len(positions_obj.positions_list)} items, total={positions_obj.total_amount_detected}")
                     return positions_obj
                 except ValidationError as e:
                     logger.error(f"Pydantic validation failed for positions/total response.text: {e}. JSON: {response.text}")
                     return None
             except Exception as parse_err:
                 logger.error(f"Failed to parse JSON positions/total from response.text: {parse_err}")
                 return None
        else:
             logger.error("No usable content found in Gemini response for positions/total.")
             return None

    except Exception as e:
        logger.error(f"Error during Gemini API call for positions/total: {e}", exc_info=True)
        return None

# --- Обновленная функция get_recommendations ---
def get_recommendations(extracted_text: str, num_people: int, tea_money: float, item_assignments: Dict[str, List[str]]) -> Optional[Recommendation]:
    if not extracted_text or num_people <= 0:
        logger.warning("Invalid input for get_recommendations.")
        return None

    assignments_str = "\n".join([f"- {name}: {', '.join(items)}" for name, items in item_assignments.items()])
    if not assignments_str:
        assignments_str = "Распределение блюд по людям не указано."

    tea_money_int = int(round(tea_money))

    # --- ОБНОВЛЕННЫЙ ПРОМПТ без описаний ---
    prompt = f"""
Проанализируй счет из ресторана/кафе и рассчитай варианты его разделения на {num_people} человек.

--- ТЕКСТ СЧЕТА ---
{extracted_text}
--- КОНЕЦ ТЕКСТА СЧЕТА ---

--- ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ---
- Количество человек: {num_people}
- Желаемые чаевые (добавить к итогу, если не включены): {tea_money_int} RUB (целое число). Проверь, нет ли строки "Сервисный сбор" или "Чаевые" с этой же суммой в тексте счета - если есть, НЕ добавляй эти {tea_money_int} повторно.
- Кто что ел/пил (если указано):
{assignments_str}

--- ЗАДАЧА ---
Рассчитай ИТОГОВУЮ сумму к оплате (с учетом скидок из чека и добавленных чаевых, если они не были включены), **округленную до целых рублей (int)**, и помести ее в поле `final_total_calculated`.

Рассчитай доли для КАЖДОГО человека по следующим методам деления (все суммы округляй до целых рублей):
1.  `equally`: Разделить итоговую сумму поровну.
2.  `who_more_eat_then_more_pay`: Разделить так, чтобы те, кто съел БОЛЬШЕ позиций (по количеству штук), заплатили больше. Если распределение не указано, используй равное деление.
3.  `who_more_cost_then_more_pay`: Разделить так, чтобы те, кто заказал на БОЛЬШУЮ СУММУ (сумма их блюд), заплатили больше. Если распределение не указано, используй равное деление.
4.  `proportional_division_by_the_cost_of_orders`: Разделить итоговую сумму ПРОПОРЦИОНАЛЬНО стоимости заказа каждого человека. Если распределение не указано, используй равное деление.

Сформируй СПИСОК объектов `peoples_list`. Каждый объект в списке должен представлять одного человека и иметь два поля:
    - `name`: Имя человека (из `item_assignments`, если есть, иначе используй "Человек 1", "Человек 2" и т.д.).
    - `shares`: Объект со следующими полями (все **целые числа int**, округленные рубли): `equally`, `who_more_eat_then_more_pay`, `who_more_cost_then_more_pay`, `proportional_division_by_the_cost_of_orders`.

Верни результат СТРОГО в формате JSON, соответствующем структуре:""" + """
{
  "peoples_list": [
    {
      "name": "Имя1",
      "shares": {
        "equally": ЦЕЛОЕ,
        "who_more_eat_then_more_pay": ЦЕЛОЕ,
        "who_more_cost_then_more_pay": ЦЕЛОЕ,
        "proportional_division_by_the_cost_of_orders": ЦЕЛОЕ
      }
    },
    {
      "name": "Имя2",
      "shares": {
        "equally": ЦЕЛОЕ,
        "who_more_eat_then_more_pay": ЦЕЛОЕ,
        "who_more_cost_then_more_pay": ЦЕЛОЕ,
        "proportional_division_by_the_cost_of_orders": ЦЕЛОЕ
      }
    }
  ]
}
и так далее
**Все числовые значения сумм должны быть ЦЕЛЫМИ ЧИСЛАМИ (int).** Не добавляй никаких других пояснений или текста вне JSON. Валюта по умолчанию - RUB.
"""
    # --- КОНЕЦ ОБНОВЛЕННОГО ПРОМПТА ---
    try:
        client = genai_module.Client(api_key=os.getenv('GOOGLE_API_KEY'))

        response_schema = {
            "type": "object",
            "properties": {
                "peoples_list": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "shares": {
                                "type": "object",
                                "properties": {
                                    "equally": {"type": "integer"},
                                    "who_more_eat_then_more_pay": {"type": "integer"},
                                    "who_more_cost_then_more_pay": {"type": "integer"},
                                    "proportional_division_by_the_cost_of_orders": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            }
        }

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': response_schema,
            },
        )

        logger = logging.getLogger(__name__)

        try:
            # Попытка получить объект Recommendation
            if hasattr(response, 'parsed') and isinstance(response.parsed, Recommendation):
                recommendation_obj = response.parsed
            else:
                logger.error("Failed to access parsed Recommendation object. Attempting manual JSON parsing.")
                raw_text = None

                # Извлекаем текстовый ответ
                if hasattr(response, 'text') and response.text:
                    raw_text = response.text
                elif (hasattr(response, 'candidates') and response.candidates and 
                    hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts') and 
                    response.candidates[0].content.parts):
                    raw_text = response.candidates[0].content.parts[0].text

                if raw_text:
                    logger.info(f"Raw response text received: {raw_text[:1000]}...")

                    # Попытка распарсить JSON вручную
                    try:
                        parsed_data = json.loads(raw_text)

                        # Создаем объект через Pydantic
                        recommendation_obj = Recommendation(**parsed_data)

                    except (json.JSONDecodeError, ValidationError) as parse_err:
                        logger.error(f"Failed to parse response into Recommendation: {parse_err}")
                        return None
                else:
                    logger.error("Could not retrieve raw response text.")
                    return None

            # Проверяем список людей
            if not isinstance(recommendation_obj.peoples_list, list):
                logger.warning("Parsed 'peoples_list' is not a list. Setting to empty list.")
                recommendation_obj.peoples_list = []

            logger.info(f"Successfully accessed parsed recommendations. People count: {len(recommendation_obj.peoples_list)}")

            return recommendation_obj

        except Exception as e:
            logger.error(f"Error during Gemini API call for recommendations: {e}", exc_info=True)
            return None


    except Exception as e:
        logger.error(f"Error during Gemini API call for recommendations: {e}", exc_info=True)
        return None


# --- Маршруты Flask ---

@app.route('/favicon.ico')
def favicon():
    # Убедитесь, что favicon.png находится в static/
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.png', mimetype='image/png')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/share')
def share():
    # Эта страница может больше не понадобиться в старом виде,
    # но оставим маршрут, если она используется для чего-то еще.
    return render_template('share.html')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


# --- Обновленный маршрут /preprocess_receipt ---
@app.route('/preprocess_receipt', methods=['POST'])
def preprocess_receipt():
    image_file = request.files.get('receipt_image')
    if not image_file:
        logger.warning("Preprocess request failed: No image file provided.")
        return jsonify({'error': 'No image file provided'}), 400
    original_filename = image_file.filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)

    try:
        image_file.save(filepath)
        logger.info(f"Image saved temporarily to {filepath}")

        # Шаг 1: OCR
        extracted_text = process_image_with_gemini(filepath)
        if extracted_text is None:
             logger.error("OCR processing failed.")
             return jsonify({'error': 'Failed to process image with OCR'}), 500
        if not extracted_text:
             logger.warning("OCR resulted in empty text.")
             # Возвращаем с значениями по умолчанию
             return jsonify({"positions_list": [], "is_restaurant": False, "extracted_text": "", "total_amount_detected": 0.0}), 200

        logger.info(f"OCR extracted text (first 100 chars): {extracted_text[:100]}")

        # Шаг 2: Проверка на ресторан
        is_restaurant_flag = is_restaurant_check(extracted_text)

        # Обработка ошибки при проверке или если это не ресторан
        if is_restaurant_flag is None:
            logger.error("Failed to determine if image is a restaurant check.")
            # Можно вернуть ошибку или считать, что это не ресторан
            # return jsonify({'error': 'Failed to analyze check type'}), 500
            is_restaurant_flag = False # Считаем не рестораном при ошибке
        elif is_restaurant_flag is False:
            logger.info("Image determined not to be a restaurant check.")
            # Возвращаем результат с флагом False и пустыми позициями
            return jsonify({"positions_list": [], "is_restaurant": False, "extracted_text": extracted_text, "total_amount_detected": 0.0}), 200

        # Шаг 3: Если это ресторан, извлекаем позиции и сумму
        logger.info("Check identified as restaurant, proceeding to get positions.")
        positions_data = get_positions(extracted_text)

        if positions_data is None:
            logger.error("Failed to get positions/total data from Gemini even though it's a restaurant check.")
            return jsonify({'error': 'Failed to extract items/total from the restaurant check'}), 500

        # Шаг 4: Собираем финальный ответ
        response_data = positions_data.dict()
        response_data['is_restaurant'] = True # Мы уже знаем, что это ресторан
        response_data['extracted_text'] = extracted_text
        logger.info(f"Preprocess successful. is_restaurant=True, items={len(response_data['positions_list'])}")
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error during preprocess_receipt: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred during preprocessing.'}), 500
    finally:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Temporary file {filepath} deleted.")
            except Exception as e:
                logger.error(f"Error deleting temporary file {filepath}: {e}")

# --- НОВЫЙ МАРШРУТ ДЛЯ РАСЧЕТА ---
@app.route('/calculate_split', methods=['POST'])
def calculate_split():
    """
    Эндпоинт для второго шага: расчет рекомендаций по делению.
    Принимает: JSON с 'extracted_text', 'num_people', 'tea_money', 'item_assignments'
    Возвращает: JSON с рекомендациями или ошибку.
    """
    try:
        data = request.get_json()
        if not data:
            logger.error("Calculate split request failed: No JSON data provided.")
            return jsonify({'error': 'No JSON data provided'}), 400

        extracted_text = data.get('extracted_text')
        num_people_str = data.get('num_people')
        tea_money_str = data.get('tea_money', '0') # По умолчанию 0
        item_assignments = data.get('item_assignments') # Ожидаем Dict[str, List[str]]

        # Валидация входных данных
        if not extracted_text:
            logger.error("Calculate split request failed: Missing extracted_text.")
            return jsonify({'error': 'Missing extracted_text'}), 400
        if not num_people_str:
            logger.error("Calculate split request failed: Missing num_people.")
            return jsonify({'error': 'Missing num_people'}), 400
        if not isinstance(item_assignments, dict):
             # Если распределения нет, передаем пустой словарь
             item_assignments = {}
             logger.warning("item_assignments not provided or not a dict, using empty for calculation.")
             # Не возвращаем ошибку, просто считаем без распределения

        try:
            num_people = int(num_people_str)
            if num_people <= 0:
                raise ValueError("Number of people must be positive.")
        except ValueError:
            logger.error(f"Calculate split request failed: Invalid num_people value '{num_people_str}'.")
            return jsonify({'error': 'Invalid num_people value'}), 400

        try:
            # Заменяем запятую на точку для безопасности
            tea_money = float(str(tea_money_str).replace(',', '.'))
            if tea_money < 0:
                raise ValueError("Tea money cannot be negative.")
        except ValueError:
            logger.error(f"Calculate split request failed: Invalid tea_money value '{tea_money_str}'.")
            return jsonify({'error': 'Invalid tea_money value'}), 400

        logger.info(f"Calculating split for {num_people} people, tea: {tea_money}, assignments: {len(item_assignments)} people assigned.")

        # Получаем рекомендации (вызываем функцию get_recommendations)
        recommendations = get_recommendations(extracted_text, num_people, tea_money, item_assignments)

        if recommendations is None:
            logger.error("Failed to get recommendations from Gemini.")
            return jsonify({'error': 'Failed to generate splitting recommendations'}), 500

        logger.info("Recommendations generated successfully.")
        # Возвращаем результат в виде словаря
        return jsonify(recommendations.dict()), 200

    except Exception as e:
        logger.error(f"Error during calculate_split: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred during calculation.'}), 500

# --- КОНЕЦ ДОБАВЛЕНИЯ ---

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Установите debug=False для продакшена
    app.run(host='0.0.0.0', port=port, debug=True)

# --- END OF FILE app.py ---