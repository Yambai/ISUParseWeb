document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');
  const menuToggle = document.getElementById('menu-toggle');
  const refreshButton = document.getElementById('refresh');
  const semesterTitle = document.getElementById('semester-title');
  const cardsContainer = document.getElementById('cards-container');

  console.log('script.js loaded, currentSemester:', window.currentSemester);

  // Открытие/закрытие сайдбара
  menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('active');
  });

  // Закрытие сайдбара при клике вне его
  document.addEventListener('click', (e) => {
    if (!sidebar.contains(e.target) && !menuToggle.contains(e.target) && sidebar.classList.contains('active')) {
      sidebar.classList.remove('active');
    }
  });

  // Обновление оценок при нажатии на "Обновить"
  refreshButton.addEventListener('click', () => {
    const spinner = refreshButton.querySelector('.loading-spinner');
    const icon = refreshButton.querySelector('.nav-icon');
    const text = refreshButton.querySelector('.nav-text');
    spinner.style.display = 'inline';
    if (icon) icon.style.display = 'none';
    if (text) text.style.display = 'none';

    fetch('/refresh_marks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          alert(data.error);
          return;
        }
        semesterTitle.textContent = `Оценки по семестрам (Семестр ${data.semester})`;
        cardsContainer.innerHTML = '';
        data.cards.forEach(card => {
          const cardHtml = `
            <div class="card subject-card">
              <h3>${card.subject}</h3>
              ${card.scores.length ? `<div class="scores">${card.scores.join('')}</div>` : '<p>Нет оценок</p>'}
            </div>
          `;
          cardsContainer.insertAdjacentHTML('beforeend', cardHtml);
        });
      })
      .catch(error => {
        console.error('Ошибка при обновлении данных:', error);
        alert('Произошла ошибка при обновлении данных.');
      })
      .finally(() => {
        spinner.style.display = 'none';
        if (icon) icon.style.display = window.innerWidth <= 600 ? 'inline' : 'none';
        if (text) text.style.display = window.innerWidth <= 600 ? 'none' : 'inline';
      });
  });

  // Выбор семестра через AJAX
  const semesterLinks = document.querySelectorAll('.semester-card');
  console.log('Found semester links:', semesterLinks.length);
  semesterLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const semester = link.getAttribute('data-semester');
      console.log('Switching to semester:', semester);
      fetch(`/get_semester_data?semester=${semester}`)
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error('Error fetching semester data:', data.error);
            alert(data.error);
            return;
          }
          window.currentSemester = data.semester;
          console.log('Updated currentSemester:', window.currentSemester);
          semesterTitle.textContent = `Оценки по семестрам (Семестр ${data.semester})`;
          cardsContainer.innerHTML = '';
          data.cards.forEach(card => {
            const cardHtml = `
              <div class="card subject-card">
                <h3>${card.subject}</h3>
                ${card.scores.length ? `<div class="scores">${card.scores.join('')}</div>` : '<p>Нет оценок</p>'}
              </div>
            `;
            cardsContainer.insertAdjacentHTML('beforeend', cardHtml);
          });
          semesterLinks.forEach(l => l.classList.remove('active'));
          link.classList.add('active');
        })
        .catch(error => {
          console.error('Ошибка при загрузке данных:', error);
        });
    });
  });

  // Устанавливаем активный семестр при загрузке страницы
  semesterLinks.forEach(link => {
    if (parseInt(link.getAttribute('data-semester')) === window.currentSemester) {
      link.classList.add('active');
    }
  });
});

