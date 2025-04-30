(function() {
    'use strict';

    // Функция для плавной прокрутки окна вниз
    function scrollToWindowBottomSmooth() {
        const scrollHeight = document.documentElement.scrollHeight;
        window.scrollTo({
            top: scrollHeight,
            behavior: 'smooth'
        });
        // console.log(`Scrolling window smoothly to: ${scrollHeight}`);
    }

    // --- Debounce Function (без изменений) ---
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait); // Используем переданное значение wait
        };
    }

    // Создаем debounced-версию функции прокрутки
    // Уменьшим немного задержку debounce для большей отзывчивости
    const debouncedScrollHandler = debounce(scrollToWindowBottomSmooth, 200);

    // --- Event Listeners ---

    // 1. Прокрутка после полной загрузки страницы
    window.addEventListener('load', () => {
        // Небольшая задержка после load
        setTimeout(scrollToWindowBottomSmooth, 150); // Чуть увеличим задержку на всякий случай

        // --- Setup ResizeObserver ---
        // Находим основной контейнер ПОСЛЕ загрузки DOM
        const mainContainer = document.querySelector('.container');

        if (mainContainer) {
            try {
                const resizeObserver = new ResizeObserver(entries => {
                    // Срабатывает, когда размер наблюдаемого элемента меняется
                    console.log('ResizeObserver detected .container size change.');
                    // Вызываем debounced-обработчик, чтобы не скроллить слишком часто
                    // во время быстрых изменений размера
                    debouncedScrollHandler();
                });

                // Начинаем наблюдение за основным контейнером
                resizeObserver.observe(mainContainer);
                console.log('ResizeObserver is watching .container');

            } catch (error) {
                console.error("ResizeObserver is not supported or failed:", error);
                // Можно добавить fallback на MutationObserver здесь, если нужна поддержка старых браузеров
                // setupMutationObserverFallback();
            }
        } else {
            console.warn('.container element not found. ResizeObserver not attached.');
            // setupMutationObserverFallback(); // Возможно, запустить MutationObserver как fallback?
        }

        // 2. Прокрутка при изменении РАЗМЕРА ОКНА (остается)
        window.addEventListener('resize', debouncedScrollHandler);

    }); // Конец window.load

    // (Опционально) Fallback с MutationObserver, если ResizeObserver не сработает
    /*
    function setupMutationObserverFallback() {
        console.warn('Using MutationObserver as fallback.');
        const observer = new MutationObserver((mutations) => {
            console.log('MutationObserver detected DOM change (fallback).');
            debouncedScrollHandler();
        });

        // Наблюдаем за body или более конкретным контейнером
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['style', 'class'] // Наблюдаем за изменениями стилей и классов
        });
    }
    */

})();