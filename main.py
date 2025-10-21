# -*- coding: utf-8 -*-
# 名称: MinimalLightBrowser
# 说明: 一个极简、无黑色元素、带运行日志终端的轻量浏览器（悬浮输入条版本 + 历史消息）
# 依赖: pip install PyQt5 PyQtWebEngine

import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QTextEdit, QSplitter, QStyleFactory, QPushButton, QHBoxLayout, 
    QScrollArea, QLabel, QFrame
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl, Qt, QByteArray, QBuffer, QIODevice, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QPalette, QColor

class MessageBubble(QFrame):
    """消息气泡组件"""
    def __init__(self, text, is_user=True, timestamp=None):
        super().__init__()
        self.is_user = is_user
        self.init_ui(text, timestamp)
    
    def init_ui(self, text, timestamp):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 消息容器
        bubble_container = QWidget()
        bubble_layout = QHBoxLayout(bubble_container)
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        
        # 消息气泡
        bubble = QFrame()
        bubble.setMaximumWidth(600)
        bubble_content = QVBoxLayout(bubble)
        bubble_content.setContentsMargins(12, 8, 12, 8)
        bubble_content.setSpacing(4)
        
        # 消息文本
        msg_label = QLabel(text)
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        msg_label.setFont(QFont("Microsoft YaHei", 10))
        
        # 时间戳
        time_label = QLabel(timestamp or datetime.now().strftime("%H:%M"))
        time_label.setFont(QFont("Microsoft YaHei", 8))
        time_label.setStyleSheet("color: rgba(100, 100, 100, 0.7);")
        
        bubble_content.addWidget(msg_label)
        bubble_content.addWidget(time_label, alignment=Qt.AlignRight if self.is_user else Qt.AlignLeft)
        
        # 根据发送者设置样式和对齐
        if self.is_user:
            bubble.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #007AFF, stop:1 #0051D5);
                    border-radius: 16px;
                    border: none;
                }
            """)
            msg_label.setStyleSheet("color: white;")
            bubble_layout.addStretch()
            bubble_layout.addWidget(bubble)
        else:
            bubble.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #F0F0F0, stop:1 #E8E8E8);
                    border-radius: 16px;
                    border: 1px solid #D8D8D8;
                }
            """)
            msg_label.setStyleSheet("color: #1D1D1F;")
            bubble_layout.addWidget(bubble)
            bubble_layout.addStretch()
        
        layout.addWidget(bubble_container)
        self.setStyleSheet("background: transparent;")

class DateSeparator(QWidget):
    """日期分隔符"""
    def __init__(self, date_text):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        
        # 左边线
        left_line = QFrame()
        left_line.setFrameShape(QFrame.HLine)
        left_line.setStyleSheet("background: #D0D0D0; max-height: 1px;")
        
        # 日期标签
        date_label = QLabel(date_text)
        date_label.setFont(QFont("Microsoft YaHei", 9))
        date_label.setStyleSheet("""
            color: #8E8E93;
            background: #F5F5F7;
            border-radius: 10px;
            padding: 4px 12px;
        """)
        
        # 右边线
        right_line = QFrame()
        right_line.setFrameShape(QFrame.HLine)
        right_line.setStyleSheet("background: #D0D0D0; max-height: 1px;")
        
        layout.addWidget(left_line, 1)
        layout.addWidget(date_label, 0)
        layout.addWidget(right_line, 1)

class HistoryPanel(QWidget):
    """历史消息面板"""
    def __init__(self):
        super().__init__()
        self.messages = []
        self.last_date = None
        self.init_ui()
    
    def init_ui(self):
        self.setFixedHeight(0)  # 初始隐藏
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 标题栏
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FAFAFA, stop:1 #F5F5F5);
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        
        title = QLabel("💬 对话历史")
        title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        title.setStyleSheet("color: #1D1D1F; background: transparent; border: none;")
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setFixedSize(50, 26)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #007AFF;
                border: 1px solid #007AFF;
                border-radius: 13px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: rgba(0, 122, 255, 0.1);
            }
            QPushButton:pressed {
                background: rgba(0, 122, 255, 0.2);
            }
        """)
        self.clear_btn.clicked.connect(self.clear_history)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.clear_btn)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #FFFFFF;
            }
            QScrollBar:vertical {
                background: #F5F5F5;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #C8C8C8;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #A8A8A8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 消息容器
        self.message_container = QWidget()
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(12, 12, 12, 12)
        self.message_layout.setSpacing(8)
        self.message_layout.addStretch()
        
        scroll.setWidget(self.message_container)
        
        main_layout.addWidget(header)
        main_layout.addWidget(scroll)
        
        self.setStyleSheet("""
            QWidget {
                background: #FFFFFF;
                border-radius: 12px;
            }
        """)
    
    def add_message(self, text, is_user=True):
        """添加消息"""
        now = datetime.now()
        current_date = now.strftime("%Y年%m月%d日")
        timestamp = now.strftime("%H:%M")
        
        # 检查是否需要添加日期分隔符
        if current_date != self.last_date:
            separator = DateSeparator(current_date)
            self.message_layout.insertWidget(self.message_layout.count() - 1, separator)
            self.last_date = current_date
        
        # 添加消息气泡
        bubble = MessageBubble(text, is_user, timestamp)
        self.message_layout.insertWidget(self.message_layout.count() - 1, bubble)
        
        # 滚动到底部
        QTimer.singleShot(50, self.scroll_to_bottom)
        
        self.messages.append({
            'text': text,
            'is_user': is_user,
            'timestamp': now,
            'date': current_date
        })
    
    def scroll_to_bottom(self):
        """滚动到底部"""
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
    
    def clear_history(self):
        """清空历史"""
        # 清空所有消息
        while self.message_layout.count() > 1:  # 保留最后的 stretch
            item = self.message_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.messages.clear()
        self.last_date = None
    
    def toggle_visibility(self):
        """切换显示/隐藏"""
        target_height = 400 if self.height() == 0 else 0
        
        self.animation = QPropertyAnimation(self, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setStartValue(self.height())
        self.animation.setEndValue(target_height)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()
        
        if target_height > 0:
            QTimer.singleShot(50, self.scroll_to_bottom)

class BrowserView:
    """浏览器视图模块 - 封装浏览器视图和相关操作"""
    def __init__(self, profile, terminal):
        self.terminal = terminal
        self.web_view = QWebEngineView()
        self.web_view.setPage(QWebEnginePage(profile, self.web_view))
        self.web_view.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, ok):
        if ok:
            self.terminal.log("✅ 加载完成")
            QTimer.singleShot(1000, self.check_page_stability)
        else:
            self.terminal.log("❌ 加载失败")

    def check_page_stability(self):
        js_check = """
        (function() {
            const hasActiveRequests = performance.getEntriesByType('resource').some(
                entry => entry.responseEnd === 0
            );
            const loadingElements = document.querySelectorAll('img[loading], iframe[loading]');
            const hasLoadingElements = Array.from(loadingElements).some(el => el.complete === false);
            return !hasActiveRequests && !hasLoadingElements;
        })();
        """
        def handle_stability(result):
            if result:
                self.terminal.log("✅ 页面已稳定")
            else:
                self.terminal.log("⏳ 页面仍在加载中...")
                QTimer.singleShot(2000, self.check_page_stability)
        self.web_view.page().runJavaScript(js_check, handle_stability)

    def load_url(self, url):
        self.web_view.setUrl(QUrl(url))

    def run_javascript(self, js_code, callback=None):
        if callback:
            self.web_view.page().runJavaScript(js_code, callback)
        else:
            self.web_view.page().runJavaScript(js_code)

class Terminal:
    """终端日志模块 - 负责日志显示"""
    def __init__(self):
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setMinimumHeight(160)
        self.terminal.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                color: #333;
                border-top: 1px solid #ccc;
                padding: 6px;
            }
        """)

    def log(self, message):
        self.terminal.append(message)

    def widget(self):
        return self.terminal

class FloatingChatWindow(QWidget):
    """悬浮聊天窗口 - 独立的悬浮输入条"""
    def __init__(self, on_send_callback, on_toggle_main, on_toggle_terminal, history_panel):
        super().__init__()
        self.on_send_callback = on_send_callback
        self.on_toggle_main = on_toggle_main
        self.on_toggle_terminal = on_toggle_terminal
        self.history_panel = history_panel
        self.is_always_on_top = False
        self.drag_position = None
        self.init_ui()

    def init_ui(self):
        # 设置为无边框、置顶窗口
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 主容器
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # 添加历史消息面板
        main_layout.addWidget(self.history_panel)
        
        # 控制按钮容器
        control_container = QWidget()
        control_container.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 18px;
                border: 1px solid #d0d0d0;
            }
        """)
        control_layout = QHBoxLayout(control_container)
        control_layout.setContentsMargins(8, 6, 8, 6)
        control_layout.setSpacing(6)
        
        # 控制按钮
        self.hide_main_btn = QPushButton("🏠 主窗口")
        self.history_btn = QPushButton("📜 历史")
        self.terminal_btn = QPushButton("📊 终端")
        self.settings_btn = QPushButton("⚙️ 设置")
        self.pin_btn = QPushButton("📌 置顶")
        
        button_style = """
            QPushButton {
                background: #e8f4f8;
                border: 1px solid #b8d4e0;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 11px;
                color: #333;
            }
            QPushButton:hover {
                background: #d0e8f0;
            }
            QPushButton:pressed {
                background: #b8dce8;
            }
        """
        
        for btn in [self.hide_main_btn, self.history_btn, self.terminal_btn, self.settings_btn, self.pin_btn]:
            btn.setStyleSheet(button_style)
            control_layout.addWidget(btn)
        
        control_layout.addStretch()
        
        # 输入容器（气泡风格）
        input_container = QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                border: 1px solid #d0d0d0;
            }
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)
        
        # 输入框
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("输入消息... (Enter发送, Shift+Enter换行)")
        self.chat_input.setMaximumHeight(120)
        self.chat_input.setMinimumHeight(36)
        self.chat_input.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_input.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                padding: 4px;
                font-size: 13px;
                color: #333;
            }
        """)
        
        # 监听文本变化以自动调整高度
        self.chat_input.textChanged.connect(self.adjust_input_height)
        
        # 发送按钮
        self.send_button = QPushButton("发送")
        self.send_button.setFixedSize(60, 32)
        self.send_button.setStyleSheet("""
            QPushButton {
                background: #007AFF;
                border: none;
                border-radius: 16px;
                padding: 6px 12px;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                background: #0051D5;
            }
            QPushButton:pressed {
                background: #003DA5;
            }
            QPushButton:disabled {
                background: #E0E0E0;
                color: #999;
            }
        """)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.send_button)
        
        # 添加到主布局
        main_layout.addWidget(control_container)
        main_layout.addWidget(input_container)
        
        # 连接信号
        self.send_button.clicked.connect(self.send_message)
        self.hide_main_btn.clicked.connect(self.toggle_main_window)
        self.history_btn.clicked.connect(self.toggle_history)
        self.terminal_btn.clicked.connect(self.on_toggle_terminal)
        self.settings_btn.clicked.connect(self.show_settings)
        self.pin_btn.clicked.connect(self.toggle_pin)
        
        # 设置初始大小和位置
        self.setMinimumWidth(600)
        self.adjustSize()
        self.move_to_screen_bottom()

    def adjust_input_height(self):
        """根据文本内容自动调整输入框高度"""
        doc_height = self.chat_input.document().size().height()
        new_height = min(max(36, int(doc_height) + 10), 120)
        self.chat_input.setFixedHeight(new_height)
        self.adjustSize()

    def move_to_screen_bottom(self):
        """将窗口移动到屏幕底部中央"""
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 50
        self.move(x, y)

    def send_message(self):
        """发送消息"""
        text = self.chat_input.toPlainText().strip()
        if not text:
            return
        self.on_send_callback(text)
        self.chat_input.clear()

    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
            self.send_message()
            event.accept()
        elif event.key() == Qt.Key_Return and event.modifiers() & Qt.ShiftModifier:
            self.chat_input.insertPlainText("\n")
            event.accept()
        else:
            super().keyPressEvent(event)

    def toggle_main_window(self):
        """切换主窗口显示/隐藏"""
        self.on_toggle_main()
        if self.hide_main_btn.text() == "🏠 主窗口":
            self.hide_main_btn.setText("🏠 显示")
        else:
            self.hide_main_btn.setText("🏠 主窗口")

    def toggle_history(self):
        """切换历史面板"""
        self.history_panel.toggle_visibility()
        if self.history_btn.text() == "📜 历史":
            self.history_btn.setText("📜 收起")
        else:
            self.history_btn.setText("📜 历史")

    def show_settings(self):
        """显示设置（占位）"""
        pass

    def toggle_pin(self):
        """切换置顶状态"""
        self.is_always_on_top = not self.is_always_on_top
        if self.is_always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.pin_btn.setText("📍 已置顶")
            self.pin_btn.setStyleSheet("""
                QPushButton {
                    background: #ffd0d0;
                    border: 1px solid #ffb0b0;
                    border-radius: 10px;
                    padding: 4px 10px;
                    font-size: 11px;
                    color: #333;
                }
            """)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.pin_btn.setText("📌 置顶")
            self.pin_btn.setStyleSheet("""
                QPushButton {
                    background: #e8f4f8;
                    border: 1px solid #b8d4e0;
                    border-radius: 10px;
                    padding: 4px 10px;
                    font-size: 11px;
                    color: #333;
                }
                QPushButton:hover {
                    background: #d0e8f0;
                }
            """)
        self.show()

    def set_enabled(self, enabled):
        """启用/禁用输入"""
        self.chat_input.setEnabled(enabled)
        self.send_button.setEnabled(enabled)

    def focus_input(self):
        """聚焦输入框"""
        self.chat_input.setFocus()
        self.activateWindow()
        self.raise_()

    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖动窗口"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

class ChatInput:
    """聊天输入模块 - 负责聊天输入和发送（保持兼容性）"""
    def __init__(self, on_send_callback):
        self.on_send_callback = on_send_callback
        self.floating_window = None

    def set_floating_window(self, floating_window):
        """设置悬浮窗口引用"""
        self.floating_window = floating_window

    def set_enabled(self, enabled):
        if self.floating_window:
            self.floating_window.set_enabled(enabled)

    def focus(self):
        if self.floating_window:
            self.floating_window.focus_input()

    def widget(self):
        return QWidget()

class ScreenshotHandler:
    """截图和上传模块 - 负责截图和上传"""
    def __init__(self, browser_view, terminal):
        self.browser_view = browser_view
        self.terminal = terminal

    def upload_screenshot(self, text, after_upload_callback):
        screen = QApplication.primaryScreen()
        pixmap = screen.grabWindow(0)

        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        base64_image = byte_array.toBase64().data().decode()

        js_image = f"""
        (function() {{
            const base64 = '{base64_image}';
            const byteString = atob(base64);
            const ab = new ArrayBuffer(byteString.length);
            const ia = new Uint8Array(ab);
            for (let i = 0; i < byteString.length; i++){{
                ia[i] = byteString.charCodeAt(i);
            }}

            const blob = new Blob([ab], {{type: 'image/png'}});
            const file = new File([blob], 'screenshot.png', {{type: 'image/png'}});

            const fileSelectors = [
                'input[type="file"][accept="image/*,video/*,audio/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv,text/plain"]',
                'input[type="file"][accept*="image"]',
                'input[data-testid*="upload"]',
                'input.semi-upload-input',
                'input[class*="upload"]',
                '.upload-button input',
                'input[type="file"]'
            ];

            let fileInput = null;
            for (let selector of fileSelectors){{
                const el = document.querySelector(selector);
                if (el){{
                    fileInput = el;
                    console.log('✅ 找到文件输入:', selector);
                    break;
                }}
            }}
            if (!fileInput){{
                console.log('❌ 未找到文件输入');
                return false;
            }}
            const dt = new DataTransfer();
            dt.items.add(file);
            fileInput.files = dt.files;
            fileInput.dispatchEvent(new Event('change',{{ bubbles: true }}));
            console.log('✅ 截图上传成功');
            return true;
        }})();
        """

        def handle_result(result):
            if result:
                self.terminal.log("✅ 截图上传成功")
                QTimer.singleShot(1000, lambda: after_upload_callback(text))
            else:
                self.terminal.log("❌ 截图上传失败，直接发送文字")
                QTimer.singleShot(500, lambda: after_upload_callback(text))

        self.browser_view.run_javascript(js_image, handle_result)

class ResponseMonitor:
    """回复监控模块 - 负责监控豆包回复状态"""
    def __init__(self, browser_view, terminal, chat_input, history_panel):
        self.browser_view = browser_view
        self.terminal = terminal
        self.chat_input = chat_input
        self.history_panel = history_panel
        self.timer = None
        self.waiting_logged = False
        self.user_check_count = 0
        self.last_reply_length = 0
        self.stable_count = 0
        self.current_user_message = None

    def check_response_complete(self):
        js = """
        (function() {
            const stopBtn = document.querySelector('button[data-testid*="stop"], button[aria-label*="停止"], button[class*="stop"]');
            if (stopBtn) {
                console.log('⏹️ 检测到停止按钮 — 正在回复中');
                return { complete: false, reason: 'has_stop_button', replyLength: 0 };
            }

            const msgSelectors = [
                'div[data-testid="message_text_content"]',
                'div.msg-bubble',
                'div[class*="message-content"]',
                'div[class*="markdown-body"]',
                'div[class*="chat-message"]'
            ];
            let msgs = [];
            for (let sel of msgSelectors) {
                const found = document.querySelectorAll(sel);
                if (found && found.length > 0) {
                    msgs = found;
                    break;
                }
            }
            if (msgs.length === 0) {
                console.log('❌ 未找到任何消息');
                return { complete: false, reason: 'no_messages', replyLength: 0 };
            }

            const lastMsg = msgs[msgs.length - 1];
            const text = lastMsg.textContent.trim();
            const len = text.length;
            const cls = lastMsg.className || '';
            const isBot = cls.includes('assistant') || cls.includes('bot') || cls.includes('markdown-body');

            if (!isBot) {
                console.log('📩 最后消息是用户消息，还没有机器人回复');
                return { complete: false, reason: 'no_bot_reply', replyLength:0 };
            }

            console.log('📄 机器人回复长度:', len);
            return { complete: true, reason: 'ok', replyLength: len, replyText: text };
        })();
        """
        def handle(result):
            if not result:
                return
            if not result.get('complete', False):
                const_reason = result.get('reason', 'unknown')
                if const_reason == 'has_stop_button':
                    if not self.waiting_logged:
                        self.terminal.log("💬 正在回复中…")
                        self.waiting_logged = True
                return

            current_len = result.get('replyLength', 0)
            reply_text = result.get('replyText', '')
            
            if current_len > 0:
                if current_len == self.last_reply_length:
                    self.stable_count += 1
                    self.terminal.log(f"⏳ 回复长度稳定: {current_len} 字符 (稳定次数: {self.stable_count}/3)")
                    if self.stable_count >= 3:
                        if self.timer:
                            self.timer.stop()
                        self.terminal.log("🤖 豆包回复:")
                        self.terminal.log("---")
                        self.terminal.log(reply_text)
                        self.terminal.log("---")
                        self.terminal.log("✅ 回复完成，输入框已启用")
                        
                        # 添加到历史记录
                        self.history_panel.add_message(reply_text, is_user=False)
                        
                        # 将回复保存到文件，供其他软件读取
                        try:
                            with open("latest_reply.txt", "w", encoding="utf-8") as f:
                                f.write(reply_text)
                            self.terminal.log("💾 回复已保存到 latest_reply.txt 文件")
                        except Exception as e:
                            self.terminal.log(f"❌ 保存回复到文件时出错: {str(e)}")
                        
                        self.chat_input.set_enabled(True)
                        self.chat_input.focus()
                        self.waiting_logged = False
                        self.user_check_count = 0
                        self.last_reply_length = 0
                        self.stable_count = 0
                        self.current_user_message = None
                else:
                    self.stable_count = 0
                    self.last_reply_length = current_len
                    self.terminal.log(f"📝 回复更新: {current_len} 字符")
        self.browser_view.run_javascript(js, handle)

    def check_user_message_appeared(self, text):
        self.current_user_message = text
        safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

        js = """
        (function() {{
            const possibleSelectors = [
                '[data-role="user-message"]',
                '[class*="role-user"]',
                '[class*="msg-bubble"]',
                '[class*="message"]',
                '[data-testid*="message"]',
                'div[class*="chat"] div',
                'p',
                'span'
            ];

            let found = false;
            for (let sel of possibleSelectors) {{
                const els = document.querySelectorAll(sel);
                for (let el of els) {{
                    const txt = el.textContent.trim();
                    if (txt && txt.includes('{text}')) {{
                        console.log('✅ 找到用户消息:', txt);
                        found = true;
                        break;
                    }}
                }}
                if (found) break;
            }}
            return found;
        }})();
        """.replace("{", "{{").replace("}", "}}").replace("{{text}}", "{text}").format(text=safe_text)

        def handle(result):
            if result:
                self.terminal.log("✅ 用户消息已出现在页面上")
                # 添加到历史记录
                if self.current_user_message:
                    self.history_panel.add_message(self.current_user_message, is_user=True)
                self.terminal.log("🔍 开始监测豆包回复状态…")
                self.start_monitoring()
            else:
                self.user_check_count += 1
                if self.user_check_count < 10:
                    QTimer.singleShot(1000, lambda: self.check_user_message_appeared(text))
                else:
                    self.terminal.log("❌ 未检测到用户消息，但可能已成功发送（请检查界面）")
                    self.chat_input.set_enabled(True)

        self.browser_view.run_javascript(js, handle)

    def start_monitoring(self):
        if self.timer and self.timer.isActive():
            self.timer.stop()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_response_complete)
        self.timer.start(2000)
        self.terminal.log("⌛ 等待回复中…")

class MinimalLightBrowser(QMainWindow):
   """主窗口类 - 负责整体窗口布局和协调各个模块"""
   def __init__(self):
       super().__init__()
       self.setup_storage()
       self.terminal = Terminal()
       self.browser_view = BrowserView(self.profile, self.terminal)
       self.chat_input = ChatInput(self.on_send_message)
       self.screenshot_handler = ScreenshotHandler(self.browser_view, self.terminal)
       
       # 创建历史面板
       self.history_panel = HistoryPanel()
       
       # 创建回复监控器（传入历史面板）
       self.response_monitor = ResponseMonitor(
           self.browser_view, 
           self.terminal, 
           self.chat_input,
           self.history_panel
       )
       
       # 创建悬浮窗口
       self.floating_chat = FloatingChatWindow(
           self.on_send_message,
           self.toggle_main_window,
           self.toggle_terminal,
           self.history_panel
       )
       self.chat_input.set_floating_window(self.floating_chat)
       
       self.init_ui()
       self.load_homepage()
       
       # 显示悬浮窗口
       self.floating_chat.show()

   def setup_storage(self):
       self.storage_path = os.path.join(os.getcwd(), "browser_data")
       os.makedirs(self.storage_path, exist_ok=True)
       self.profile = QWebEngineProfile("MinimalLightBrowser", self)
       self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
       self.profile.setPersistentStoragePath(self.storage_path)
       self.profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
       self.profile.setHttpCacheMaximumSize(200 * 1024 * 1024)

   def init_ui(self):
       self.setWindowTitle("Minimal Light Browser")
       self.setGeometry(100, 80, 1200, 800)

       app.setStyle(QStyleFactory.create("Fusion"))
       palette = QPalette()
       palette.setColor(QPalette.Window, QColor(245, 245, 245))
       palette.setColor(QPalette.Base, QColor(255, 255, 255))
       palette.setColor(QPalette.Text, QColor(50, 50, 50))
       palette.setColor(QPalette.Button, QColor(240, 240, 240))
       palette.setColor(QPalette.ButtonText, QColor(30, 30, 30))
       palette.setColor(QPalette.Highlight, QColor(173, 216, 230))
       app.setPalette(palette)

       font = QFont("Microsoft YaHei", 10)
       app.setFont(font)

       splitter = QSplitter(Qt.Vertical)
       
       # 浏览器容器
       browser_container = QWidget()
       layout = QVBoxLayout(browser_container)
       layout.addWidget(self.browser_view.web_view)
       layout.setContentsMargins(0, 0, 0, 0)
       
       splitter.addWidget(browser_container)
       splitter.addWidget(self.terminal.widget())
       splitter.setSizes([700, 100])

       self.setCentralWidget(splitter)

   def load_homepage(self):
       home_url = "https://www.doubao.com/chat/25474120854203650"
       self.browser_view.load_url(home_url)
       self.terminal.log("🌐 已加载首页：" + home_url)

   def toggle_main_window(self):
       """切换主窗口的显示/隐藏"""
       if self.isVisible():
           self.hide()
       else:
           self.show()
           self.activateWindow()

   def toggle_terminal(self):
       """切换终端的显示/隐藏"""
       terminal_widget = self.terminal.widget()
       if terminal_widget.isVisible():
           terminal_widget.hide()
       else:
           terminal_widget.show()

   def on_send_message(self, text):
       self.terminal.log(f"📤 发送消息：{text}")
       self.chat_input.set_enabled(False)
       self.screenshot_handler.upload_screenshot(text, self.send_text)

   def send_text(self, text):
       escaped = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
       js_text = f"""
       (function() {{
           const selectors = [
               'textarea[data-testid="chat_input_input"]',
               'textarea.semi-input-textarea',
               'textarea[placeholder*="发消息"]',
               'textarea',
               '[contenteditable="true"]',
               '.chat-input',
               '[class*="input"] textarea'
           ];
           let ta = null;
           for (let sel of selectors) {{
               const el = document.querySelector(sel);
               if (el) {{
                   ta = el;
                   console.log('✅ 找到输入框:', sel);
                   break;
               }}
           }}
           if (!ta) {{
               console.log('❌ 未找到输入框');
               return false;
           }}
           ta.focus();
           const nativeSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
           const inputEvt = new Event('input', {{ bubbles: true, composed: true }});
           const setValue = value => {{
               nativeSetter.call(ta, value);
               ta.dispatchEvent(inputEvt);
           }};
           setValue('{escaped}');
           ['input','change','keyup','keydown'].forEach(evt => {{
               ta.dispatchEvent(new Event(evt, {{ bubbles: true, composed: true }}));
           }});
           setTimeout(() => {{
               const sendSelectors = [
                   'button[type="submit"]',
                   'button[class*="send"]',
                   '.send-button',
                   'button[aria-label*="发送"]',
                   'button[data-testid*="send"]',
                   'button.semi-button'
               ];
               let btn = null;
               for (let sel of sendSelectors) {{
                   const el = document.querySelector(sel);
                   if (el) {{
                       btn = el;
                       console.log('✅ 找到发送按钮:', sel);
                       break;
                   }}
               }}
               if (btn) {{
                   btn.click();
                   console.log('✅ 点击发送按钮');
               }} else {{
                   console.log('❌ 未找到发送按钮');
               }}
           }}, 300);
           return true;
       }})();
       """
       def handle(result):
           if result:
               self.terminal.log("✅ 文字发送成功")
               self.response_monitor.user_check_count = 0
               QTimer.singleShot(1000, lambda: self.response_monitor.check_user_message_appeared(text))
           else:
               self.terminal.log("❌ 文字发送失败，重新启用输入框")
               self.chat_input.set_enabled(True)
       self.browser_view.run_javascript(js_text, handle)

if __name__ == "__main__":
   app = QApplication(sys.argv)
   window = MinimalLightBrowser()
   window.show()
   sys.exit(app.exec_())


