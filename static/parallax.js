document.addEventListener('DOMContentLoaded', () => {
  console.log('parallax.js loaded');
  // Эффект параллакса
  const parallaxVideos = document.querySelectorAll('.parallax-video');
  const parallaxShapes = document.querySelectorAll('.parallax-shape');

  // Объекты для хранения текущих позиций (для сглаживания)
  const currentPositions = {
    videos: new Map(),
    shapes: new Map()
  };

  // Инициализируем текущие позиции
  parallaxVideos.forEach(video => {
    currentPositions.videos.set(video, 0);
  });
  parallaxShapes.forEach(shape => {
    currentPositions.shapes.set(shape, 0);
  });

  // Коэффициент сглаживания (чем меньше, тем плавнее)
  const easing = 0.05;

  // Функция для обновления позиций с анимацией
  function updateParallax() {
    const scrollPosition = window.scrollY;

    // Обновляем позиции видео
    parallaxVideos.forEach(video => {
      const speed = video.classList.contains('video-1') ? 0.3 : 0.5;
      const targetOffset = scrollPosition * speed;
      const currentOffset = currentPositions.videos.get(video);
      // Сглаживание: текущая позиция приближается к целевой
      const newOffset = currentOffset + (targetOffset - currentOffset) * easing;
      video.style.transform = `translateY(${newOffset}px)`;
      currentPositions.videos.set(video, newOffset);
    });

    // Обновляем позиции фигур
    parallaxShapes.forEach(shape => {
      const speed = shape.classList.contains('shape-1') ? 0.2 : shape.classList.contains('shape-2') ? 0.4 : 0.3;
      const targetOffset = scrollPosition * speed;
      const currentOffset = currentPositions.shapes.get(shape);
      // Сглаживание: текущая позиция приближается к целевой
      const newOffset = currentOffset + (targetOffset - currentOffset) * easing;
      shape.style.transform = `translateY(${newOffset}px)`;
      currentPositions.shapes.set(shape, newOffset);
    });

    // Запрашиваем следующий кадр анимации
    requestAnimationFrame(updateParallax);
  }

  // Запускаем анимацию
  window.addEventListener('scroll', () => {
    // Просто вызываем updateParallax, чтобы начать анимацию
    // requestAnimationFrame сам позаботится о плавности
  });

  // Инициируем первый вызов
  requestAnimationFrame(updateParallax);
});