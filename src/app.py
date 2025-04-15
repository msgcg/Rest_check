from flask import Flask, request, render_template, jsonify, send_from_directory
import os,re
import google.generativeai as genai
from google import genai as genai_module
from ocr_module import process_image_with_gemini
from pydantic import BaseModel, ValidationError  
from typing import Dict, List, Optional
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Убедитесь, что папка uploads существует
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---  Pydantic Модели ---

class RestaurantCheckResult(BaseModel):
    is_restaurant: bool

class PositionItem(BaseModel):
    name: str
    price: int

class Positions(BaseModel):
    positions_list: List[PositionItem]

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




# --- Настройка Gemini ---
def get_gemini_model(model_name="models/gemini-2.0-flash"):
    # ... (код функции без изменений) ...
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set.")
        raise ValueError("API key not configured.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

# --- функция для проверки ---
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

def get_positions(extracted_text: str) -> Optional[Positions]:
    if not extracted_text:
        logger.warning("No extracted text provided to get_positions.")
        return Positions(positions_list=[]) # Возвращаем пустой список

    # --- ИЗМЕНЕНО: Упрощенный промпт ---
    prompt = f"""
Анализируй следующий текст, извлеченный из изображения чека:
--- ТЕКСТ ЧЕКА ---
{extracted_text}
--- КОНЕЦ ТЕКСТА ЧЕКА ---""" + """

Твоя задача:
1.  Извлеки все позиции (блюда, напитки) с их ценами. Игнорируй строки типа "Итого", "Скидка", "Обслуживание", "НДС", "Официант" и т.п. Формируй результат как СПИСОК объектов в поле 'positions_list'. Каждый объект в списке должен содержать два поля: 'name' (строка, название позиции) и 'price' (**целое число int**, округленная цена в рублях). Если позиций нет, верни ПУСТОЙ СПИСОК `[]` для 'positions_list'. Старайся нормализовать названия.
2.  Верни результат СТРОГО в формате JSON, соответствующем структуре: {{ "positions_list": [{{ "name": "...", "price": ЦЕЛОЕ_ЧИСЛО }}] }}. **Только поле 'positions_list' должно присутствовать в ответе.** Не добавляй никаких других пояснений или текста вне JSON.
3.  Любые кавычки (одинарные и двойные) и другие символы, которые могут вызвать ошибки типа Invalid or unexpected token в JavaScript, не должны присутствовать в твоем ответе, замени на что-то другое или удали.
"""
    try:
        model = get_gemini_model()
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                # response_schema=Positions # Можно использовать Pydantic модель
            )
        )

        positions_obj: Optional[Positions] = None

        # --- Логика парсинга ответа (остается похожей, но ожидает только positions_list) ---
        if hasattr(response, 'text') and response.text:
             json_text = response.text
             logger.info(f"Received JSON from Gemini for positions: {json_text[:500]}...")
             # Удаляем возможные артефакты ```json ... ```
             cleaned_json_text = re.sub(r'^```json\s*|\s*```$', '', json_text, flags=re.MULTILINE | re.DOTALL).strip()
             try:
                 parsed_data = json.loads(cleaned_json_text)
                 # Валидируем структуру с помощью Pydantic
                 positions_obj = Positions(**parsed_data)
                 logger.info(f"Successfully parsed positions: {len(positions_obj.positions_list)} items")

             except (json.JSONDecodeError, ValidationError) as e:
                 logger.error(f"Pydantic validation or JSON parsing failed for positions: {e}. JSON: {cleaned_json_text}")
                 return None # Ошибка валидации или парсинга, выходим
        else:
             logger.error("No usable content found in Gemini response for positions.")
             return None # Нет данных от модели, выходим

        # --- Очистка имен позиций (остается без изменений) ---
        if positions_obj and isinstance(positions_obj.positions_list, list):
            cleaned_count = 0
            for item in positions_obj.positions_list:
                if isinstance(item.name, str):
                    original_name = item.name
                    item.name = re.sub(r'[&"\'<>`]', '', item.name) # Удаляем небезопасные символы
                    if item.name != original_name:
                        cleaned_count += 1
                        logger.debug(f"Cleaned item name: '{original_name}' -> '{item.name}'")
            if cleaned_count > 0:
                logger.info(f"Cleaned names for {cleaned_count} position(s).")
        elif positions_obj and not isinstance(positions_obj.positions_list, list):
             logger.warning("Parsed 'positions_list' is not a list after validation. Setting to empty list.")
             positions_obj.positions_list = []

        return positions_obj

    except Exception as e:
        logger.error(f"Error during Gemini API call or processing for positions: {e}", exc_info=True)
        return None

def get_total_amount(extracted_text: str) -> int:
    """Извлекает итоговую сумму из текста чека как целое число."""
    if not extracted_text:
        logger.warning("No extracted text provided to get_total_amount.")
        return 0

    prompt = f"""
Тебе дан текст чека:
---Начало текста чека---
{extracted_text}
---Конец текста чека---
Извлеки из этого чека итоговую сумму (обычно находится в поле "Итого", "ИТОГ", "ВСЕГО К ОПЛАТЕ" или похожем).
Ответ выдай СТРОГО в формате JSON с одним полем "total_amount", значение которого - ЦЕЛОЕ ЧИСЛО (int). Если в чеке указана десятичная часть суммы, округли до ближайшего целого числа рублей. Если итоговая сумма не найдена, верни 0.
Пример ответа: {{ "total_amount": 1234 }}
Не давай никаких пояснений, только JSON."""

    try:
        model = get_gemini_model()
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                # response_schema={"type": "object", "properties": {"total_amount": {"type": "integer"}}} # Можно указать схему
            ),
        )

        # Парсинг ответа
        if hasattr(response, 'text') and response.text:
            json_text = response.text
            logger.info(f"Received JSON from Gemini for total amount: {json_text}")
            # Удаляем возможные артефакты ```json ... ```
            cleaned_json_text = re.sub(r'^```json\s*|\s*```$', '', json_text, flags=re.MULTILINE | re.DOTALL).strip()
            try:
                parsed_data = json.loads(cleaned_json_text)
                total_amount = parsed_data.get("total_amount")
                if isinstance(total_amount, int):
                    logger.info(f"Successfully parsed total amount: {total_amount}")
                    return total_amount
                elif isinstance(total_amount, (float, str)): # Попытка преобразовать, если пришло не int
                    try:
                        amount_int = int(round(float(str(total_amount).replace(',','.'))))
                        logger.warning(f"Parsed total_amount was not int ({type(total_amount)}), converted to: {amount_int}")
                        return amount_int
                    except (ValueError, TypeError):
                         logger.error(f"Could not convert parsed total_amount '{total_amount}' to int.")
                         return 0
                else:
                    logger.error("Field 'total_amount' is missing or not a number in parsed data.")
                    return 0
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"JSON parsing or validation failed for total amount: {e}. JSON: {cleaned_json_text}")
                return 0
        else:
            logger.error("No usable content found in Gemini response for total amount.")
            return 0

    except Exception as e:
        logger.error(f"Error during Gemini API call for total amount: {e}", exc_info=True)
        return 0

def get_recommendations(extracted_text: str, num_people: int, tea_money: float, item_assignments: Dict[str, List[str]]) -> Optional[Recommendation]:
    if not extracted_text or num_people <= 0:
        logger.warning("Invalid input for get_recommendations.")
        return None

    assignments_str = "\n".join([f"- {name}: {', '.join(items)}" for name, items in item_assignments.items()])
    if not assignments_str:
        assignments_str = "Распределение блюд по людям не указано."

    tea_money_int = int(round(tea_money))


    prompt = f"""
Проанализируй счет из ресторана/кафе и рассчитай варианты его разделения на {num_people} человек.

--- ТЕКСТ СЧЕТА ---
{extracted_text}
--- КОНЕЦ ТЕКСТА СЧЕТА ---

--- ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ---
- Количество человек: {num_people}
- Желаемые чаевые (добавить к итогу, если не включены): {tea_money_int} (целое число рублей). Проверь, нет ли строк "Сервисный сбор", "Чаевые", или им подобных с этой же суммой (если округлять до целых рублей) в тексте счета - если есть, НЕ добавляй эти {tea_money_int} повторно.
- Кто что ел/пил (если указано):
{assignments_str}

--- ЗАДАЧА ---

Рассчитай доли для КАЖДОГО человека (с учетом скидок из чека и добавленных чаевых, если они не были включены в сам чек) по следующим методам деления (все суммы округляй до целых рублей):
1.  `equally`: Разделить итоговую сумму поровну.
2.  `who_more_eat_then_more_pay`: Разделить так, чтобы те, кто съел БОЛЬШЕ позиций (по количеству штук), заплатили больше. Если распределение блюд по людям не указано, используй равное деление.
3.  `who_more_cost_then_more_pay`: Разделить так, чтобы те, кто заказал на БОЛЬШУЮ СУММУ (сумма их блюд), заплатили больше. Если распределение блюд по людям не указано, используй равное деление.
4.  `proportional_division_by_the_cost_of_orders`: Разделить итоговую сумму ПРОПОРЦИОНАЛЬНО стоимости заказа каждого человека. Если распределение блюд по людям не указано, используй равное деление.

Сформируй СПИСОК объектов `peoples_list`. Каждый объект в списке должен представлять одного человека и иметь два поля:
    - `name`: Имя человека (из `item_assignments`, если есть, иначе используй "Человек 1", "Человек 2" и т.д.).
    - `shares`: Объект со следующими полями (все **целые числа int**, округленные до целого деньги): `equally`, `who_more_eat_then_more_pay`, `who_more_cost_then_more_pay`, `proportional_division_by_the_cost_of_orders`.

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
**Все числовые значения сумм должны быть ЦЕЛЫМИ ЧИСЛАМИ (int).** Не добавляй никаких других пояснений или текста вне JSON. Валюта по умолчанию, если другая явно не указана в чеке - Российский рубль.
"""
 
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
            # Попытка получить объект Recommendation вручную
            logger.error("Direct parsing of Recommendation object. Skipping attribute check.")
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
                    recommendation_obj = None
            else:
                logger.error("Could not retrieve raw response text.")
                recommendation_obj = None


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
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.png', mimetype='image/png')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/share')
def share():
    return render_template('share.html')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


# --- маршрут /preprocess_receipt ---
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
             # Возвращаем пустые данные, но с успехом
             return jsonify({"positions_list": [], "is_restaurant": False, "extracted_text": "", "total_amount_detected": 0}), 200

        logger.info(f"OCR extracted text (first 100 chars): {extracted_text[:100]}...")

        # Шаг 2: Проверка на ресторан
        is_restaurant_flag = is_restaurant_check(extracted_text)

        if is_restaurant_flag is None:
            logger.error("Failed to determine if image is a restaurant check.")
            is_restaurant_flag = False # Считаем не рестораном при ошибке
        elif is_restaurant_flag is False:
            logger.info("Image determined not to be a restaurant check.")
            # Возвращаем результат с флагом False и пустыми данными
            return jsonify({"positions_list": [], "is_restaurant": False, "extracted_text": extracted_text, "total_amount_detected": 0}), 200

        # --- Шаг 3: Если это ресторан, извлекаем ПОЗИЦИИ ---
        logger.info("Check identified as restaurant, proceeding to get positions.")
        positions_data = get_positions(extracted_text)

        if positions_data is None:
            logger.error("Failed to get positions data from Gemini.")
            # Можно вернуть ошибку или пустой список позиций
            positions_data = Positions(positions_list=[]) # Возвращаем пустой список при ошибке
            # return jsonify({'error': 'Failed to extract items from the restaurant check'}), 500

        # --- Шаг 4: Извлекаем ИТОГОВУЮ СУММУ ОТДЕЛЬНО ---
        logger.info("Proceeding to get total amount.")
        total_amount = get_total_amount(extracted_text) # Возвращает int, 0 при ошибке

        # --- Шаг 5: Собираем финальный ответ ---
        response_data = positions_data.dict() # Получаем {'positions_list': [...]}
        response_data['is_restaurant'] = True
        response_data['extracted_text'] = extracted_text
        response_data['total_amount_detected'] = total_amount # Добавляем сумму

        logger.info(f"Preprocess successful. is_restaurant=True, items={len(response_data['positions_list'])}, total_amount={total_amount}")
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error during preprocess_receipt: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred during preprocessing.'}), 500
    finally:
        # Удаляем временный файл
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Temporary file {filepath} deleted.")
            except Exception as e:
                logger.error(f"Error deleting temporary file {filepath}: {e}")

# --- МАРШРУТ ДЛЯ РАСЧЕТА ---
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
    # Установите debug=True для отладки
    app.run(host='0.0.0.0', port=port, debug=False)

