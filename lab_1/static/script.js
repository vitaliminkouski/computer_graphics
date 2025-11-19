// Глобальный флаг, чтобы избежать "гонки" обновлений
let isUpdating = false;

// Помощники для обновления UI

 //Обновляет все поля ввода, ползунки и палитры на основе данных с сервера

function updateUI(data) {
    isUpdating = true; // Ставим флаг, что мы обновляем UI

    const { rgb, cmyk, hls } = data;

    // Обновляем RGB
    document.getElementById('rgb-r-slider').value = rgb.r;
    document.getElementById('rgb-r-input').value = rgb.r;
    document.getElementById('rgb-g-slider').value = rgb.g;
    document.getElementById('rgb-g-input').value = rgb.g;
    document.getElementById('rgb-b-slider').value = rgb.b;
    document.getElementById('rgb-b-input').value = rgb.b;

    // Обновляем CMYK
    document.getElementById('cmyk-c-slider').value = cmyk.c;
    document.getElementById('cmyk-c-input').value = cmyk.c;
    document.getElementById('cmyk-m-slider').value = cmyk.m;
    document.getElementById('cmyk-m-input').value = cmyk.m;
    document.getElementById('cmyk-y-slider').value = cmyk.y;
    document.getElementById('cmyk-y-input').value = cmyk.y;
    document.getElementById('cmyk-k-slider').value = cmyk.k;
    document.getElementById('cmyk-k-input').value = cmyk.k;

    // Обновляем HLS
    document.getElementById('hls-h-slider').value = hls.h;
    document.getElementById('hls-h-input').value = hls.h;
    document.getElementById('hls-l-slider').value = hls.l; // Lightness
    document.getElementById('hls-l-input').value = hls.l; // Lightness
    document.getElementById('hls-s-slider').value = hls.s; // Saturation
    document.getElementById('hls-s-input').value = hls.s; // Saturation

    // Обновляем главный свотч и палитру
    const rgbString = `rgb(${rgb.r}, ${rgb.g}, ${rgb.b})`;
    document.getElementById('color-swatch').style.backgroundColor = rgbString;
    document.getElementById('html-color-picker').value = rgbToHex(rgb.r, rgb.g, rgb.b);

    // Снимаем флаг через короткое время
    setTimeout(() => { isUpdating = false; }, 50);
}

// Функция вызова API (FastAPI Backend)


 // Собирает данные из измененной модели и отправляет на сервер
async function sendUpdate(modelName, fieldset) {
    if (isUpdating) return; // Не делаем ничего, если UI сейчас обновляется

    const values = {};
    // Собираем все значения (поля data-field) из этой модели
    fieldset.querySelectorAll('[data-field]').forEach(el => {
        values[el.dataset.field] = el.value;
    });

    // Формируем данные для отправки на /convert
    const formData = new FormData();
    formData.append('source_model', modelName);
    formData.append('values', JSON.stringify(values));

    try {
        const response = await fetch('/convert', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        // Обновляем ВЕСЬ интерфейс новыми данными
        updateUI(data);

    } catch (error) {
        console.error('Error during color conversion:', error);
    }
}

// Вспомогательные функции (для палитры)

function rgbToHex(r, g, b) {
    return "#" + [r, g, b].map(x => {
        const hex = x.toString(16);
        return hex.length === 1 ? "0" + hex : hex;
    }).join('');
}

function hexToRgb(hex) {
    let r = 0, g = 0, b = 0;
    if (hex.length == 4) { // #RGB
        r = parseInt(hex[1] + hex[1], 16);
        g = parseInt(hex[2] + hex[2], 16);
        b = parseInt(hex[3] + hex[3], 16);
    } else if (hex.length == 7) { // #RRGGBB
        r = parseInt(hex[1] + hex[2], 16);
        g = parseInt(hex[3] + hex[4], 16);
        b = parseInt(hex[5] + hex[6], 16);
    }
    return { r, g, b };
}

// Назначение слушателей событий

document.addEventListener('DOMContentLoaded', () => {

    // Инициализируем UI начальными данными с сервера
    updateUI(initialData);

    // Слушатель для всех <fieldset>
    // Используем 'input' для ползунков (плавное изменение)
    // и 'change' для полей ввода (при потере фокуса)
    ['rgb', 'cmyk', 'hls'].forEach(modelName => { // <--- Обновлено на HLS
        const fieldset = document.getElementById(`model-${modelName}`);

        // Слушаем ползунки (input - при любом движении)
        fieldset.querySelectorAll('.slider').forEach(slider => {
            slider.addEventListener('input', () => {
                // Синхронизируем парное поле ввода
                document.getElementById(slider.id.replace('-slider', '-input')).value = slider.value;
                sendUpdate(modelName, fieldset);
            });
        });

        // Слушаем поля ввода (change - при потере фокуса)
        fieldset.querySelectorAll('.input-field').forEach(input => {
            input.addEventListener('change', () => {
                // Синхронизируем парный ползунок
                document.getElementById(input.id.replace('-input', '-slider')).value = input.value;
                sendUpdate(modelName, fieldset);
            });
        });
    });

    // Слушатель для HTML5-палитры
    document.getElementById('html-color-picker').addEventListener('input', (e) => {
        const rgb = hexToRgb(e.target.value);
        const fieldset = document.getElementById('model-rgb');

        // Вручную "симулируем" изменение RGB
        // и отправляем его на сервер
        document.getElementById('rgb-r-input').value = rgb.r;
        document.getElementById('rgb-g-input').value = rgb.g;
        document.getElementById('rgb-b-input').value = rgb.b;
        document.getElementById('rgb-r-slider').value = rgb.r;
        document.getElementById('rgb-g-slider').value = rgb.g;
        document.getElementById('rgb-b-slider').value = rgb.b;

        sendUpdate('rgb', fieldset);
    });
});