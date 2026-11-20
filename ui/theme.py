# Material You Dark Theme Colors
COLORS = {
    "background": "#121212",
    "surface": "#1E1E1E",
    "surface_variant": "#2E2E2E",
    "primary": "#A8C7FA",         # Light Blue
    "on_primary": "#000000",
    "secondary": "#7FCFFF",       
    "error": "#FFB4AB",
    "on_error": "#690005",
    "warning": "#FFD54F",
    "success": "#81C995",
    "text": "#E3E3E3",
    "text_disabled": "#8E8E8E",
    "border": "#44474E"
}

QSS = f"""
QMainWindow {{
    background-color: {COLORS['background']};
}}

QWidget {{
    color: {COLORS['text']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
}}

QLineEdit {{
    background-color: {COLORS['surface_variant']};
    border: 1.5px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 12px;
    min-height: 24px;
    color: {COLORS['text']};
}}

QLineEdit:focus {{
    border: 1.5px solid {COLORS['primary']};
}}

QLineEdit:disabled {{
    color: rgba(227, 227, 227, 0.35);
    background-color: rgba(46, 46, 46, 0.4);
    border-color: rgba(68, 71, 78, 0.4);
}}

QComboBox {{
    background-color: {COLORS['surface_variant']};
    color: {COLORS['text']};
    border: 1.5px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 36px 6px 12px;
    min-height: 24px;
    font-size: 14px;
}}

QComboBox:focus {{
    border: 1.5px solid {COLORS['primary']};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 36px;
    border-left: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}}

QComboBox::down-arrow {{
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['text']};
    margin-right: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {COLORS['surface_variant']};
    outline: none;
}}

/* For standard buttons that might not use the custom paintEvent */
QPushButton {{
    background-color: {COLORS['surface_variant']};
    border: none;
    border-radius: 12px;
    padding: 8px 16px;
    color: {COLORS['text']};
}}

QPushButton:disabled {{
    background-color: {COLORS['background']};
    color: {COLORS['text_disabled']};
}}
"""
