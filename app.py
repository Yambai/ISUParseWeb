import requests
from bs4 import BeautifulSoup
import fake_useragent
import secrets
import pickle
import re
import logging
import json
from datetime import timedelta

from flask import Flask, render_template, redirect, request, url_for, session, flash, jsonify

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class MyError(Exception):
    pass


class ISUParser:
    def __init__(self, login, password):
        self.name = "Yambai"
        self.session = requests.Session()
        self.login = login
        self.password = password
        self.headers = {'User-Agent': fake_useragent.UserAgent().random}
        self.cookies = {'PHPSESSID': f'{secrets.randbits(64)}'}
        self.all_marks = None
        self.table_headers = None

    def authorisation(self) -> requests.Session:
        logging.debug("Начало авторизации для пользователя: %s", self.login)
        session_req = self.session
        cookies = self.cookies
        headers = self.headers

        form_num_response = session_req.get('https://isu.uust.ru/login/', cookies=cookies, headers=headers).text
        logging.debug("Получен ответ с формы авторизации, длина: %d символов", len(form_num_response))
        soup = BeautifulSoup(form_num_response, 'html.parser')
        value = soup.find('input')['value']
        logging.debug("Извлечён form_num: %s", value)

        data = {'form_num': value, 'login': self.login, 'password': self.password}
        authorisation_request = session_req.post(url='https://isu.uust.ru', cookies=cookies, headers=headers, data=data,
                                                 allow_redirects=False)
        if authorisation_request.status_code == 200:
            logging.error("Авторизация не прошла, статус код: %s", authorisation_request.status_code)
            raise MyError("Авторизация не прошла. Логин или пароль не верный.")
        re_authorisation = session_req.post(url='https://isu.uust.ru', cookies=cookies, headers=headers, data=data)
        logging.debug("Авторизация прошла, получен HTML после редиректа, длина: %d", len(re_authorisation.text))
        soup = BeautifulSoup(re_authorisation.text, "html.parser")
        name_tag = soup.find('h4', class_='user-name')
        if name_tag:
            name = name_tag.text.split('\n')[0]
            self.name = ' '.join(name.split(' ')[:2])
            logging.debug("Имя пользователя после авторизации: %s", self.name)
        else:
            logging.warning("Не удалось извлечь имя пользователя из HTML.")
        self.session = session_req
        return self.session

    def exit(self):
        headers = self.headers
        params = {'exit': 'exit'}
        self.session.get('https://isu.uust.ru/', params=params, headers=headers)
        logging.debug("Выход из системы выполнен.")

    def clean_cell(self, cell):
        text = cell.get_text(strip=True)
        if not text:
            title = cell.get("title", "")
            if title == "Не зачет":
                return "(?)"
            return ""
        if text == "Зачтено":
            return "ЗЧ"
        elif text == "Не зачет":
            return "НЗ"
        elif text == "Неявка":
            return "НЯ"
        return text

    def update_all_marks(self):
        session = self.session
        headers = self.headers
        marks_response = session.post('https://isu.uust.ru/student_points_view/', headers=headers).text
        soup = BeautifulSoup(marks_response, 'lxml')
        table = soup.find('table', {'id': 'basic-datatable'})
        headers_list = [header.text for header in table.find_all('th')]
        self.table_headers = headers_list
        rows = table.find_all('tr')
        table_data = []
        for row in rows:
            cols = row.find_all('td')
            cols = [f'{col}'.strip().replace("\n", '').replace("\t", "").replace("\r", "").replace("<td>", "").replace(
                "</td>", "") for col in cols]
            new_cols = []
            for text in cols:
                if "<i" in text:
                    if "text" not in text:
                        new_cols.append("---")
                        continue
                    if re.compile(r'<i.*?>(.*?)<\/i>').findall(text)[0] == "":
                        if "title" not in text:
                            new_cols.append("---")
                            continue
                        else:
                            match = re.search(r'title="(.*?)"', text)
                            result = match.group(1)
                            new_cols.append(result)
                            continue
                    else:
                        pattern = re.compile(r'<i.*?>(.*?)</i>')
                        matches = pattern.findall(text)
                        result = matches[0]
                        new_cols.append(result)
                        continue
                pattern = re.compile(r'<span.*?>(.*?)</span>')
                matches = pattern.findall(text)
                result = matches[0] if matches else 'No matches'
                if result == 'No matches':
                    new_cols.append(text)
                else:
                    new_cols.append(result)
            table_data.append(new_cols)
        semester_count = 0
        for i in table_data[1:]:
            if not i:
                semester_count += 1
        marks = [[] for _ in range(semester_count)]
        semester_num = -1
        for data_row in table_data[1:]:
            if not data_row:
                semester_num += 1
            elif data_row[0][0] == 'Б':
                marks[semester_num].append(data_row)
        self.all_marks = marks
        return self.all_marks

    def get_semester_marks(self, semester_num: int, all_marks) -> list:
        if 1 <= semester_num <= len(all_marks):
            logging.debug("Возвращаем оценки для семестра %d: %s", semester_num, all_marks[semester_num - 1])
            return all_marks[semester_num - 1]
        logging.error("Указанный семестр (%d) вне диапазона (доступно %d)", semester_num, len(all_marks))
        raise MyError("Указанный семестр не соответствует действительности")

    def session_dump(self, path):
        with open(path, "wb") as file:
            pickle.dump(self.session, file)
        logging.debug("Сессия сохранена в файл: %s", path)

    def session_load(self, path):
        with open(path, "rb") as file:
            session_loaded = pickle.load(file)
        self.session = session_loaded
        logging.debug("Сессия загружена из файла: %s", path)


app = Flask(__name__)
app.secret_key = 'your_flask_secret_key'

# Настройка срока действия постоянной сессии (30 дней)
app.permanent_session_lifetime = timedelta(days=30)


def format_score(score):
    score = score.strip()
    if score == "---":
        return '<span class="score score-empty">---</span>'
    elif score == "Зачтено":
        return '<span class="score score-pass">Зачет</span>'
    elif score == "3":
        return '<span class="score score-3">3</span>'
    elif score in ["4", "5"]:
        return f'<span class="score score-{score}">{score}</span>'
    else:
        return f'<span class="score score-fail">{score}</span>'


@app.route('/', methods=['GET', 'POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем на дашборд
    if 'login' in session and 'password' in session and 'all_marks' in session:
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        login_input = request.form.get('username')
        password_input = request.form.get('password')
        parser = ISUParser(login_input, password_input)
        try:
            parser.authorisation()
            # Делаем сессию постоянной
            session.permanent = True
            session['login'] = login_input
            session['password'] = password_input
            all_marks = parser.update_all_marks()
            session['all_marks'] = all_marks
            # Устанавливаем начальный семестр
            session['current_semester'] = 1
            logging.debug("Авторизация успешна для пользователя: %s", login_input)
            return redirect(url_for('dashboard'))
        except MyError as e:
            error = str(e)
            logging.error("Ошибка авторизации: %s", error)
    return render_template('login.html', error=error)


@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'login' not in session or 'password' not in session or 'all_marks' not in session:
        return redirect(url_for('login'))
    all_marks = session.get('all_marks')
    total_semesters = len(all_marks)

    # Используем семестр из сессии, если он есть, иначе берем из параметра запроса
    sem_param = request.args.get('semester', default=session.get('current_semester', 1))
    try:
        selected_semester = int(sem_param)
    except ValueError:
        selected_semester = session.get('current_semester', 1)
    if selected_semester < 1 or selected_semester > total_semesters:
        selected_semester = 1

    # Сохраняем выбранный семестр в сессии
    session['current_semester'] = selected_semester

    semester_marks = ISUParser(session['login'], session['password']).get_semester_marks(selected_semester, all_marks)
    subject_cards = []
    for row in semester_marks:
        subject = row[1] if len(row) > 1 else "Неизвестно"
        scores = [format_score(cell) for cell in row[7:16] if cell]
        subject_cards.append({
            'subject': subject,
            'scores': scores
        })
    return render_template('dashboard.html',
                           cards=subject_cards,
                           total_semesters=total_semesters,
                           selected_semester=selected_semester)


@app.route('/get_semester_data', methods=['GET'])
def get_semester_data():
    if 'login' not in session or 'password' not in session or 'all_marks' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    all_marks = session.get('all_marks')
    total_semesters = len(all_marks)
    sem_param = request.args.get('semester', default=session.get('current_semester', 1))
    try:
        selected_semester = int(sem_param)
    except ValueError:
        selected_semester = session.get('current_semester', 1)
    if selected_semester < 1 or selected_semester > total_semesters:
        selected_semester = 1

    # Сохраняем выбранный семестр в сессии
    session['current_semester'] = selected_semester

    semester_marks = ISUParser(session['login'], session['password']).get_semester_marks(selected_semester, all_marks)
    subject_cards = []
    for row in semester_marks:
        subject = row[1] if len(row) > 1 else "Неизвестно"
        scores = [format_score(cell) for cell in row[7:16] if cell]
        subject_cards.append({
            'subject': subject,
            'scores': scores
        })
    return jsonify({
        'semester': selected_semester,
        'cards': subject_cards
    })


@app.route('/refresh_marks', methods=['POST'])
def refresh_marks():
    if 'login' not in session or 'password' not in session:
        return jsonify({'error': 'Не авторизован'}), 401

    # Используем текущий семестр из сессии
    current_semester = session.get('current_semester', 1)

    try:
        # Создаем новый парсер и авторизуемся
        parser = ISUParser(session['login'], session['password'])
        parser.authorisation()
        # Обновляем все оценки
        all_marks = parser.update_all_marks()
        # Сохраняем обновленные оценки в сессии
        session['all_marks'] = all_marks

        # Получаем данные для текущего семестра
        total_semesters = len(all_marks)
        if current_semester < 1 or current_semester > total_semesters:
            current_semester = 1
            session['current_semester'] = 1

        semester_marks = parser.get_semester_marks(current_semester, all_marks)
        subject_cards = []
        for row in semester_marks:
            subject = row[1] if len(row) > 1 else "Неизвестно"
            scores = [format_score(cell) for cell in row[7:16] if cell]
            subject_cards.append({
                'subject': subject,
                'scores': scores
            })

        return jsonify({
            'semester': current_semester,
            'cards': subject_cards
        })
    except MyError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error("Ошибка при обновлении оценок: %s", str(e))
        return jsonify({'error': 'Произошла ошибка при обновлении данных'}), 500


from flask import send_from_directory, make_response

@app.route('/sw.js')
def serve_sw():
    response = make_response(send_from_directory('.', 'sw.js'))
    response.headers['Service-Worker-Allowed'] = '/'  # Указываем область действия
    response.headers['Content-Type'] = 'application/javascript'
    return response

@app.route('/logout')
def logout():
    session.clear()
    logging.debug("Пользователь вышел из системы, сессия очищена.")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")