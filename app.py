from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session
import json
import os
import random
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import datetime  # Для установки срока действия сессии

# Загрузка переменных окружения
load_dotenv()
app = Flask(__name__)
app.secret_key = "python_code_reading_practice_secret_key"

# Настройка Flask-Session для хранения в файлах
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "flask_session"  # Директория для хранения файлов сессий
app.config["SESSION_PERMANENT"] = True  # Делаем сессию постоянной
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=30)  # Срок хранения сессии

# Создаем директорию для хранения сессий, если она не существует
if not os.path.exists(app.config["SESSION_FILE_DIR"]):
    os.makedirs(app.config["SESSION_FILE_DIR"])

Session(app)  # Инициализация Flask-Session

# Load skills data
with open('skills.json', 'r', encoding='utf-8') as f:
    skills_data = json.load(f)

# Структура данных для прогресса пользователя по умолчанию
default_user_progress = {
    "completed_skills": [],
    "current_skill": "Комментарии и документация кода",  # Default starting skill
    "completed_exercises": {},
    "average_time": {},
    "success_rate": {},
    "completed_exercise_ids": {}
}


def get_user_progress():
    """Получает прогресс пользователя из сессии или создает новый"""
    if 'user_progress' not in session:
        session['user_progress'] = default_user_progress.copy()
    return session['user_progress']


def save_user_progress(progress):
    """Сохраняет прогресс пользователя в сессию"""
    session['user_progress'] = progress
    # Явно сохраняем сессию
    session.modified = True


def load_learning_material(skill_name):
    """Load the learning material for a specific skill"""
    try:
        with open(f'learning_materials/{skill_name.replace(" ", "_")}.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    except FileNotFoundError:
        print(f"Для материала \"{skill_name}\" не был обнаружен исходный файл.")


def evaluate_answer(user_explanation, exercise_code, learning_material, hidden_explanation=None,
                    expected_concepts=None):
    """Use LangChain to evaluate the user's explanation of the code"""
    # Initialize LangChain components
    llm = ChatOpenAI(temperature=0.3)

    prompt = PromptTemplate(
        input_variables=["learning_material", "code", "explanation", "hidden_explanation", "expected_concepts"],
        template="""
        Это приложение для практики чтения кода. В нем пользователь изучает материалы по программированию в Python.
        После изучения, пользователь ознакамливается с проверочным заданием и своими словами описывает код. 
        Ты опытный педагог и твоя задача оценить ответ пользователя. 

        На основе следующего учебного материала:
        {learning_material}

        Этого проверочного задания:
        {code}

        Правильного объяснения кода для полной картины:
        {hidden_explanation}

        Ключевых концепций, которые рекомендуемо к упоминанию:
        {expected_concepts}

        Оцени, демонстрирует ли объяснение пользователя понимание кода:
        {explanation}

        Ответьте строго в формате JSON:
        ```json
        {{
            "result": "SUCCESS" или "FAILURE",
            "feedback": "Ваш подробный отзыв, обращенный напрямую к пользователю",
            "recommendations": "Конкретные рекомендации по улучшению (если необходимо)",
            "covered_concepts": ["Список концепций, которые пользователь успешно раскрыл"],
            "missing_concepts": ["Список концепций, которые пользователь не раскрыл"]
        }}
        ```

        Важно: 
        - Весь отзыв и рекомендации должны быть на русском языке
        - Обращайтесь к пользователю напрямую (например, "Вы правильно поняли..." вместо "Пользователь правильно понял...")
        - Строго соблюдайте формат JSON
        - Дополнительным преимуществом (НО НЕ ОБЯЗАТЕЛЬНЫМ УСЛОВИЕМ) будет упоминание пользователем ключевых концепций.
        - Не требуй что бы в ответе было то чему не посвящен данный навык.
        - Уровень сложности выполнения задания должен быть 6 из 10.
        """
    )

    runnable = prompt | llm

    # Prepare the learning material summary
    material_summary = f"Topic: {learning_material['topic']}\nOverview: {learning_material['theory']['overview']}"

    # Format expected concepts for the prompt
    formatted_concepts = "\n".join([f"- {concept}" for concept in (expected_concepts or [])])

    # Get evaluation from LLM
    response = runnable.invoke({
        "learning_material": material_summary,
        "code": exercise_code,
        "explanation": user_explanation,
        "hidden_explanation": hidden_explanation,
        "expected_concepts": formatted_concepts
    })

    # Extract the response text
    response_text = response.content if hasattr(response, 'content') else str(response)

    # Extract JSON from the response
    try:
        # Find JSON content between triple backticks if present
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)

        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find any JSON-like structure
            json_match = re.search(r'({.*})', response_text, re.DOTALL)
            json_str = json_match.group(1) if json_match else response_text

        # Parse the JSON
        import json
        result_data = json.loads(json_str)

        success = result_data.get("result", "").upper() == "SUCCESS"
        feedback = result_data.get("feedback", "")
        recommendations = result_data.get("recommendations", "")
        covered_concepts = result_data.get("covered_concepts", [])
        missing_concepts = result_data.get("missing_concepts", [])

        # Combine feedback and recommendations
        complete_feedback = feedback
        if recommendations:
            complete_feedback += "<br><br>Рекомендации:<br>" + recommendations

        if covered_concepts:
            complete_feedback += "<br><br>Вы успешно раскрыли следующие концепции:<br>- " + "<br>- ".join(
                covered_concepts)

        if missing_concepts:
            complete_feedback += "<br><br>Не раскрытые концепции:<br>- " + "<br>- ".join(missing_concepts)

    except Exception as e:
        # Fallback if JSON parsing fails
        print(f"Error parsing LLM response as JSON: {e}")
        print(f"Raw response: {response_text}")

        # Simple fallback parsing
        success = "SUCCESS" in response_text.upper()
        complete_feedback = response_text
        covered_concepts = []
        missing_concepts = []

    return {
        "success": success,
        "feedback": complete_feedback,
        "covered_concepts": covered_concepts,
        "missing_concepts": missing_concepts
    }


def get_next_exercise(skill_name):
    """Get a practice exercise for the current skill that hasn't been completed yet"""
    user_progress = get_user_progress()
    material = load_learning_material(skill_name)

    if 'practice_examples' in material and 'examples' in material['practice_examples']:
        all_exercises = material['practice_examples']['examples']

        # Получаем список ID выполненных заданий для текущего навыка
        completed_ids = user_progress["completed_exercise_ids"].get(skill_name, [])

        # Отфильтровываем невыполненные задания
        available_exercises = [ex for ex in all_exercises if ex.get('id') not in completed_ids]

        if available_exercises:
            # Если есть невыполненные задания, выбираем одно из них
            return random.choice(available_exercises)
        elif all_exercises:
            # Если все задания выполнены, можно вернуть сообщение или случайное задание для повторения
            return {
                "code": "# Вы выполнили все задания для этого навыка!",
                "id": "completed_all",
                "description": "Поздравляем! Вы успешно выполнили все задания для этого навыка. Вы можете перейти к следующему навыку или повторить текущий."
            }

    return {"code": "# No exercises available for this skill"}


@app.route('/')
def index():
    user_progress = get_user_progress()
    current_skill = user_progress["current_skill"]
    material = load_learning_material(current_skill)
    total_exercises_in_skill = len(material['practice_examples']['examples'])
    completed_exercises_in_skill =  len(user_progress["completed_exercise_ids"].get(current_skill, []))
    return render_template('index.html',
                           skills=skills_data,
                           progress=user_progress,
                           current_skill_name=user_progress["current_skill"],
                           total_exercises_in_skill=total_exercises_in_skill,
                           completed_exercises_in_skill=completed_exercises_in_skill)


@app.route('/skill/<skill_name>')
def skill(skill_name):
    # Показывает только образовательный материал
    user_progress = get_user_progress()
    user_progress["current_skill"] = skill_name
    save_user_progress(user_progress)
    material = load_learning_material(skill_name)
    total_exercises_in_skill = len(material['practice_examples']['examples'])
    completed_exercises_in_skill =  len(user_progress["completed_exercise_ids"].get(skill_name, []))
    return render_template('skill_material.html',
                           skills=skills_data,
                           progress=user_progress,
                           material=material,
                           total_exercises_in_skill=total_exercises_in_skill,
                           completed_exercises_in_skill=completed_exercises_in_skill)


@app.route('/skill/<skill_name>/practice')
def practice(skill_name):
    # Показывает только проверочное задание
    user_progress = get_user_progress()
    user_progress["current_skill"] = skill_name
    save_user_progress(user_progress)
    material = load_learning_material(skill_name)
    exercise = get_next_exercise(skill_name)
    exercise['skill_name'] = skill_name
    total_exercises_in_skill = len(material['practice_examples']['examples'])
    completed_exercises_in_skill =  len(user_progress["completed_exercise_ids"].get(skill_name, []))
    return render_template('skill_practice.html',
                           skills=skills_data,
                           progress=user_progress,
                           material=material,
                           exercise=exercise,
                           skill_name=skill_name,
                           total_exercises_in_skill=total_exercises_in_skill,
                           completed_exercises_in_skill=completed_exercises_in_skill)


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    user_progress = get_user_progress()
    skill_name = user_progress.get('current_skill')
    exercise_id = request.form.get('exercise_id')
    user_explanation = request.form.get('explanation')

    # Проверка наличия идентификатора
    if not exercise_id:
        return jsonify({
            "success": False,
            "feedback": "Ошибка: идентификатор упражнения не найден",
            "covered_concepts": [],
            "missing_concepts": [],
            "next_exercise": None,
            "next_skill": user_progress["current_skill"]
        }), 400

    # Load the learning material
    material = load_learning_material(skill_name)

    # Find the current exercise by ID
    current_exercise = None
    for exercise in material['practice_examples']['examples']:
        if exercise.get('id') == exercise_id:
            current_exercise = exercise
            break

    # Если упражнение не найдено, возвращаем ошибку
    if not current_exercise:
        return jsonify({
            "success": False,
            "feedback": f"Ошибка: упражнение с идентификатором '{exercise_id}' не найдено",
            "covered_concepts": [],
            "missing_concepts": [],
            "next_exercise": get_next_exercise(skill_name),
            "next_skill": user_progress["current_skill"]
        }), 404

    # Get hidden explanation and expected concepts
    hidden_explanation = current_exercise.get('hidden_explanation')
    expected_concepts = current_exercise.get('expected_concepts')
    exercise_code = current_exercise.get('code')

    # Evaluate the answer using LangChain
    result = evaluate_answer(
        user_explanation,
        exercise_code,
        material,
        hidden_explanation,
        expected_concepts
    )

    # Update user progress
    if skill_name not in user_progress["completed_exercises"]:
        user_progress["completed_exercises"][skill_name] = 0
        user_progress["success_rate"][skill_name] = 0
        # Инициализируем словарь для отслеживания выполненных заданий
        if "completed_exercise_ids" not in user_progress:
            user_progress["completed_exercise_ids"] = {}
        if skill_name not in user_progress["completed_exercise_ids"]:
            user_progress["completed_exercise_ids"][skill_name] = []

    if result["success"]:
        user_progress["completed_exercises"][skill_name] += 1
        user_progress["success_rate"][skill_name] = (
                (user_progress["success_rate"][skill_name] *
                 (user_progress["completed_exercises"][skill_name] - 1) + 100) /
                user_progress["completed_exercises"][skill_name]
        )

        # Добавляем ID успешно выполненного задания в список
        if exercise_id not in user_progress["completed_exercise_ids"][skill_name]:
            user_progress["completed_exercise_ids"][skill_name].append(exercise_id)
    else:
        user_progress["success_rate"][skill_name] = (
                (user_progress["success_rate"][skill_name] *
                 user_progress["completed_exercises"][skill_name]) /
                (user_progress["completed_exercises"][skill_name] + 1)
        )

    # Проверяем, выполнены ли все задания для текущего навыка
    all_exercises = material['practice_examples']['examples']
    total_exercises = len(all_exercises)
    completed_exercises = len(user_progress["completed_exercise_ids"].get(skill_name, []))

    # Если все задания выполнены успешно
    next_skill = None
    if result["success"] and completed_exercises >= total_exercises:
        # Mark skill as completed
        if skill_name not in user_progress["completed_skills"]:
            user_progress["completed_skills"].append(skill_name)

        # Find next skill
        next_skill = find_next_skill(skill_name)
        if next_skill:
            user_progress["current_skill"] = next_skill

    # Сохраняем обновленный прогресс пользователя
    save_user_progress(user_progress)

    return jsonify({
        "success": result["success"],
        "feedback": result["feedback"],
        "covered_concepts": result.get("covered_concepts", []),
        "missing_concepts": result.get("missing_concepts", []),
        "next_exercise": get_next_exercise(skill_name),
        "next_skill": next_skill or user_progress["current_skill"],
        "skill_completed": completed_exercises >= total_exercises
    })


def find_next_skill(current_skill):
    """Find the next skill in the sequence"""
    found_current = False

    for category in skills_data:
        for skill in category["skills"]:
            if found_current:
                return skill["name"]
            if skill["name"] == current_skill:
                found_current = True

    return None  # No next skill found


@app.route('/reset_progress', methods=['POST'])
def reset_progress():
    """Сбрасывает прогресс пользователя"""
    session['user_progress'] = default_user_progress.copy()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
