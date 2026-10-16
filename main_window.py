# -*- coding: utf-8 -*-
"""
Main Window for Al-Bonyan ERP (نظام البنيان للمحاسبة وتجارة الحديد والأسمنت)
Features:
- Full Arabic Right-to-Left (RTL) layout
- Modern Sidebar Navigation across all 6 core modules + WhatsApp Quick Center
- Theme Switcher (Dark Mode / Light Mode) in Top Header Bar
- Clean Font Scaling selector (85%, 100%, 115%, 130%)
"""
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QComboBox,
    QStatusBar, QDialog, QGridLayout, QLineEdit, QTextEdit
)
from PyQt6.QtCore import Qt

from config import APP_NAME, APP_VERSION, CURRENCY_NAME, format_egp
from database import DatabaseManager
from theme import build_stylesheet
from services import WhatsAppService
from sync_server import start_sync_server, stop_sync_server, get_local_ip

from views.dashboard_view import DashboardView
from views.journal_view import JournalView
from views.inventory_view import InventoryView
from views.customers_view import CustomersView
from views.suppliers_view import SuppliersView
from views.employees_view import EmployeesView
from views.ai_invoice_view import AIInvoiceView
from views.settings_view import SettingsView


class WhatsAppHubDialog(QDialog):
    """Centralized WhatsApp Sharing & Quick Messaging Hub for Managers, Customers, and Suppliers."""
    def __init__(self, parent: QWidget, db: DatabaseManager):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("📲 مركز المشاركة السريعة والتقارير عبر واتساب (WhatsApp Hub)")
        self.setMinimumWidth(580)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QGridLayout()
        form.setSpacing(10)

        self.target_combo = QComboBox()
        self.target_combo.addItem(f"👔 الإدارة العليا / المدير المالي ({self.db.get_setting('manager_whatsapp', '201001234567')})", self.db.get_setting("manager_whatsapp", "201001234567"))
        for c in self.db.get_all_customers_with_balances():
            self.target_combo.addItem(f"👤 عميل: {c['name']} ({c['phone']})", c["phone"])
        for s in self.db.get_all_suppliers_with_balances():
            self.target_combo.addItem(f"🏭 مورد: {s['name']} ({s['phone']})", s["phone"])
        self.target_combo.currentIndexChanged.connect(self.on_target_changed)

        self.phone_in = QLineEdit(self.db.get_setting("manager_whatsapp", "201001234567"))
        self.phone_in.setPlaceholderText("رقم الهاتف بصيغة دولية مثل 201012345678")

        self.msg_edit = QTextEdit()
        self.msg_edit.setMinimumHeight(180)

        form.addWidget(QLabel("اختر المستلم:"), 0, 0)
        form.addWidget(self.target_combo, 0, 1)
        form.addWidget(QLabel("رقم الواتساب:"), 1, 0)
        form.addWidget(self.phone_in, 1, 1)
        form.addWidget(QLabel("نص التقرير / الرسالة:"), 2, 0, 1, 2)
        form.addWidget(self.msg_edit, 3, 0, 1, 2)
        layout.addLayout(form)

        # Quick Templates
        tpl_row = QHBoxLayout()
        b1 = QPushButton("📊 ملخص المركز المالي للمدير")
        b1.clicked.connect(self.fill_manager_report)
        b2 = QPushButton("🏗️ نشرة أسعار الحديد والأسمنت اليوم")
        b2.clicked.connect(self.fill_price_list_report)
        tpl_row.addWidget(b1)
        tpl_row.addWidget(b2)
        layout.addLayout(tpl_row)

        self.fill_manager_report()

        btns = QHBoxLayout()
        btns.addStretch()
        send_btn = QPushButton("📲 إرسال الآن عبر واتساب")
        send_btn.setProperty("class", "WhatsAppBtn")
        send_btn.clicked.connect(self.send_now)
        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(self.reject)
        btns.addWidget(send_btn)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

    def on_target_changed(self):
        phone = self.target_combo.currentData()
        if phone:
            self.phone_in.setText(str(phone))

    def fill_manager_report(self):
        stats = self.db.get_dashboard_summary()
        company = self.db.get_setting("company_name", "شركة البنيان لتجارة الحديد والأسمنت")
        txt = "\n".join([
            f"*{company}*",
            "━━━━━━━━━━━━━━━━━━━━",
            "📊 *ملخص المركز المالي والمخزني السريع*",
            f"• إجمالي المبيعات: {format_egp(stats['sales_total'])}",
            f"• إجمالي المشتريات: {format_egp(stats['purchases_total'])}",
            f"• قيمة المخزون بالتكلفة: {format_egp(stats['cost_valuation'])}",
            f"• مديونيات العملاء (لنا): {format_egp(stats['total_receivables'])}",
            f"• مستحقات الموردين (علينا): {format_egp(stats['total_payables'])}",
        ])
        self.msg_edit.setPlainText(txt)

    def fill_price_list_report(self):
        company = self.db.get_setting("company_name", "شركة البنيان لتجارة الحديد والأسمنت")
        items = self.db.get_items()
        lines = [
            f"*{company}*",
            "━━━━━━━━━━━━━━━━━━━━",
            "🏗️ *نشرة أسعار بيع الحديد والأسمنت المعتمدة اليوم*",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
        for it in items:
            lines.append(f"▪️ {it['name']}: *{format_egp(it['sale_price'])}* / {it['unit']}")
        lines.append("━━━━━━━━━━━━━━━━━━━━\nللحجز والتوريد المباشر للمواقع يرجى التواصل معنا.")
        self.msg_edit.setPlainText("\n".join(lines))

    def send_now(self):
        WhatsAppService.send_whatsapp_message(self.phone_in.text().strip(), self.msg_edit.toPlainText())
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_theme = self.db.get_setting("theme", "dark")
        try:
            self.current_scale = int(self.db.get_setting("font_scale", "100"))
        except ValueError:
            self.current_scale = 100

        self.setWindowTitle(f"{APP_NAME} — الإصدار {APP_VERSION}")
        self.setMinimumSize(1024, 660)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.nav_buttons = []
        self.init_ui()
        self.apply_theme_and_scale()

        # Start lightweight local Wi-Fi sync server for Android mobile app & browser
        try:
            self.sync_server = start_sync_server(self.db)
        except Exception as e:
            print(f"Warning: Could not start sync server: {e}")

    def init_ui(self):
        central = QWidget()
        central.setObjectName("CentralArea")
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Right Sidebar Navigation (in RTL layout, first widget in QHBoxLayout is on the RIGHT)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("SidebarFrame")
        self.sidebar.setFixedWidth(230)
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(10, 14, 10, 12)
        sb_layout.setSpacing(3)

        # Brand Identity Box
        brand_title = QLabel("🏗️ البنيان ERP")
        brand_title.setObjectName("BrandTitle")
        brand_sub = QLabel("إدارة وتجارة الحديد والأسمنت")
        brand_sub.setObjectName("BrandSubtitle")
        sb_layout.addWidget(brand_title)
        sb_layout.addWidget(brand_sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(148, 163, 184, 0.12); margin: 4px 0;")
        sb_layout.addWidget(sep)

        nav_items = [
            ("📊 الرئيسية والمركز المالي", 0),
            ("📘 اليومية وحركة القبض والصرف", 1),
            ("🏗️ المخازن والمخزون (حديد/أسمنت)", 2),
            ("👥 العملاء والأسعار المخصصة", 3),
            ("🏭 الموردين والمستحقات", 4),
            ("👔 الموظفين والرواتب", 5),
            ("🤖 قارئ الفواتير الذكي (AI OCR)", 6),
            ("⚙️ الإعدادات والنسخ الاحتياطي", 7),
        ]

        for text, idx in nav_items:
            btn = QPushButton(text)
            btn.setProperty("class", "NavButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self.switch_page(i))
            sb_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sb_layout.addStretch()

        # Quick WhatsApp Hub Button in Sidebar Footer
        wa_hub_btn = QPushButton("📲 مركز رسائل واتساب")
        wa_hub_btn.setProperty("class", "WhatsAppBtn")
        wa_hub_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        wa_hub_btn.clicked.connect(self.open_whatsapp_hub)
        sb_layout.addWidget(wa_hub_btn)

        curr_badge = QLabel(f"💵 العملة: {CURRENCY_NAME}")
        curr_badge.setStyleSheet("color: #8E9CAE; font-size: 10.5px; padding-top: 2px;")
        curr_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_layout.addWidget(curr_badge)

        root_layout.addWidget(self.sidebar)

        # 2. Main Content Area (Top Header Bar + Stacked Views)
        content_wrapper = QWidget()
        cw_layout = QVBoxLayout(content_wrapper)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.setSpacing(0)

        # Top Bar
        self.top_bar = QFrame()
        self.top_bar.setObjectName("TopBar")
        self.top_bar.setFixedHeight(52)
        tb_layout = QHBoxLayout(self.top_bar)
        tb_layout.setContentsMargins(16, 6, 16, 6)
        tb_layout.setSpacing(10)

        self.page_title_lbl = QLabel("📊 الرئيسية والمركز المالي")
        self.page_title_lbl.setObjectName("PageTitle")
        tb_layout.addWidget(self.page_title_lbl)

        tb_layout.addStretch()

        # Quick AI Reader Button in Top Bar
        quick_ai_btn = QPushButton("📸 قراءة فاتورة بالذكاء الاصطناعي")
        quick_ai_btn.setProperty("class", "GoldBtn")
        quick_ai_btn.clicked.connect(lambda: self.switch_page(6))
        tb_layout.addWidget(quick_ai_btn)

        # Font Scaling Selector
        tb_layout.addWidget(QLabel("🔍 حجم الخط:"))
        self.scale_combo = QComboBox()
        self.scale_options = [
            ("صغير (90%)", 90),
            ("قياسي (100%)", 100),
            ("كبير (115%)", 115),
            ("كبير جداً (130%)", 130),
        ]
        for label, val in self.scale_options:
            self.scale_combo.addItem(label, val)
        idx = self.scale_combo.findData(self.current_scale)
        if idx >= 0:
            self.scale_combo.setCurrentIndex(idx)
        self.scale_combo.currentIndexChanged.connect(self.on_scale_changed)
        tb_layout.addWidget(self.scale_combo)

        # Global Refresh Button in Top Bar
        global_refresh_btn = QPushButton("🔄 تحديث شامل")
        global_refresh_btn.setProperty("class", "PrimaryBtn")
        global_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        global_refresh_btn.setToolTip("إعادة تحميل وتحديث كافة البيانات من قاعدة البيانات فوراً")
        global_refresh_btn.clicked.connect(self.refresh_all_views)
        tb_layout.addWidget(global_refresh_btn)

        # Theme Switcher Button (Dark / Light Mode)
        self.theme_btn = QPushButton()
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        tb_layout.addWidget(self.theme_btn)

        cw_layout.addWidget(self.top_bar)

        # Stacked Pages
        self.stack = QStackedWidget()
        self.dashboard_view = DashboardView(self.db)
        self.journal_view = JournalView(self.db)
        self.inventory_view = InventoryView(self.db)
        self.customers_view = CustomersView(self.db)
        self.suppliers_view = SuppliersView(self.db)
        self.employees_view = EmployeesView(self.db)
        self.ai_invoice_view = AIInvoiceView(self.db)
        self.settings_view = SettingsView(self.db)

        self.stack.addWidget(self.dashboard_view)   # 0
        self.stack.addWidget(self.journal_view)     # 1
        self.stack.addWidget(self.inventory_view)   # 2
        self.stack.addWidget(self.customers_view)   # 3
        self.stack.addWidget(self.suppliers_view)   # 4
        self.stack.addWidget(self.employees_view)   # 5
        self.stack.addWidget(self.ai_invoice_view)  # 6
        self.stack.addWidget(self.settings_view)    # 7

        # Connect cross-module refresh signals so changes anywhere update all modules immediately
        self.dashboard_view.navigate_requested.connect(self.switch_page)
        self.dashboard_view.open_ai_invoice_requested.connect(lambda: self.switch_page(6))
        self.settings_view.appearance_changed.connect(self.on_settings_appearance_changed)

        for view in (
            self.journal_view,
            self.inventory_view,
            self.customers_view,
            self.suppliers_view,
            self.employees_view,
            self.ai_invoice_view,
            self.settings_view,
        ):
            view.data_changed.connect(self.refresh_all_views)

        cw_layout.addWidget(self.stack, 1)
        root_layout.addWidget(content_wrapper, 1)

        # Status Bar
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage(
            "✅ النظام متصل بقاعدة البيانات المحلية (SQLite WAL) | العملة: جنيه مصري (ج.م) | دعم كامل للغة العربية (RTL)"
        )

        self.switch_page(0)

    def switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        titles = [
            "📊 الرئيسية والمركز المالي والمخزني",
            "📘 سجل اليومية وحركة القبض والصرف (Cash-In & Cash-Out)",
            "🏗️ إدارة المخازن ومخزون الحديد والأسمنت (Inventory & Warehouses)",
            "👥 إدارة العملاء والأسعار المخصصة وكشوف الحساب",
            "🏭 إدارة الموردين والمصانع وتقارير أعمار الديون",
            "👔 شؤون الموظفين ومسير الرواتب الشهري (Payroll)",
            "🤖 قارئ الفواتير بالذكاء الاصطناعي (AI Invoice OCR)",
            "⚙️ الإعدادات العامة وبيانات الشركة والنسخ الاحتياطي",
        ]
        if 0 <= index < len(titles):
            self.page_title_lbl.setText(titles[index])

        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Refresh active view
        widget = self.stack.currentWidget()
        if hasattr(widget, "refresh_data"):
            widget.refresh_data()
        elif hasattr(widget, "refresh_warehouses"):
            widget.refresh_warehouses()

    def refresh_all_views(self):
        self.dashboard_view.refresh_data()
        self.journal_view.refresh_data()
        self.inventory_view.refresh_data()
        self.customers_view.refresh_data()
        self.suppliers_view.refresh_data()
        self.employees_view.refresh_data()
        if hasattr(self.ai_invoice_view, "refresh_data"):
            self.ai_invoice_view.refresh_data()
        else:
            self.ai_invoice_view.refresh_warehouses()
        self.settings_view.refresh_data()
        self.statusBar().showMessage("✅ تم تحديث كافة البيانات من قاعدة البيانات المحلية بنجاح", 4000)

    def on_settings_appearance_changed(self, theme: str, scale: int):
        self.current_theme = theme
        self.current_scale = int(scale)
        self.scale_combo.blockSignals(True)
        idx = self.scale_combo.findData(self.current_scale)
        if idx >= 0:
            self.scale_combo.setCurrentIndex(idx)
        self.scale_combo.blockSignals(False)
        self.apply_theme_and_scale()

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.db.set_setting("theme", self.current_theme)
        self.apply_theme_and_scale()
        self.settings_view.refresh_data()

    def on_scale_changed(self):
        val = self.scale_combo.currentData()
        if val:
            self.current_scale = int(val)
            self.db.set_setting("font_scale", str(self.current_scale))
            self.apply_theme_and_scale()
            self.settings_view.refresh_data()

    def apply_theme_and_scale(self):
        if self.current_theme == "dark":
            self.theme_btn.setText("☀️ الوضع النهاري المريح")
        else:
            self.theme_btn.setText("🌙 الوضع الليلي الهادئ")

        qss = build_stylesheet(self.current_theme, self.current_scale)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)

        from PyQt6.QtWidgets import QTableWidget
        from views import fit_table_columns
        for tbl in self.findChildren(QTableWidget):
            fit_table_columns(tbl, update_items=False)

    def open_whatsapp_hub(self):
        dlg = WhatsAppHubDialog(self, self.db)
        dlg.exec()

    def closeEvent(self, event):
        try:
            stop_sync_server()
        except Exception:
            pass
        super().closeEvent(event)

