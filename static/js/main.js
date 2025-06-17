document.addEventListener('DOMContentLoaded', function() {
    // Initialize progress chart if canvas exists
    const progressChartCanvas = document.getElementById('progressChart');
    if (progressChartCanvas) {
        // Фиксируем размер контейнера
        const chartContainer = progressChartCanvas.parentElement;
        if (chartContainer) {
            chartContainer.style.height = '250px';
            chartContainer.style.width = '100%';
            chartContainer.style.maxWidth = '300px';
            chartContainer.style.margin = '0 auto';
            chartContainer.style.position = 'relative';
        }

        // Установка фиксированных размеров для canvas
        progressChartCanvas.style.height = '250px';
        progressChartCanvas.style.width = '100%';
        progressChartCanvas.style.maxWidth = '300px';
        progressChartCanvas.style.margin = '0 auto';
        progressChartCanvas.style.display = 'block';

        // Установка физических размеров canvas для предотвращения масштабирования
        progressChartCanvas.width = 300;
        progressChartCanvas.height = 250;

        const ctx = progressChartCanvas.getContext('2d');

        // Get counts with fallbacks to 0
        const completedCount = document.querySelectorAll('.skill-item.completed').length || 0;
        const currentCount = 1; // Current skill
        const notStartedCount = document.querySelectorAll('.skill-item:not(.completed):not(.current)').length || 0;

        // Задержка создания диаграммы для обеспечения правильной отрисовки
        setTimeout(() => {
            const chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Completed', 'In Progress', 'Not Started'],
                    datasets: [{
                        data: [completedCount, currentCount, notStartedCount],
                        backgroundColor: [
                            '#2ecc71',
                            '#3498db',
                            '#ecf0f1'
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true, // Изменено на true
                    aspectRatio: 1.2, // Фиксированное соотношение сторон
                    cutout: '70%',
                    layout: {
                        padding: 0
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                boxWidth: 12,
                                padding: 10
                            }
                        },
                        tooltip: {
                            enabled: true
                        }
                    },
                    animation: {
                        duration: 500 // Сокращенное время анимации
                    }
                }
            });
        }, 100);
    }

    // Handle answer submission
    const answerForm = document.getElementById('answer-form');
    if (answerForm) {
        answerForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const submitBtn = document.getElementById('submit-btn');
            const feedbackDiv = document.getElementById('feedback');
            const nextExerciseBtn = document.getElementById('next-exercise');
            const nextSkillBtn = document.getElementById('next-skill');
            const backToMaterialBtn = document.getElementById('back-to-material');

            // Disable submit button and show loading state
            submitBtn.disabled = true;
            submitBtn.textContent = 'Проверяем...';

            // Get form data
            const formData = new FormData(answerForm);

            // Send AJAX request
            fetch('/submit_answer', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Re-enable submit button
                submitBtn.disabled = false;
                submitBtn.textContent = 'Проверить';

                // Show feedback
                feedbackDiv.innerHTML = data.feedback;
                feedbackDiv.classList.remove('hidden');

                // Handle success/failure
                if (data.success) {
                    feedbackDiv.classList.remove('failure');
                    feedbackDiv.classList.add('success');

                    // Показываем контейнер с кнопками
                    const nextButtonsContainer = document.getElementById('next-buttons');
                    if (nextButtonsContainer) {
                        nextButtonsContainer.classList.remove('hidden');
                    }

                    // Всегда показываем кнопку следующего задания при успехе
                    nextExerciseBtn.classList.remove('hidden');

                    // Проверяем, завершен ли навык полностью
                    if (data.skill_completed) {
                        console.log('Навык завершен:', data.skill_completed);
                        console.log('Следующий навык:', data.next_skill);
                        // Только если навык полностью завершен - показываем кнопку перехода к следующему навыку
                        nextSkillBtn.classList.remove('hidden');
                        // Обновляем ссылку на следующий навык
                        nextSkillBtn.href = `/skill/${data.next_skill}`;
                    } else {
                        // Если навык не завершен, убедимся что кнопка скрыта
                        nextSkillBtn.classList.add('hidden');
                    }
                } else {
                    feedbackDiv.classList.remove('success');
                    feedbackDiv.classList.add('failure');
                }

                // Всегда показываем кнопку возврата к материалу
                if (backToMaterialBtn) {
                    backToMaterialBtn.classList.remove('hidden');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Проверить';
                feedbackDiv.innerHTML = 'Произошла ошибка при отправке ответа. Пожалуйста, попробуйте еще раз.';
                feedbackDiv.classList.remove('hidden');
                feedbackDiv.classList.remove('success');
                feedbackDiv.classList.add('failure');
            });
        });

        // Настройка обработчика для кнопки "Следующее задание"
        const nextExerciseBtn = document.getElementById('next-exercise');
        if (nextExerciseBtn) {
            nextExerciseBtn.addEventListener('click', function() {
                // Перезагружаем текущую страницу для получения нового задания
                window.location.reload();
            });
        }
    }

    // Исправление кнопки "Вернуться к материалу"
    const backToMaterialBtn = document.getElementById('back-to-material');
    if (backToMaterialBtn) {
        // Получаем skill_name из URL
        const pathParts = window.location.pathname.split('/');
        const skillNameIndex = pathParts.indexOf('skill') + 1;

        if (skillNameIndex > 0 && skillNameIndex < pathParts.length) {
            const skillName = pathParts[skillNameIndex];
            // Формируем правильный URL для возврата к материалу
            backToMaterialBtn.href = `/skill/${skillName}`;
            console.log('Исправлен URL кнопки "Вернуться к материалу":', backToMaterialBtn.href);
        }
    }
});
