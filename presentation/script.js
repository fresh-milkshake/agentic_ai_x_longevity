(function () {
    // Используем querySelectorAll для получения всех элементов с классом 'moving-pixel'
    const pixels = document.querySelectorAll('.moving-pixel');
    if (pixels.length === 0) return;

    const pixelData = {}; // Храним данные для каждого пикселя
    let animFrame = null;
    let isActive = false;

    function updateBounds(pixel) {
        const id = pixel.dataset.id || pixel.src; // Уникальный идентификатор для каждого пикселя
        if (!pixelData[id]) return;
        pixelData[id].width = pixel.offsetWidth || 72;
        pixelData[id].height = pixel.offsetHeight || 72;
    }

    function animate() {
        if (!isActive) return;

        pixels.forEach(pixel => {
            const id = pixel.dataset.id || pixel.src;
            if (!pixelData[id]) return;

            const slide = pixel.closest('.slides section.present');
            if (!slide || !slide.contains(pixel)) {
                pixel.style.display = 'none';
                return;
            }

            pixel.style.display = 'block';

            const slideRect = slide.getBoundingClientRect();
            const slideWidth = slideRect.width;
            const slideHeight = slideRect.height;

            let { x, y, dx, dy, width, height } = pixelData[id];

            // Проверка на столкновение с границами слайда
            if (x + dx < 0 || x + dx + width > slideWidth) {
                dx = -dx;
            }
            if (y + dy < 0 || y + dy + height > slideHeight) {
                dy = -dy;
            }

            x += dx;
            y += dy;

            // Ограничиваем координаты в пределах слайда
            x = Math.max(0, Math.min(x, slideWidth - width));
            y = Math.max(0, Math.min(y, slideHeight - height));

            // Обновляем позицию
            pixel.style.left = x + 'px';
            pixel.style.top = y + 'px';

            // Сохраняем новые значения
            pixelData[id] = { ...pixelData[id], x, y, dx, dy };
        });

        animFrame = requestAnimationFrame(animate);
    }

    function startAnimation() {
        if (isActive) return;
        isActive = true;
        cancelAnimationFrame(animFrame);
        animFrame = requestAnimationFrame(animate);
    }

    function stopAnimation() {
        isActive = false;
        cancelAnimationFrame(animFrame);
        pixels.forEach(pixel => {
            pixel.style.display = 'none';
        });
    }

    function onSlideChanged() {
        const idx = Reveal.getIndices();
        // Сброс позиций для всех пикселей на текущем слайде
        pixels.forEach(pixel => {
            const id = pixel.dataset.id || pixel.src;
            const slide = pixel.closest('.slides section.present');
            if (slide && slide.contains(pixel)) {
                // Сброс позиции
                pixelData[id] = {
                    x: 50,
                    y: 50,
                    dx: 2,
                    dy: 2,
                    width: pixel.offsetWidth || 72,
                    height: pixel.offsetHeight || 72
                };
                pixel.style.left = '50px';
                pixel.style.top = '50px';
                pixel.style.display = 'block';
            } else {
                pixel.style.display = 'none';
            }
        });

        if (document.querySelector('.slides section.present .moving-pixel')) {
            startAnimation();
        } else {
            stopAnimation();
        }
    }

    // Инициализация данных для каждого пикселя
    pixels.forEach(pixel => {
        const id = pixel.dataset.id || pixel.src;
        pixelData[id] = {
            x: 50,
            y: 50,
            dx: 2,
            dy: 2,
            width: pixel.offsetWidth || 72,
            height: pixel.offsetHeight || 72
        };
        pixel.style.position = 'absolute';
        pixel.style.display = 'none';
    });

    // Обработчики событий
    Reveal.on('slidechanged', onSlideChanged);
    window.addEventListener('resize', () => {
        pixels.forEach(pixel => updateBounds(pixel));
    });

    // Начальная проверка при загрузке
    setTimeout(() => {
        if (document.querySelector('.slides section.present .moving-pixel')) {
            startAnimation();
        } else {
            pixels.forEach(pixel => pixel.style.display = 'none');
        }
    }, 500);

})();