# -*- coding: utf-8 -*-
"""
Compact, Ultra-Clean Minimalist Design System for Al-Bonyan ERP
Optimized for Standard Desktop Screens (1366x768 / 1920x1080 / 1280x720):
- Low eye fatigue matte surfaces (Slate Dark & Soft Cloud Light)
- Compact, balanced padding & spacing so all tables and forms fit 100% on screen
- Modern flat aesthetic with hairline borders and soft accents (teal, sky blue, sage)
"""

def build_stylesheet(theme: str = "dark", scale_percent: int = 100) -> str:
    scale = max(0.8, min(1.3, scale_percent / 100.0))

    f_base = int(round(12 * scale))
    f_small = int(round(10.5 * scale))
    f_medium = int(round(13 * scale))
    f_large = int(round(15 * scale))
    f_xlarge = int(round(17 * scale))

    pad_btn_v = int(round(5 * scale))
    pad_btn_h = int(round(12 * scale))
    pad_input_v = int(round(5 * scale))
    pad_input_h = int(round(10 * scale))

    if theme == "dark":
        # Ultra-clean matte slate dark (zero glare)
        bg_canvas = "#0F1319"       # Deep slate canvas
        bg_surface = "#161B22"      # Flat card surface
        bg_card = "#161B22"
        bg_subtle = "#1F242C"       # Subtle element backdrop
        bg_input = "#0F1319"        # Inset input
        bg_sidebar = "#0B0E13"      # Clean sidebar
        
        border_subtle = "#262C36"   # Whisper hairline border
        border_light = "#1D232C"    # Table grid divider
        
        text_primary = "#E6EDF3"    # Warm matte text
        text_secondary = "#848D97"  # Muted secondary text
        text_tertiary = "#57606A"
        
        accent_blue = "#388BFD"
        accent_blue_hover = "#58A6FF"
        accent_teal = "#238636"
        accent_teal_hover = "#2EA043"
        accent_danger = "#DA3633"
        accent_danger_hover = "#F85149"
        accent_amber = "#D29922"
        accent_amber_hover = "#E3B341"
        accent_wa = "#238636"
        
        table_hdr_bg = "#161B22"
        table_alt_bg = "#12161D"
        table_sel_bg = "#1F2937"
        table_sel_txt = "#58A6FF"
        scrollbar_thumb = "#2C3440"
        scrollbar_hover = "#3D4856"
    else:
        # Ultra-clean soft paper cloud light
        bg_canvas = "#F4F6F8"
        bg_surface = "#FFFFFF"
        bg_card = "#FFFFFF"
        bg_subtle = "#F0F2F5"
        bg_input = "#FAFAFA"
        bg_sidebar = "#111827"
        
        border_subtle = "#E1E4E8"
        border_light = "#F0F2F5"
        
        text_primary = "#1F2328"
        text_secondary = "#656D76"
        text_tertiary = "#8C959F"
        
        accent_blue = "#1F6FEB"
        accent_blue_hover = "#388BFD"
        accent_teal = "#1A7F37"
        accent_teal_hover = "#2DA44E"
        accent_danger = "#CF222E"
        accent_danger_hover = "#FA4549"
        accent_amber = "#BF8700"
        accent_amber_hover = "#D4A72C"
        accent_wa = "#1A7F37"
        
        table_hdr_bg = "#F6F8FA"
        table_alt_bg = "#FBFCFD"
        table_sel_bg = "#EBF5FF"
        table_sel_txt = "#0969DA"
        scrollbar_thumb = "#D0D7DE"
        scrollbar_hover = "#AFB8C1"

    return f"""
        * {{
            font-family: "Segoe UI", "Cairo", "Tahoma", sans-serif;
            font-size: {f_base}px;
            color: {text_primary};
            outline: none;
        }}
        QMainWindow, QDialog {{
            background-color: {bg_canvas};
        }}
        QWidget#CentralArea {{
            background-color: {bg_canvas};
        }}

        /* Slim 5px Scrollbars */
        QScrollBar:vertical {{
            background: transparent;
            width: 5px;
            margin: 0;
            border-radius: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {scrollbar_thumb};
            min-height: 24px;
            border-radius: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {scrollbar_hover};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 5px;
            margin: 0;
            border-radius: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: {scrollbar_thumb};
            min-width: 24px;
            border-radius: 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {scrollbar_hover};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}

        /* Compact Sidebar */
        QFrame#SidebarFrame {{
            background-color: {bg_sidebar};
            border: none;
            border-left: 1px solid {border_subtle if theme == 'dark' else '#1E2530'};
        }}
        QLabel#BrandTitle {{
            color: #FFFFFF;
            font-size: {f_large}px;
            font-weight: 700;
        }}
        QLabel#BrandSubtitle {{
            color: #8B949E;
            font-size: {f_small}px;
            font-weight: 500;
        }}
        QPushButton.NavButton {{
            background-color: transparent;
            color: #9CA3AF;
            text-align: right;
            padding: {int(round(7 * scale))}px {int(round(12 * scale))}px;
            border-radius: 6px;
            font-size: {f_medium}px;
            font-weight: 600;
            border: none;
            margin: 1px 0;
        }}
        QPushButton.NavButton:hover {{
            background-color: {'#161B22' if theme == 'dark' else '#1F2937'};
            color: #F3F4F6;
        }}
        QPushButton.NavButton[active="true"] {{
            background-color: {'#1F2937' if theme == 'dark' else '#374151'};
            color: #38BDF8;
            font-weight: 700;
            border-right: 3px solid #38BDF8;
        }}

        /* Compact Top Bar */
        QFrame#TopBar {{
            background-color: {bg_surface};
            border-bottom: 1px solid {border_subtle};
        }}
        QLabel#PageTitle {{
            font-size: {f_large}px;
            font-weight: 700;
            color: {text_primary};
        }}

        /* Minimalist Cards */
        QFrame.CardFrame {{
            background-color: {bg_card};
            border: 1px solid {border_subtle};
            border-radius: 8px;
        }}
        QLabel.CardTitle {{
            color: {text_secondary};
            font-size: {f_small}px;
            font-weight: 500;
        }}
        QLabel.CardValue {{
            color: {text_primary};
            font-size: {f_large}px;
            font-weight: 700;
        }}
        QLabel.SectionHeader {{
            font-size: {f_medium}px;
            font-weight: 700;
            color: {text_primary};
        }}

        /* Compact Flat Inputs */
        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateEdit, QTextEdit {{
            background-color: {bg_input};
            border: 1px solid {border_subtle};
            border-radius: 6px;
            padding: {pad_input_v}px {pad_input_h}px;
            color: {text_primary};
            selection-background-color: {accent_blue};
            selection-color: #FFFFFF;
        }}
        QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QDateEdit:focus, QTextEdit:focus {{
            border: 1.5px solid {accent_blue};
            background-color: {bg_surface};
        }}
        QLineEdit::placeholder {{
            color: {text_tertiary};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {bg_card};
            border: 1px solid {border_subtle};
            border-radius: 6px;
            selection-background-color: {table_sel_bg};
            selection-color: {table_sel_txt};
            padding: 4px;
        }}

        /* Compact Flat Buttons */
        QPushButton {{
            background-color: {bg_subtle if theme == 'dark' else '#FFFFFF'};
            border: 1px solid {border_subtle};
            border-radius: 6px;
            padding: {pad_btn_v}px {pad_btn_h}px;
            font-weight: 600;
            color: {text_primary};
        }}
        QPushButton:hover {{
            background-color: {'#2A323D' if theme == 'dark' else '#F3F4F6'};
            border-color: {accent_blue};
            color: {text_primary};
        }}
        QPushButton.PrimaryBtn {{
            background-color: {accent_blue};
            color: #FFFFFF;
            border: none;
            font-weight: 600;
        }}
        QPushButton.PrimaryBtn:hover {{
            background-color: {accent_blue_hover};
        }}
        QPushButton.SuccessBtn {{
            background-color: {accent_teal};
            color: #FFFFFF;
            border: none;
            font-weight: 600;
        }}
        QPushButton.SuccessBtn:hover {{
            background-color: {accent_teal_hover};
        }}
        QPushButton.DangerBtn {{
            background-color: {accent_danger};
            color: #FFFFFF;
            border: none;
            font-weight: 600;
        }}
        QPushButton.DangerBtn:hover {{
            background-color: {accent_danger_hover};
        }}
        QPushButton.GoldBtn {{
            background-color: {accent_amber};
            color: #FFFFFF;
            border: none;
            font-weight: 600;
        }}
        QPushButton.GoldBtn:hover {{
            background-color: {accent_amber_hover};
        }}
        QPushButton.WhatsAppBtn {{
            background-color: {accent_wa};
            color: #FFFFFF;
            border: none;
            font-weight: 600;
        }}
        QPushButton.WhatsAppBtn:hover {{
            background-color: {accent_teal_hover};
        }}

        /* Modern Flat Compact Tables */
        QTableWidget {{
            background-color: {bg_surface};
            alternate-background-color: {table_alt_bg};
            border: 1px solid {border_subtle};
            border-radius: 8px;
            gridline-color: {border_light};
            selection-background-color: {table_sel_bg};
            selection-color: {table_sel_txt};
        }}
        QTableWidget::item {{
            padding: 3px {int(round(8 * scale))}px;
            border: none;
        }}
        QHeaderView::section {{
            background-color: {table_hdr_bg};
            color: {text_secondary};
            font-weight: 600;
            font-size: {f_small}px;
            padding: {int(round(6 * scale))}px {int(round(8 * scale))}px;
            border: none;
            border-bottom: 1.5px solid {border_subtle};
            border-left: 1px solid {border_light};
        }}

        /* Flat Tabs */
        QTabWidget::pane {{
            border: 1px solid {border_subtle};
            background-color: {bg_surface};
            border-radius: 8px;
            padding: 8px;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {text_secondary};
            padding: {int(round(6 * scale))}px {int(round(16 * scale))}px;
            border-bottom: 2px solid transparent;
            font-weight: 600;
            margin-left: 4px;
        }}
        QTabBar::tab:hover {{
            color: {text_primary};
        }}
        QTabBar::tab:selected {{
            color: {accent_blue};
            border-bottom: 2px solid {accent_blue};
        }}

        /* Checkbox */
        QCheckBox {{
            spacing: 6px;
            color: {text_primary};
            font-weight: 500;
        }}
        QCheckBox::indicator {{
            width: 15px;
            height: 15px;
            border-radius: 4px;
            border: 1px solid {border_subtle};
            background-color: {bg_input};
        }}
        QCheckBox::indicator:checked {{
            background-color: {accent_blue};
            border-color: {accent_blue};
        }}

        /* Status Bar */
        QStatusBar {{
            background-color: {bg_surface};
            color: {text_secondary};
            font-size: {f_small}px;
            border-top: 1px solid {border_subtle};
            padding: 2px 10px;
        }}
        QProgressBar {{
            border: 1px solid {border_subtle};
            border-radius: 4px;
            text-align: center;
            background-color: {bg_input};
            height: 10px;
        }}
        QProgressBar::chunk {{
            background-color: {accent_blue};
            border-radius: 3px;
        }}
    """
