# **Приложение для распознавания текста на чеках ПоДЕЛИ!**


## **Обзор:**

Сервис использует технологию оптического распознавания символов (OCR) для извлечения текста из изображений чеков кафе и ресторанов, а затем предлагает рекомендации по разделению суммы счета между участниками трапезы.

---

## **Требования:**

- Flask
- requests
- google
- google.genai
- google-generativeai
- pydantic
- typing-extensions
- python-dotenv
- waitress (для продакшна)
---
## **Интеграция со Сбером:**
Сервис работает на полностью доступном и бесплатном Gemini API, но при необходимости можно легко перейти на модели от Сбера. Вот как это сделать:
*   Установите и подключите библиотеку ```openai```.
*   Найдите в коде ```app.py``` все функции для работы с искуственным интеллектом (отмечены комментариями).
*   На основании [документации GigaChat](https://developers.sber.ru/portal/products/gigachat-api) замените:
    * Подключение genai на openai
    * Gemini модели на GigaChat модели
* Вместо JSON schema и Pydantic моделей внедрите описание json вывода в переменную ```prompt```
## Теперь сервис работает на базе GigaChat
## **Настройка для запуска на сервере или личном пк:**

1.  **Клонируйте репозиторий:**
    *   Загрузите или скопируйте файлы проекта на ваш локальный компьютер или сервер.
        Если используется Git, команда:
        
        ```bash
        git clone https://github.com/msgcg/Rest_check
        ```

2.  **Установите необходимые пакеты:**
    *   Откройте терминал или командную строку в папке проекта.
    *   Создайте окружение (**Python 3.12+**):
        ```bash
        python -m venv venv
        source venv/bin/activate
        ```
        Или для Windows:

        ```pwsh
        python -m venv venv
        ./venv/scripts/activate.ps1
        ```
    после чего выполните установку записимостей:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Настройте переменные окружения:**
    *   Создайте в корневом каталоге проекта файл с именем `.env`.
    *   Добавьте в этот файл следующие строки, указав ваш ключ API от Gemini API:

        ```dotenv
        GOOGLE_API_KEY='ВАШ_GOOGLE_API_KEY'
        ENV=prod (или dev для отладки)
        PORT=5000
        DEBUG=False (или True для отладки)
        ```
        *(Замените `ВАШ_GOOGLE_API_KEY` на реальный ключ. Создайте папку `uploads` - она будет использоваться для временного хранения загруженных изображений чеков).*

4.  **Настройте доступ к Gemini API:**
    *   Google Gemini должен быть доступен с вашего IP адреса. Это может зависеть от DNS сервера, используемого в системе. По умолчанию хостинг ПоДЕЛИ! обеспечивает легальный доступ к Gemini API.
    

5.  **Запустите приложение:**
    *   В терминале или командной строке, находясь в папке проекта, выполните команду:
        ```bash
        python src/app.py
        ```
    *   После запуска приложение будет доступно в вашем веб-браузере по адресу, указанному в выводе Flask (обычно `http://127.0.0.1:5000/`).


## **Бинарный релиз:**
*   Мобильное приложение, работающее "из коробки" с любых IP, можно загрузить в Release
*   После коммита от авторизованного аккаунта приложение будет так же доступно на https://rest-check.onrender.com/ 


