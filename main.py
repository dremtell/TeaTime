import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.core.image import Image as CoreImage
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import cm
from kivy.graphics import Color, RoundedRectangle

# Нативная интеграция вибрации для Android (pyjnius)
try:
    from jnius import autoclass

    PythonActivity = autoclass('org.renpy.android.PythonActivity')
    activity = PythonActivity.mActivity
    Context = autoclass('android.content.Context')
    vibrator_service = activity.getSystemService(Context.VIBRATOR_SERVICE)
    HAS_NATIVE_VIBRATOR = True
except Exception:
    HAS_NATIVE_VIBRATOR = False

kivy.require('2.0.0')


# Виджет картинки с программно скругленными углами и сохранением пропорций.
class RoundedImage(Widget):

    def __init__(self, source='gaiwan_idle.jpg', **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.core_image = CoreImage(source)

        with self.canvas:
            Color(1, 1, 1, 1)
            self.rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[25, 25, 25, 25],  # Радиус скругления углов
                texture=self.core_image.texture
            )

        self.bind(pos=self._update_rect, size=self._update_rect)

    # Безопасная смена изображения (для состояний idle / pour).
    def set_source(self, source):
        self.source = source
        self.core_image = CoreImage(source)
        self.rect.texture = self.core_image.texture
        self._update_rect()

    def _update_rect(self, *args):
        w, h = self.size
        if w == 0 or h == 0:
            return

        tex = self.rect.texture
        if not tex:
            self.rect.pos = self.pos
            self.rect.size = self.size
            return

        tw, th = tex.size
        if tw == 0 or th == 0:
            return

        # Сохранение пропорций (keep_ratio=True) и центрирование
        widget_aspect = w / h
        image_aspect = tw / th

        if image_aspect > widget_aspect:
            new_w = w
            new_h = w / image_aspect
            new_x = self.x
            new_y = self.y + (h - new_h) / 2
        else:
            new_h = h
            new_w = h * image_aspect
            new_x = self.x + (w - new_w) / 2
            new_y = self.y

        self.rect.pos = (new_x, new_y)
        self.rect.size = (new_w, new_h)


# Интерфейс таймера для чайной церемонии с визуализацией.
class TeaTimerWidget(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 10

        # --- Состояние таймера ---
        self.current_total_time = 0
        self.steep_count = 0
        self.timer_running = False

        # --- Загрузка звука окончания таймера ---
        self.end_sound = SoundLoader.load('End_timer.mp3')
        if self.end_sound:
            self.end_sound.volume = 1.0

        # --- UI Элементы ---

        # Заголовок
        title_label = Label(
            text="ЧАЙНЫЙ ТАЙМЕР",
            font_size='18sp',
            bold=True,
            color=(0.7, 0.7, 0.7, 1),
            size_hint_y=None,
            height=30
        )
        self.add_widget(title_label)

        # Отступ между заголовком и блоком полей ввода
        self.add_widget(Widget(size_hint_y=None, height=cm(0.5)))

        # --- Блок настроек ---
        settings_container = BoxLayout(
            orientation='horizontal',
            spacing=20,
            size_hint=(None, None),
            width=380,
            height=65
        )
        settings_container.pos_hint = {'center_x': 0.5}

        # Блок 1: Начальное время
        initial_block = BoxLayout(orientation='vertical', spacing=4, size_hint_x=0.5)
        initial_label = Label(
            text="Начало (сек):",
            halign='center',
            color=(0.8, 0.8, 0.8, 1),
            font_size='14sp',
            bold=True,
            size_hint_y=None,
            height=50
        )
        initial_block.add_widget(initial_label)

        self.initial_input = TextInput(
            text="20", input_filter='int', multiline=False,
            size_hint_y=None, height=50,
            halign='center', font_size='16sp', padding=[10, 6, 10, 0]
        )
        initial_block.add_widget(self.initial_input)
        settings_container.add_widget(initial_block)

        # Блок 2: Шаг добавления
        increment_block = BoxLayout(orientation='vertical', spacing=4, size_hint_x=0.5)
        increment_label = Label(
            text="Шаг (сек):",
            halign='center',
            color=(0.8, 0.8, 0.8, 1),
            font_size='14sp',
            bold=True,
            size_hint_y=None,
            height=50
        )
        increment_block.add_widget(increment_label)

        self.increment_input = TextInput(
            text="20", input_filter='int', multiline=False,
            size_hint_y=None, height=50,
            halign='center', font_size='16sp', padding=[10, 6, 10, 0]
        )
        increment_block.add_widget(self.increment_input)
        settings_container.add_widget(increment_block)

        self.add_widget(settings_container)

        # --- Картинка в центре ---
        self.gaiwan_image = RoundedImage(
            source='gaiwan_idle.jpg',
            size_hint_y=0.36
        )
        self.add_widget(self.gaiwan_image)

        # --- Блок таймера и счетчика ---
        timer_block = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width=Window.width,
            height=cm(3.3)
        )
        timer_block.pos_hint = {'center_x': 0.5}

        # Счетчик пролива
        self.steep_label = Label(
            text="Пролив: 0",
            font_size='21sp',
            bold=False,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=cm(0.65)
        )
        timer_block.add_widget(self.steep_label)

        # Отступ между счетчиком и цифрами
        spacer = Widget(
            size_hint_y=None,
            height=cm(0.35)
        )
        timer_block.add_widget(spacer)

        # Индикатор времени
        self.time_display = Label(
            text="Нажмите старт",
            font_size='32sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=cm(2.0)
        )
        timer_block.add_widget(self.time_display)

        self.add_widget(timer_block)

        # --- Панель кнопок управления ---
        buttons_layout = BoxLayout(size_hint_y=None, height=cm(1.8), spacing=15)

        self.reset_button = Button(
            text="СБРОС",
            background_color=(0.4, 0.15, 0.15, 1),
            bold=True,
            font_size='20sp'
        )
        self.reset_button.bind(on_press=self.handle_reset)
        buttons_layout.add_widget(self.reset_button)

        self.start_button = Button(
            text="СТАРТ",
            background_color=(0.15, 0.5, 0.3, 1),
            bold=True,
            font_size='20sp'
        )
        self.start_button.bind(on_press=self.handle_timer_start)
        buttons_layout.add_widget(self.start_button)

        self.add_widget(buttons_layout)

    def handle_timer_start(self, instance):
        if self.timer_running:
            return

        if not self.initial_input.text.strip() or not self.increment_input.text.strip():
            self.time_display.font_size = '32sp'
            self.time_display.text = "!"
            return

        try:
            initial = int(self.initial_input.text)
            increment = int(self.increment_input.text)
        except ValueError:
            return

        self.steep_count += 1
        self.current_total_time = initial + (self.steep_count - 1) * increment

        if self.current_total_time <= 0:
            self.steep_count = 0
            self.current_total_time = 0
            self.steep_label.text = "Пролив: 0"
            return

        # Обновляем текст счетчика пролива
        self.steep_label.text = f"Пролив: {self.steep_count}"

        self.gaiwan_image.set_source('gaiwan_idle.jpg')

        self.timer_running = True
        self.start_button.disabled = True

        # Переключаем на крупный шрифт для цифр таймера
        self.time_display.font_size = '56sp'
        self.time_display.text = str(self.current_total_time)

        Clock.schedule_interval(self._update_timer, 1.0)

    def _update_timer(self, dt):
        if self.current_total_time > 1:
            self.current_total_time -= 1
            self.time_display.text = str(self.current_total_time)
        else:
            self.current_total_time = 0
            Clock.unschedule(self._update_timer)
            self.handle_timer_end()

    def handle_timer_end(self):
        self.gaiwan_image.set_source('gaiwan_pour.jpg')
        Window.clearcolor = (0.3, 0.1, 0.1, 1)
        self.time_display.font_size = '42sp'
        self.time_display.text = "ГОТОВО"
        self.timer_running = False
        self.start_button.disabled = False

        # 1. Воспроизведение звука
        if self.end_sound:
            self.end_sound.play()

        # 2. Нативная вибрация на 0.5 секунду
        if HAS_NATIVE_VIBRATOR:
            try:
                vibrator_service.vibrate(500)
            except Exception:
                pass

        Clock.schedule_once(self.reset_image_and_bg, 10)

    def reset_image_and_bg(self, dt):
        if not self.timer_running:
            self.gaiwan_image.set_source('gaiwan_idle.jpg')
            Window.clearcolor = (0.08, 0.08, 0.08, 1)
            if self.current_total_time == 0 and self.time_display.text == "ГОТОВО":
                self.time_display.font_size = '32sp'
                self.time_display.text = "Нажмите старт"

    def handle_reset(self, instance):
        Clock.unschedule(self._update_timer)
        self.current_total_time = 0
        self.steep_count = 0
        self.timer_running = False
        self.start_button.disabled = False
        self.gaiwan_image.set_source('gaiwan_idle.jpg')
        self.time_display.font_size = '32sp'
        self.time_display.text = "Нажмите старт"
        self.steep_label.text = "Пролив: 0"
        Window.clearcolor = (0.08, 0.08, 0.08, 1)


class TeaTimerApp(App):
    def build(self):
        return TeaTimerWidget()


if __name__ == '__main__':
    Window.clearcolor = (0.08, 0.08, 0.08, 1)
    TeaTimerApp().run()