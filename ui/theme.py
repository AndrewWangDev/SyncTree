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
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {COLORS['text']};
}}

QLineEdit:focus {{
    border: 2px solid {COLORS['primary']};
}}

QLineEdit:disabled {{
    opacity: 0.3;
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
