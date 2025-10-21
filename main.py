# -*- coding: utf-8 -*-
# 名称: MinimalLightBrowser
# 说明: 一个极简、无黑色元素、带运行日志终端的轻量浏览器（悬浮输入条版本 + 历史消息 + 终端集成）
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

class TerminalPanel(QWidget):
    """终端面板（集成到悬浮窗口）"""
    def __init__(self):
        super().__init__()
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
                    stop:0 #F8F8F8, stop:1 #F0F0F0);
                border-bottom: 1px solid #D0D0D0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        
        title = QLabel("📊 运行日志")
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
        self.clear_btn.clicked.connect(self.clear_terminal)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.clear_btn)
        
        # 终端内容
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("""
            QTextEdit {
                background-color: #FAFAFA;
                color: #333;
                border: none;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        
        main_layout.addWidget(header)
        main_layout.addWidget(self.terminal)
        
        self.setStyleSheet("""
            QWidget {
                background: #FFFFFF;
                border-radius: 12px;
            }
        """)
    
    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal.append(f"[{timestamp}] {message}")
    
    def clear_terminal(self):
        """清空终端"""
        self.terminal.clear()
    
    def toggle_visibility(self):
        """切换显示/隐藏"""
        target_height = 200 if self.height() == 0 else 0
        
        self.animation = QPropertyAnimation(self, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setStartValue(self.height())
        self.animation.setEndValue(target_height)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

class BrowserView:
    """浏览器视图模块 - 封装浏览器视图和相关操作"""
    def __init__(self, profile, terminal_panel):
        self.terminal_panel = terminal_panel
        self.web_view = QWebEngineView()
        self.web_view.setPage(QWebEnginePage(profile, self.web_view))
        self.web_view.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, ok):
        if ok:
            self.terminal_panel.log("✅ 加载完成")
            QTimer.singleShot(1000, self.check_page_stability)
        else:
            self.terminal_panel.log("❌ 加载失败")

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
                self.terminal_panel.log("✅ 页面已稳定")
            else:
                self.terminal_panel.log("⏳ 页面仍在加载中...")
                QTimer.singleShot(2000, self.check_page_stability)
        self.web_view.page().runJavaScript(js_check, handle_stability)

    def load_url(self, url):
        self.web_view.setUrl(QUrl(url))

    def run_javascript(self, js_code, callback=None):
        if callback:
            self.web_view.page().runJavaScript(js_code, callback)
        else:
            self.web_view.page().runJavaScript(js_code)

class FloatingChatWindow(QWidget):
    """悬浮聊天窗口 - 独立的悬浮输入条（集成终端）"""
    def __init__(self, on_send_callback, on_toggle_main, history_panel, terminal_panel):
        super().__init__()
        self.on_send_callback = on_send_callback
        self.on_toggle_main = on_toggle_main
        self.history_panel = history_panel
        self.terminal_panel = terminal_panel
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
        
        # 添加终端面板
        main_layout.addWidget(self.terminal_panel)
        
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
        self.terminal_btn.clicked.connect(self.toggle_terminal)
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

    def toggle_terminal(self):
        """切换终端面板"""
        self.terminal_panel.toggle_visibility()
        if self.terminal_btn.text() == "📊 终端":
            self.terminal_btn.setText("📊 收起")
        else:
            self.terminal_btn.setText("📊 终端")

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

class ScreenshotHandler:
    """截图和上传模块 - 优化版"""
    def __init__(self, browser_view, terminal_panel):
        self.browser_view = browser_view
        self.terminal_panel = terminal_panel

    def upload_screenshot(self, text, after_upload_callback):
        """上传截图，不跳过截图步骤"""
        screen = QApplication.primaryScreen()
        pixmap = screen.grabWindow(0)

        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        base64_image = byte_array.toBase64().data().decode()

        # 优化后的文件上传脚本
        js_image = f"""
        (function() {{
            try {{
                const base64 = '{base64_image}';
                const byteString = atob(base64);
                const ab = new ArrayBuffer(byteString.length);
                const ia = new Uint8Array(ab);
                for (let i = 0; i < byteString.length; i++){{
                    ia[i] = byteString.charCodeAt(i);
                }}

                const blob = new Blob([ab], {{type: 'image/png'}});
                const file = new File([blob], 'screenshot.png', {{type: 'image/png'}});

                // 扩展文件输入选择器列表
                const fileSelectors = [
                    'input[type="file"]',
                    'input[accept*="image"]',
                    'input[data-testid*="upload"]',
                    'input[data-testid*="file"]',
                    'input.semi-upload-input',
                    'input[class*="upload"]',
                    'input[class*="file"]',
                    '.upload-button input',
                    '[class*="attachment"] input',
                    '[class*="file-input"]'
                ];

                let fileInput = null;
                for (let selector of fileSelectors){{
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {{
                        // 找到第一个可见或存在的文件输入
                        for (let el of elements) {{
                            if (!el.disabled) {{
                                fileInput = el;
                                console.log('✅ 找到文件输入:', selector);
                                break;
                            }}
                        }}
                        if (fileInput) break;
                    }}
                }}
                
                if (!fileInput){{
                    console.log('⚠️ 未找到文件输入，继续执行但不影响文字发送');
                    // 不返回false，继续执行以确保文字发送
                }}
                
                const dt = new DataTransfer();
                dt.items.add(file);
                fileInput.files = dt.files;
                
                // 触发多种事件确保上传生效
                ['change', 'input'].forEach(eventType => {{
                    fileInput.dispatchEvent(new Event(eventType, {{ bubbles: true, cancelable: true }}));
                }});
                
                console.log('✅ 截图上传成功');
                return true;
            }} catch (error) {{
                console.error('❌ 截图上传异常:', error);
                return false;
            }}
        }})();
        """

        def handle_result(result):
            if result:
                self.terminal_panel.log("✅ 截图上传成功")
            else:
                self.terminal_panel.log("⚠️ 截图上传过程已执行（可能未找到上传位置）")
            # 无论截图是否成功，都执行文字发送
            QTimer.singleShot(1500, lambda: after_upload_callback(text))

        self.browser_view.run_javascript(js_image, handle_result)

class ResponseMonitor:
    """回复监控模块 - 优化版"""
    def __init__(self, browser_view, terminal_panel, floating_chat, history_panel):
        self.browser_view = browser_view
        self.terminal_panel = terminal_panel
        self.floating_chat = floating_chat
        self.history_panel = history_panel
        self.timer = None
        self.waiting_logged = False
        self.user_check_count = 0
        self.last_reply_length = 0
        self.stable_count = 0
        self.current_user_message = None

    def check_user_message_appeared(self, text):
        """优化的用户消息检测"""
        self.current_user_message = text
        
        # 更安全的文本转义
        safe_text = (text.replace("\\", "\\\\")
                         .replace("'", "\\'")
                         .replace('"', '\\"')
                         .replace("\n", "\\n"))

        # 优化后的检测脚本
        js = """
        (function() {{
            try {{
                const searchText = '{text}';
                
                // 扩展选择器列表
                const possibleSelectors = [
                    '[data-role="user-message"]',
                    '[class*="user"]',
                    '[class*="role-user"]',
                    '[class*="msg-bubble"]',
                    '[class*="message"]',
                    '[data-testid*="message"]',
                    'div[class*="chat"] > div',
                    '.markdown-body',
                    'p', 'span', 'div'
                ];

                let found = false;
                
                // 方法1: 通过选择器查找
                for (let sel of possibleSelectors) {{
                    const els = document.querySelectorAll(sel);
                    for (let el of els) {{
                        const txt = el.textContent.trim();
                        if (txt && txt.includes(searchText.substring(0, 50))) {{
                            console.log('✅ 找到用户消息(选择器):', sel);
                            found = true;
                            break;
                        }}
                    }}
                    if (found) break;
                }}
                
                // 方法2: 如果方法1失败，使用全局搜索
                if (!found) {{
                    const bodyText = document.body.textContent;
                    if (bodyText.includes(searchText.substring(0, 50))) {{
                        console.log('✅ 找到用户消息(全局搜索)');
                        found = true;
                    }}
                }}
                
                return found;
            }} catch (error) {{
                console.error('❌ 检测用户消息异常:', error);
                return false;
            }}
        }})();
        """.format(text=safe_text[:100])  # 只取前100个字符进行匹配

        def handle(result):
            if result:
                self.terminal_panel.log("✅ 用户消息已出现在页面上")
                if self.current_user_message:
                    self.history_panel.add_message(self.current_user_message, is_user=True)
                self.terminal_panel.log("🔍 开始监测豆包回复状态…")
                self.start_monitoring()
            else:
                self.user_check_count += 1
                if self.user_check_count < 15:  # 增加重试次数到15次
                    self.terminal_panel.log(f"⏳ 等待用户消息出现... ({self.user_check_count}/15)")
                    QTimer.singleShot(800, lambda: self.check_user_message_appeared(text))
                else:
                    self.terminal_panel.log("⚠️ 消息可能已发送，但未在页面检测到（开始监测回复）")
                    # 即使没检测到用户消息，也添加到历史并开始监测回复
                    if self.current_user_message:
                        self.history_panel.add_message(self.current_user_message, is_user=True)
                    self.start_monitoring()

        self.browser_view.run_javascript(js, handle)

    def check_response_complete(self):
        """检查回复是否完成"""
        js = """
        (function() {
            try {
                // 检查是否有停止按钮
                const stopBtn = document.querySelector(
                    'button[data-testid*="stop"], ' +
                    'button[aria-label*="停止"], ' +
                    'button[class*="stop"], ' +
                    'button[class*="abort"]'
                );
                if (stopBtn && stopBtn.offsetParent !== null) {
                    return { complete: false, reason: 'has_stop_button', replyLength: 0 };
                }

                // 查找消息列表
                const msgSelectors = [
                    'div[data-testid="message_text_content"]',
                    'div.msg-bubble',
                    'div[class*="message-content"]',
                    'div[class*="markdown-body"]',
                    'div[class*="chat-message"]',
                    '.markdown-body',
                    '[class*="assistant"] > div',
                    '[data-role*="assistant"]'
                ];
                
                let msgs = [];
                for (let sel of msgSelectors) {
                    const found = document.querySelectorAll(sel);
                    if (found && found.length > 0) {
                        msgs = Array.from(found);
                        break;
                    }
                }
                
                if (msgs.length === 0) {
                    return { complete: false, reason: 'no_messages', replyLength: 0 };
                }

                // 获取最后一条消息
                const lastMsg = msgs[msgs.length - 1];
                const text = lastMsg.textContent.trim();
                const len = text.length;
                
                // 判断是否是机器人消息
                const cls = lastMsg.className || '';
                const role = lastMsg.getAttribute('data-role') || '';
                const isBot = cls.includes('assistant') || 
                             cls.includes('bot') || 
                             cls.includes('markdown-body') ||
                             role.includes('assistant');

                if (!isBot) {
                    return { complete: false, reason: 'no_bot_reply', replyLength: 0 };
                }

                return { complete: true, reason: 'ok', replyLength: len, replyText: text };
            } catch (error) {
                console.error('❌ 检查回复异常:', error);
                return { complete: false, reason: 'error', replyLength: 0 };
            }
        })();
        """
        
        def handle(result):
            if not result:
                return
                
            if not result.get('complete', False):
                reason = result.get('reason', 'unknown')
                if reason == 'has_stop_button':
                    if not self.waiting_logged:
                        self.terminal_panel.log("💬 正在回复中…")
                        self.waiting_logged = True
                elif reason == 'no_bot_reply':
                    if not self.waiting_logged:
                        self.terminal_panel.log("⏳ 等待机器人回复...")
                        self.waiting_logged = True
                return

            current_len = result.get('replyLength', 0)
            reply_text = result.get('replyText', '')
            
            if current_len > 0:
                if current_len == self.last_reply_length:
                    self.stable_count += 1
                    self.terminal_panel.log(f"⏳ 回复稳定检测: {current_len} 字符 ({self.stable_count}/3)")
                    
                    if self.stable_count >= 3:
                        if self.timer:
                            self.timer.stop()
                        
                        self.terminal_panel.log("=" * 50)
                        self.terminal_panel.log("🤖 豆包回复完成:")
                        self.terminal_panel.log(f"字数: {current_len}")
                        self.terminal_panel.log("-" * 50)
                        self.terminal_panel.log(reply_text[:200] + "..." if len(reply_text) > 200 else reply_text)
                        self.terminal_panel.log("=" * 50)
                        
                        # 添加到历史记录
                        self.history_panel.add_message(reply_text, is_user=False)
                        
                        # 重置状态并启用输入
                        self.floating_chat.set_enabled(True)
                        self.floating_chat.focus_input()
                        self.waiting_logged = False
                        self.user_check_count = 0
                        self.last_reply_length = 0
                        self.stable_count = 0
                        self.current_user_message = None
                else:
                    self.stable_count = 0
                    self.last_reply_length = current_len
                    self.terminal_panel.log(f"📝 回复更新: {current_len} 字符")
                    
        self.browser_view.run_javascript(js, handle)

    def start_monitoring(self):
        """开始监控回复"""
        if self.timer and self.timer.isActive():
            self.timer.stop()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_response_complete)
        self.timer.start(1500)  # 缩短检测间隔到1.5秒
        
        self.terminal_panel.log("⌛ 等待回复中…")
        self.waiting_logged = False
class MinimalLightBrowser(QMainWindow):
    """主窗口类 - 负责整体窗口布局和协调各个模块"""
    def __init__(self):
        super().__init__()
        self.setup_storage()
        
        # 创建组件
        self.history_panel = HistoryPanel()
        self.terminal_panel = TerminalPanel()
        self.browser_view = BrowserView(self.profile, self.terminal_panel)
        self.screenshot_handler = ScreenshotHandler(self.browser_view, self.terminal_panel)
        
        # 创建悬浮窗口
        self.floating_chat = FloatingChatWindow(
            self.on_send_message,
            self.toggle_main_window,
            self.history_panel,
            self.terminal_panel
        )
        
        # 创建回复监控器
        self.response_monitor = ResponseMonitor(
            self.browser_view, 
            self.terminal_panel, 
            self.floating_chat,
            self.history_panel
        )
        
        self.init_ui()
        self.load_homepage()
        
        # 显示悬浮窗口
        self.floating_chat.show()
        
        # 默认缩小主窗口到最小尺寸
        QTimer.singleShot(100, lambda: self.resize(0, 0))

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

        # 只显示浏览器视图
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.browser_view.web_view)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.setCentralWidget(central_widget)

    def load_homepage(self):
        home_url = "https://www.doubao.com/chat/25474120854203650"
        self.browser_view.load_url(home_url)
        self.terminal_panel.log("🌐 已加载首页：" + home_url)

    def toggle_main_window(self):
        """切换主窗口的大小（最小/正常）"""
        if self.size().width() > 10 and self.size().height() > 10:
            # 如果窗口较大，则缩小到最小
            self.resize(0, 0)
        else:
            # 如果窗口很小，则恢复正常大小并确保可见
            self.show()  # 确保窗口可见
            self.resize(1200, 800)
            self.activateWindow()

    def on_send_message(self, text):
        self.terminal_panel.log(f"📤 发送消息：{text}")
        self.floating_chat.set_enabled(False)
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
                self.terminal_panel.log("✅ 文字发送成功")
                self.response_monitor.user_check_count = 0
                QTimer.singleShot(1000, lambda: self.response_monitor.check_user_message_appeared(text))
            else:
                self.terminal_panel.log("❌ 文字发送失败，重新启用输入框")
                self.floating_chat.set_enabled(True)
        self.browser_view.run_javascript(js_text, handle)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MinimalLightBrowser()
    # 不在这里显示主窗口，因为在 __init__ 中已经默认隐藏
    sys.exit(app.exec_())
