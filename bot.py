import asyncio
import aiohttp
import sys
import re
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QHBoxLayout,
    QComboBox, QProgressBar, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt

def generate_user_agent():
    version = f"{random.randint(100, 130)}.{random.randint(0, 10)}.{random.randint(0, 10)}.{random.randint(0, 10)}"
    
    os_versions = [
        f"Windows NT {random.randint(6, 10)}.{random.randint(0, 10)}; Win64; x64",
        f"Macintosh; Intel Mac OS X 10_{random.randint(6, 15)}_{random.randint(0, 10)}",
        f"Linux; U; Android {random.randint(10, 12)}; en-US; Pixel 3 XL Build/{random.randint(1000, 2000)}"
    ]
    
    os_version = random.choice(os_versions)
    
    return f"Mozilla/5.0 ({os_version}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"

LANGUAGES = {
    "English": {
        "title": "Like & View Bot",
        "enter_url": "Enter URL (https://rooms.xyz/nick/room)",
        "enter_likes": "Enter number of likes (b)",
        "enter_iterations": "Enter number of iterations",
        "enter_threads": "Enter number of threads (1-100)",
        "start": "Start",
        "pause": "Pause",
        "likes_sent": "Likes sent:",
        "views_sent": "Views sent:",
        "error": "❌ Error! Enter a valid URL and number of likes!",
        "starting": "🚀 Starting bot for",
    },
    "Русский": {
        "title": "Бот лайков и просмотров",
        "enter_url": "Введите ссылку (https://rooms.xyz/nick/room)",
        "enter_likes": "Введите количество лайков (b)",
        "enter_iterations": "Введите количество итераций",
        "enter_threads": "Введите количество потоков (1-100)",
        "start": "Запустить",
        "pause": "Пауза",
        "likes_sent": "Лайков отправлено:",
        "views_sent": "Просмотров отправлено:",
        "error": "❌ Ошибка! Введите корректную ссылку и количество лайков!",
        "starting": "🚀 Запуск бота для",
    }
}

class RequestSender(QThread):
    update_likes = pyqtSignal(int)
    update_views = pyqtSignal(int)
    update_log = pyqtSignal(str)
    update_progress = pyqtSignal(int)

    total_likes = 0
    total_views = 0 

    def __init__(self, nick, room, likes, iterations, infinite_mode, thread_id):
        super().__init__()
        self.nick = nick
        self.room = room
        self.likes_to_send = likes
        self.views_to_send = 1
        self.iterations = iterations
        self.like_count = 0
        self.view_count = 0
        self.infinite_mode = infinite_mode
        self.thread_id = thread_id
        self._stop_event = asyncio.Event()

    async def send_request(self, session, i):
        url = f"https://us-central1-things-roomsxyz.cloudfunctions.net/roomsf1?a={self.nick}%2F{self.room}&b={self.likes_to_send}&c={self.views_to_send}"
        headers = {"User-Agent": generate_user_agent()}
        try:
            async with session.post(url, headers=headers) as response:
                if response.status == 200:
                    self.like_count += self.likes_to_send
                    self.view_count += self.views_to_send
                    self.update_likes.emit(self.like_count)
                    self.update_views.emit(self.view_count)
                    self.update_log.emit(f"[Thread {self.thread_id}] ✔ Sent {self.likes_to_send} likes, {self.views_to_send} views -> {self.nick}/{self.room}")
                    RequestSender.total_likes += self.likes_to_send
                    RequestSender.total_views += self.views_to_send
                else:
                    self.update_log.emit(f"[Thread {self.thread_id}] ✖ Error: {response.status}")
        except Exception as e:
            self.update_log.emit(f"[Thread {self.thread_id}] ✖ Request error: {e}")

    async def send_requests(self):
        async with aiohttp.ClientSession() as session:
            tasks = []
            i = 1
            while True:
                if not self.infinite_mode and i > self.iterations:
                    break
                task = self.send_request(session, i)
                tasks.append(task)

                if len(tasks) >= 50 or self.infinite_mode:
                    await asyncio.gather(*tasks)
                    tasks = []

                self.update_progress.emit(int(i / self.iterations * 100) if not self.infinite_mode else 100)
                i += 1

                if self._stop_event.is_set():
                    self.update_log.emit(f"[Thread {self.thread_id}] Paused.")
                    break

            if tasks:
                await asyncio.gather(*tasks)

    def run(self):
        asyncio.run(self.send_requests())

    def stop(self):
        self._stop_event.set()


class LikeBotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.language = "English"
        self.is_running = False
        self.initUI()

    def initUI(self):
        self.setWindowTitle(LANGUAGES[self.language]["title"])
        self.setGeometry(100, 100, 550, 400)

        layout = QHBoxLayout()

        self.stats_layout = QVBoxLayout()
        self.label_likes = QLabel(LANGUAGES[self.language]["likes_sent"] + " 0")
        self.label_views = QLabel(LANGUAGES[self.language]["views_sent"] + " 0")
        self.stats_layout.addWidget(self.label_likes)
        self.stats_layout.addWidget(self.label_views)
        layout.addLayout(self.stats_layout)

        self.form_layout = QVBoxLayout()

        self.language_selector = QComboBox(self)
        self.language_selector.addItems(["English", "Русский"])
        self.language_selector.currentTextChanged.connect(self.change_language)

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText(LANGUAGES[self.language]["enter_url"])
        self.likes_input = QLineEdit(self)
        self.likes_input.setPlaceholderText(LANGUAGES[self.language]["enter_likes"])
        self.iterations_input = QLineEdit(self)
        self.iterations_input.setPlaceholderText(LANGUAGES[self.language]["enter_iterations"])
        self.threads_input = QLineEdit(self)
        self.threads_input.setPlaceholderText(LANGUAGES[self.language]["enter_threads"])

        self.infinite_checkbox = QCheckBox("Run infinitely?", self)

        self.start_button = QPushButton(LANGUAGES[self.language]["start"], self)
        self.start_button.clicked.connect(self.toggle_bot)

        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.form_layout.addWidget(self.language_selector)
        self.form_layout.addWidget(self.url_input)
        self.form_layout.addWidget(self.likes_input)
        self.form_layout.addWidget(self.iterations_input)
        self.form_layout.addWidget(self.threads_input)
        self.form_layout.addWidget(self.infinite_checkbox)
        self.form_layout.addWidget(self.start_button)
        self.form_layout.addWidget(self.log_output)
        self.form_layout.addWidget(self.progress_bar)

        layout.addLayout(self.form_layout)

        self.setLayout(layout)

    def extract_nick_and_room(self, url):
        match = re.match(r"https://rooms\.xyz/([^/]+)/([^/]+)", url)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def change_language(self, lang):
        self.language = lang
        self.setWindowTitle(LANGUAGES[lang]["title"])
        self.url_input.setPlaceholderText(LANGUAGES[lang]["enter_url"])
        self.likes_input.setPlaceholderText(LANGUAGES[lang]["enter_likes"])
        self.iterations_input.setPlaceholderText(LANGUAGES[lang]["enter_iterations"])
        self.threads_input.setPlaceholderText(LANGUAGES[lang]["enter_threads"])
        self.start_button.setText(LANGUAGES[lang]["start"] if not self.is_running else LANGUAGES[lang]["pause"])
        self.label_likes.setText(LANGUAGES[lang]["likes_sent"] + " 0")
        self.label_views.setText(LANGUAGES[lang]["views_sent"] + " 0")

    def toggle_bot(self):
        if not self.is_running:
            self.start_bot()
        else:
            self.pause_bot()

    def start_bot(self):
        url = self.url_input.text().strip()
        likes = self.likes_input.text().strip()
        iterations = self.iterations_input.text().strip()
        threads = self.threads_input.text().strip()

        nick, room = self.extract_nick_and_room(url)

        if not nick or not room or not likes.isdigit() or not iterations.isdigit() or not threads.isdigit():
            self.log_output.append(LANGUAGES[self.language]["error"])
            return

        likes = int(likes)
        iterations = int(iterations)
        threads = int(threads)

        self.log_output.append(f"{LANGUAGES[self.language]['starting']} {nick}/{room}...")

        infinite_mode = self.infinite_checkbox.isChecked()

        self.threads = []
        for i in range(threads):
            worker = RequestSender(nick, room, likes, iterations, infinite_mode, i + 1)
            worker.update_likes.connect(self.update_likes_label)
            worker.update_views.connect(self.update_views_label)
            worker.update_log.connect(self.update_log)
            worker.update_progress.connect(self.update_progress_bar)
            self.threads.append(worker)
            worker.start()

        self.is_running = True
        self.start_button.setText(LANGUAGES[self.language]["pause"])

    def pause_bot(self):
        for thread in self.threads:
            thread.stop()

        self.is_running = False
        self.start_button.setText(LANGUAGES[self.language]["start"])

    def update_likes_label(self, count):
        self.label_likes.setText(f"{LANGUAGES[self.language]['likes_sent']} {RequestSender.total_likes}")

    def update_views_label(self, count):
        self.label_views.setText(f"{LANGUAGES[self.language]['views_sent']} {RequestSender.total_views}")

    def update_log(self, message):
        self.log_output.append(message)

    def update_progress_bar(self, progress):
        self.progress_bar.setValue(progress)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LikeBotApp()
    ex.show()
    sys.exit(app.exec())
