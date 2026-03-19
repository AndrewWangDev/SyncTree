from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
import re
from ui.theme import COLORS
from core.i18n import tr

def git_ansi_to_html(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("*", "●").replace("|", "│").replace("/", "╱").replace("\\", "╲")
    
    ansi_map = {
        '30': '#000000', '31': '#ff5555', '32': '#50fa7b', '33': '#f1fa8c', '34': '#bd93f9',
        '35': '#ff79c6', '36': '#8be9fd', '37': '#f8f8f2', '1;30': '#44475a', '1;31': '#ff5555',
        '1;32': '#50fa7b', '1;33': '#f1fa8c', '1;34': '#bd93f9', '1;35': '#ff79c6', '1;36': '#8be9fd',
        '1;37': '#ffffff', '39': '#E3E3E3', '0': '', '': ''
    }
    
    html = []
    lines = text.split('\n')
    for line in lines:
        parts = line.split('\x1b[')
        html.append(parts[0])
        open_spans = 0
        for part in parts[1:]:
            m = re.match(r'^([0-9;]*)m(.*)', part, re.DOTALL)
            if m:
                code = m.group(1)
                rest = m.group(2)
                if code == '0' or code == '':
                    if open_spans > 0:
                        html.append('</span>' * open_spans)
                        open_spans = 0
                else:
                    color = ansi_map.get(code, '#E3E3E3')
                    if open_spans > 0:
                        html.append('</span>' * open_spans)
                        open_spans = 0
                    html.append(f'<span style="color: {color};">')
                    open_spans += 1
                html.append(rest)
            else:
                html.append('\x1b[' + part)
                
        if open_spans > 0:
            html.append('</span>' * open_spans)
        html.append('<br>')
        
    return f"""<div style="white-space: pre; font-family: Consolas, monospace; line-height: 1.3;">{''.join(html)}</div>"""

class GraphView(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text']}; border: none; border-radius: 8px; padding: 12px;")
        self.last_raw_text = None

    def update_graph(self, state):
        if not state.isRepo:
            text = tr("not_a_repo")
            if self.last_raw_text != text:
                self.setPlainText(text)
                self.last_raw_text = text
            return
            
        if not state.commitHistory or (len(state.commitHistory) == 1 and not state.commitHistory[0]):
            text = tr("no_commits")
            if self.last_raw_text != text:
                self.setPlainText(text)
                self.last_raw_text = text
            return
            
        raw_text = "\n".join(state.commitHistory)
        if self.last_raw_text != raw_text:
            html = git_ansi_to_html(raw_text)
            scroll = self.verticalScrollBar().value()
            self.setHtml(html)
            self.verticalScrollBar().setValue(scroll)
            self.last_raw_text = raw_text
