# -*- coding: utf-8 -*-
"""
Kivy UI Components for Al-Bonyan ERP Mobile App.
Includes:
- Dashboard Screen (KPI Cards + Recent Transactions)
- Journal Screen (Transactions List + Add Transaction Modal)
- Inventory Screen (Iron & Cement stock with weights & values)
- Customers Screen (Accounts & Balances)
- Settings Screen (Wi-Fi Server IP, Port, Connection Test, Offline Mode)
"""
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp
from kivy.clock import Clock

from mobile_app.arabic_helper import ar, get_arabic_font
from mobile_app.api_client import MobileDataClient

FONT_NAME = get_arabic_font()

# Modern Slate Color Palette
C_BG = (0.059, 0.090, 0.165, 1.0)       # #0f172a
C_SURFACE = (0.118, 0.161, 0.231, 1.0)  # #1e293b
C_CARD = (0.137, 0.192, 0.278, 1.0)     # #233147
C_BORDER = (0.200, 0.275, 0.380, 1.0)   # #334661
C_PRIMARY = (0.008, 0.518, 0.780, 1.0)  # #0284c7
C_SUCCESS = (0.063, 0.725, 0.506, 1.0)  # #10b981
C_DANGER = (0.937, 0.267, 0.267, 1.0)   # #ef4444
C_WARNING = (0.961, 0.620, 0.043, 1.0)  # #f59e0b
C_TEXT = (0.973, 0.980, 0.988, 1.0)     # #f8fafc
C_MUTED = (0.580, 0.639, 0.722, 1.0)    # #94a3b8


class CardBox(BoxLayout):
    """Reusable card container with rounded corners and subtle border."""
    def __init__(self, bg_color=C_CARD, border_color=C_BORDER, radius=10, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        self.radius = radius
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            Color(*self.border_color)
            Line(rounded_rectangle=[self.pos[0], self.pos[1], self.size[0], self.size[1], self.radius], width=1)


class ArLabel(Label):
    """Arabic-aware Label with auto-reshaping and proper font."""
    def __init__(self, text="", raw=False, **kwargs):
        super().__init__(**kwargs)
        self.font_name = FONT_NAME
        self.color = C_TEXT
        self.raw = raw
        if text:
            self.set_arabic_text(text)

    def set_arabic_text(self, text: str):
        if self.raw:
            self.text = text
        else:
            self.text = ar(str(text))


class ArButton(Button):
    """Arabic-aware styled button."""
    def __init__(self, text="", bg_color=C_PRIMARY, **kwargs):
        super().__init__(**kwargs)
        self.font_name = FONT_NAME
        self.background_normal = ''
        self.background_color = bg_color
        self.color = C_TEXT
        if text:
            self.text = ar(str(text))


# =============================================================================
# Screen 1: Dashboard
# =============================================================================
class DashboardScreen(Screen):
    def __init__(self, client: MobileDataClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.init_ui()

    def init_ui(self):
        root = BoxLayout(orientation='vertical')
        
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(14), size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter('height'))

        # Header Title
        header = CardBox(bg_color=C_SURFACE, orientation='vertical', size_hint_y=None, height=dp(70), padding=dp(10))
        h_title = ArLabel(text="نظام البنيان - لوحة التحكم المالية", font_size='18sp', bold=True)
        h_sub = ArLabel(text="متابعة السيولة وحركة المخزون والديون لحظياً", font_size='12sp', color=C_MUTED)
        header.add_widget(h_title)
        header.add_widget(h_sub)
        self.content.add_widget(header)

        # KPI Container
        self.kpi_grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        self.kpi_grid.bind(minimum_height=self.kpi_grid.setter('height'))
        self.content.add_widget(self.kpi_grid)

        # Recent Transactions Header
        t_header = CardBox(bg_color=C_SURFACE, orientation='horizontal', size_hint_y=None, height=dp(40), padding=[dp(10), dp(5)])
        t_title = ArLabel(text="آخر العمليات اليومية المسجلة", font_size='14sp', bold=True)
        t_header.add_widget(t_title)
        self.content.add_widget(t_header)

        # Recent List
        self.recent_list = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None)
        self.recent_list.bind(minimum_height=self.recent_list.setter('height'))
        self.content.add_widget(self.recent_list)

        scroll.add_widget(self.content)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self):
        self.refresh_data()

    def refresh_data(self):
        data = self.client.get_dashboard()
        kpis = data.get("kpis", {})

        self.kpi_grid.clear_widgets()
        kpi_items = [
            ("المقبوضات النقدية", f"{kpis.get('total_cash_in', 0):,.2f} ج.م", C_SUCCESS),
            ("المدفوعات والمصروفات", f"{kpis.get('total_cash_out', 0):,.2f} ج.م", C_DANGER),
            ("صافي النقدية بالخزينة", f"{kpis.get('net_cash', 0):,.2f} ج.م", C_PRIMARY),
            ("قيمة بضاعة المخازن", f"{kpis.get('inventory_valuation', 0):,.2f} ج.م", C_WARNING),
            ("ديون العملاء (لنا)", f"{kpis.get('customers_balance', 0):,.2f} ج.م", C_PRIMARY),
            ("مستحقات الموردين (علينا)", f"{kpis.get('suppliers_balance', 0):,.2f} ج.م", C_DANGER),
        ]

        for title, val, col in kpi_items:
            card = CardBox(bg_color=C_SURFACE, border_color=col, orientation='vertical', size_hint_y=None, height=dp(85), padding=dp(8), spacing=dp(4))
            t_lbl = ArLabel(text=title, font_size='11sp', color=C_MUTED)
            v_lbl = ArLabel(text=val, font_size='14sp', bold=True, color=col)
            card.add_widget(t_lbl)
            card.add_widget(v_lbl)
            self.kpi_grid.add_widget(card)

        # Recent Transactions
        self.recent_list.clear_widgets()
        recents = data.get("recent_transactions", [])
        if not recents:
            empty_card = CardBox(bg_color=C_SURFACE, size_hint_y=None, height=dp(60))
            empty_card.add_widget(ArLabel(text="لا توجد حركات مسجلة مؤخراً", color=C_MUTED))
            self.recent_list.add_widget(empty_card)
        else:
            for item in recents:
                card = CardBox(bg_color=C_SURFACE, orientation='vertical', size_hint_y=None, height=dp(70), padding=dp(8), spacing=dp(2))
                row1 = BoxLayout(orientation='horizontal')
                desc = item.get("description") or item.get("category") or "حركة مالية"
                r_desc = ArLabel(text=desc[:30], font_size='13sp', bold=True)
                amt = float(item.get("amount") or item.get("debit_amount") or item.get("credit_amount") or 0)
                flow_val = str(item.get("flow_type") or item.get("debit_account") or item.get("entry_type") or "")
                is_in = (item.get("debit_amount", 0) > 0 or item.get("entry_type") in ('sale', 'receipt', 'cust_pay') or "وارد" in flow_val or "قبض" in flow_val)
                amt_col = C_SUCCESS if is_in else C_DANGER
                r_amt = ArLabel(text=f"{amt:,.2f} ج.م", font_size='13sp', bold=True, color=amt_col)
                row1.add_widget(r_desc)
                row1.add_widget(r_amt)

                row2 = BoxLayout(orientation='horizontal')
                date_str = item.get("entry_date", "")
                cat_str = item.get("category", "")
                r_sub = ArLabel(text=f"{date_str} | {cat_str}", font_size='11sp', color=C_MUTED)
                row2.add_widget(r_sub)

                card.add_widget(row1)
                card.add_widget(row2)
                self.recent_list.add_widget(card)


# =============================================================================
# Screen 2: Journal & Daily Transactions
# =============================================================================
class AddTransactionPopup(Popup):
    def __init__(self, client: MobileDataClient, on_saved_callback, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.on_saved_callback = on_saved_callback
        self.title = ar("إضافة حركة يومية جديدة (قبض / صرف / مبيعات)")
        self.title_font = FONT_NAME
        self.size_hint = (0.95, 0.85)
        self.init_ui()

    def init_ui(self):
        layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(12))

        # Type Spinner
        t_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8))
        t_row.add_widget(ArLabel(text="نوع الحركة:", size_hint_x=0.35))
        self.type_spinner = Spinner(
            text=ar("مبيعات نقدية"),
            values=[ar("مبيعات نقدية"), ar("سند قبض نقدي"), ar("مشتريات نقدية"), ar("سند صرف نقدي"), ar("مصروفات عامة")],
            font_name=FONT_NAME,
            size_hint_x=0.65
        )
        t_row.add_widget(self.type_spinner)
        layout.add_widget(t_row)

        # Amount Input
        a_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8))
        a_row.add_widget(ArLabel(text="المبلغ (ج.م):", size_hint_x=0.35))
        self.amount_input = TextInput(text="", multiline=False, input_filter='float', size_hint_x=0.65, font_size='16sp')
        a_row.add_widget(self.amount_input)
        layout.add_widget(a_row)

        # Category Input
        c_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8))
        c_row.add_widget(ArLabel(text="التصنيف / البند:", size_hint_x=0.35))
        self.category_input = TextInput(text="عام", multiline=False, size_hint_x=0.65, font_name=FONT_NAME)
        c_row.add_widget(self.category_input)
        layout.add_widget(c_row)

        # Payment Method
        p_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8))
        p_row.add_widget(ArLabel(text="طريقة الدفع:", size_hint_x=0.35))
        self.pay_spinner = Spinner(
            text=ar("نقدي (كاش)"),
            values=[ar("نقدي (كاش)"), ar("تحويل بنكي"), ar("فودافون كاش / إنستاباي"), ar("شيك")],
            font_name=FONT_NAME,
            size_hint_x=0.65
        )
        p_row.add_widget(self.pay_spinner)
        layout.add_widget(p_row)

        # Description
        layout.add_widget(ArLabel(text="البيان / تفاصيل الحركة:", size_hint_y=None, height=dp(25)))
        self.desc_input = TextInput(text="", multiline=True, font_name=FONT_NAME, size_hint_y=1)
        layout.add_widget(self.desc_input)

        # Status / Error Label
        self.status_lbl = ArLabel(text="", size_hint_y=None, height=dp(25), color=C_WARNING)
        layout.add_widget(self.status_lbl)

        # Buttons
        btns = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(45))
        save_btn = ArButton(text="💾 حفظ وإرسال", bg_color=C_SUCCESS)
        save_btn.bind(on_press=self.save_entry)
        cancel_btn = ArButton(text="إلغاء", bg_color=C_SURFACE)
        cancel_btn.bind(on_press=self.dismiss)
        btns.add_widget(save_btn)
        btns.add_widget(cancel_btn)
        layout.add_widget(btns)

        self.content = layout

    def save_entry(self, instance):
        amt_str = self.amount_input.text.strip()
        if not amt_str:
            self.status_lbl.set_arabic_text("يرجى إدخال المبلغ بشكل صحيح")
            return
        try:
            amt = float(amt_str)
            if amt <= 0:
                self.status_lbl.set_arabic_text("المبلغ يجب أن يكون أكبر من صفر")
                return
        except ValueError:
            self.status_lbl.set_arabic_text("المبلغ غير صالح")
            return

        # Map spinner to backend entry_type
        raw_type = self.type_spinner.text
        type_map = {
            ar("مبيعات نقدية"): "sale",
            ar("سند قبض نقدي"): "receipt",
            ar("مشتريات نقدية"): "purchase",
            ar("سند صرف نقدي"): "payment",
            ar("مصروفات عامة"): "expense"
        }
        entry_type = type_map.get(raw_type, "sale")

        entry_data = {
            "entry_date": datetime.now().strftime("%Y-%m-%d"),
            "entry_type": entry_type,
            "category": self.category_input.text.strip() or "عام",
            "amount": amt,
            "description": self.desc_input.text.strip(),
            "payment_method": "cash" if "نقدي" in self.pay_spinner.text else "transfer",
            "reference_no": "",
            "created_by": "تطبيق الهاتف الذكي"
        }

        res = self.client.add_journal_entry(entry_data)
        if res.get("success"):
            self.dismiss()
            if self.on_saved_callback:
                self.on_saved_callback()
        else:
            self.status_lbl.set_arabic_text(res.get("message", "حدث خطأ أثناء الحفظ"))


class JournalScreen(Screen):
    def __init__(self, client: MobileDataClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.init_ui()

    def init_ui(self):
        root = BoxLayout(orientation='vertical')

        # Action Bar with Add Button
        top_bar = CardBox(bg_color=C_SURFACE, orientation='horizontal', size_hint_y=None, height=dp(55), padding=dp(8), spacing=dp(8))
        title = ArLabel(text="سجل اليومية وحركات الصندوق", font_size='15sp', bold=True)
        add_btn = ArButton(text="➕ إضافة قيد", bg_color=C_SUCCESS, size_hint_x=0.35)
        add_btn.bind(on_press=self.open_add_dialog)
        top_bar.add_widget(title)
        top_bar.add_widget(add_btn)
        root.add_widget(top_bar)

        # Scrollable Journal List
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.list_layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10), size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self):
        self.refresh_data()

    def refresh_data(self):
        entries = self.client.get_journal_entries(limit=50)
        self.list_layout.clear_widgets()
        if not entries:
            empty = CardBox(bg_color=C_SURFACE, size_hint_y=None, height=dp(60))
            empty.add_widget(ArLabel(text="لا توجد قيود مسجلة", color=C_MUTED))
            self.list_layout.add_widget(empty)
            return

        for e in entries:
            amt = float(e.get("amount") or e.get("debit_amount") or e.get("credit_amount") or 0)
            flow_val = str(e.get("flow_type") or e.get("debit_account") or e.get("entry_type") or "")
            is_in = (e.get("debit_amount", 0) > 0 or e.get("entry_type") in ('sale', 'receipt', 'cust_pay') or "وارد" in flow_val or "قبض" in flow_val)
            col = C_SUCCESS if is_in else C_DANGER

            card = CardBox(bg_color=C_SURFACE, border_color=col, orientation='vertical', size_hint_y=None, height=dp(80), padding=dp(10), spacing=dp(3))
            
            r1 = BoxLayout(orientation='horizontal')
            desc = e.get("description") or e.get("category") or "قيد يومية"
            lbl_desc = ArLabel(text=desc[:28], font_size='13sp', bold=True)
            lbl_amt = ArLabel(text=f"{amt:,.2f} ج.م", font_size='14sp', bold=True, color=col)
            r1.add_widget(lbl_desc)
            r1.add_widget(lbl_amt)

            r2 = BoxLayout(orientation='horizontal')
            d_str = e.get("entry_date", "")
            cat = e.get("category", "")
            lbl_sub = ArLabel(text=f"{d_str} | {cat}", font_size='11sp', color=C_MUTED)
            pay_str = str(e.get("payment_method") or "")
            pay = "نقداً" if ("نقدي" in pay_str or "cash" in pay_str.lower()) else "تحويل"
            lbl_pay = ArLabel(text=pay, font_size='11sp', color=C_MUTED)
            r2.add_widget(lbl_sub)
            r2.add_widget(lbl_pay)

            card.add_widget(r1)
            card.add_widget(r2)
            self.list_layout.add_widget(card)

    def open_add_dialog(self, instance):
        popup = AddTransactionPopup(self.client, on_saved_callback=self.refresh_data)
        popup.open()


# =============================================================================
# Screen 3: Inventory (حديد وأسمنت)
# =============================================================================
class InventoryScreen(Screen):
    def __init__(self, client: MobileDataClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.current_filter = None
        self.init_ui()

    def init_ui(self):
        root = BoxLayout(orientation='vertical')

        # Filter Tabs
        filter_bar = CardBox(bg_color=C_SURFACE, orientation='horizontal', size_hint_y=None, height=dp(48), padding=dp(4), spacing=dp(6))
        b_all = ArButton(text="الكل", bg_color=C_PRIMARY, size_hint_x=0.33)
        b_iron = ArButton(text="حديد تسليح", bg_color=C_SURFACE, size_hint_x=0.33)
        b_cement = ArButton(text="أسمنت وبياض", bg_color=C_SURFACE, size_hint_x=0.33)

        b_all.bind(on_press=lambda inst: self.set_filter(None, inst, [b_all, b_iron, b_cement]))
        b_iron.bind(on_press=lambda inst: self.set_filter("حديد", inst, [b_all, b_iron, b_cement]))
        b_cement.bind(on_press=lambda inst: self.set_filter("أسمنت", inst, [b_all, b_iron, b_cement]))

        filter_bar.add_widget(b_all)
        filter_bar.add_widget(b_iron)
        filter_bar.add_widget(b_cement)
        root.add_widget(filter_bar)

        # Scrollable items
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.items_layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10), size_hint_y=None)
        self.items_layout.bind(minimum_height=self.items_layout.setter('height'))
        scroll.add_widget(self.items_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def set_filter(self, cat, active_btn, all_btns):
        self.current_filter = cat
        for b in all_btns:
            b.background_color = C_PRIMARY if b == active_btn else C_SURFACE
        self.refresh_data()

    def on_pre_enter(self):
        self.refresh_data()

    def refresh_data(self):
        items = self.client.get_inventory(category=self.current_filter)
        self.items_layout.clear_widgets()
        if not items:
            empty = CardBox(bg_color=C_SURFACE, size_hint_y=None, height=dp(60))
            empty.add_widget(ArLabel(text="لا توجد أصناف مسجلة بالمخازن", color=C_MUTED))
            self.items_layout.add_widget(empty)
            return

        for it in items:
            card = CardBox(bg_color=C_SURFACE, orientation='vertical', size_hint_y=None, height=dp(85), padding=dp(10), spacing=dp(3))
            
            r1 = BoxLayout(orientation='horizontal')
            name = it.get("name", "صنف")
            lbl_name = ArLabel(text=name, font_size='14sp', bold=True)
            qty = float(it.get("quantity", 0))
            unit = it.get("unit", "طن")
            lbl_qty = ArLabel(text=f"{qty:,.2f} {unit}", font_size='14sp', bold=True, color=C_WARNING)
            r1.add_widget(lbl_name)
            r1.add_widget(lbl_qty)

            r2 = BoxLayout(orientation='horizontal')
            wh = it.get("warehouse_name") or "المخزن الرئيسي"
            code = it.get("code") or it.get("item_code") or ""
            lbl_wh = ArLabel(text=f"كود: {code} | {wh}", font_size='11sp', color=C_MUTED)
            price = float(it.get("cost_price") or it.get("purchase_price") or 0)
            lbl_price = ArLabel(text=f"شراء: {price:,.2f} ج.م", font_size='11sp', color=C_MUTED)
            r2.add_widget(lbl_wh)
            r2.add_widget(lbl_price)

            card.add_widget(r1)
            card.add_widget(r2)
            self.items_layout.add_widget(card)


# =============================================================================
# Screen 4: Customers (العملاء والأرصدة)
# =============================================================================
class CustomersScreen(Screen):
    def __init__(self, client: MobileDataClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.init_ui()

    def init_ui(self):
        root = BoxLayout(orientation='vertical')

        header = CardBox(bg_color=C_SURFACE, orientation='horizontal', size_hint_y=None, height=dp(48), padding=dp(8))
        header.add_widget(ArLabel(text="دليل العملاء والأرصدة المستحقة", font_size='15sp', bold=True))
        root.add_widget(header)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.cust_layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10), size_hint_y=None)
        self.cust_layout.bind(minimum_height=self.cust_layout.setter('height'))
        scroll.add_widget(self.cust_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self):
        self.refresh_data()

    def refresh_data(self):
        custs = self.client.get_customers()
        self.cust_layout.clear_widgets()
        if not custs:
            empty = CardBox(bg_color=C_SURFACE, size_hint_y=None, height=dp(60))
            empty.add_widget(ArLabel(text="لا يوجد عملاء مسجلين", color=C_MUTED))
            self.cust_layout.add_widget(empty)
            return

        for c in custs:
            bal = float(c.get("current_balance", 0))
            b_col = C_DANGER if bal > 0 else (C_SUCCESS if bal < 0 else C_MUTED)
            card = CardBox(bg_color=C_SURFACE, border_color=b_col, orientation='vertical', size_hint_y=None, height=dp(75), padding=dp(10), spacing=dp(3))

            r1 = BoxLayout(orientation='horizontal')
            name = c.get("name", "عميل")
            lbl_name = ArLabel(text=name, font_size='14sp', bold=True)
            lbl_bal = ArLabel(text=f"{bal:,.2f} ج.م", font_size='14sp', bold=True, color=b_col)
            r1.add_widget(lbl_name)
            r1.add_widget(lbl_bal)

            r2 = BoxLayout(orientation='horizontal')
            phone = c.get("phone") or "بدون هاتف"
            lbl_phone = ArLabel(text=f"هاتف: {phone}", font_size='11sp', color=C_MUTED)
            state = "مدين (عليه)" if bal > 0 else ("دائن (له)" if bal < 0 else "خالص")
            lbl_st = ArLabel(text=state, font_size='11sp', color=b_col)
            r2.add_widget(lbl_phone)
            r2.add_widget(lbl_st)

            card.add_widget(r1)
            card.add_widget(r2)
            self.cust_layout.add_widget(card)


# =============================================================================
# Screen 5: Settings (إعدادات الربط بالكمبيوتر والواي فاي)
# =============================================================================
class SettingsScreen(Screen):
    def __init__(self, client: MobileDataClient, on_settings_saved_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.on_settings_saved_callback = on_settings_saved_callback
        self.init_ui()

    def init_ui(self):
        root = BoxLayout(orientation='vertical')

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        box = BoxLayout(orientation='vertical', spacing=dp(14), padding=dp(14), size_hint_y=None)
        box.bind(minimum_height=box.setter('height'))

        # Title Card
        h_card = CardBox(bg_color=C_SURFACE, orientation='vertical', size_hint_y=None, height=dp(70), padding=dp(10))
        h_card.add_widget(ArLabel(text="إعدادات المزامنة والربط بالشبكة المحلية", font_size='16sp', bold=True))
        h_card.add_widget(ArLabel(text="ربط تطبيق الأندرويد ببرنامج الكمبيوتر عبر الواي فاي", font_size='11sp', color=C_MUTED))
        box.add_widget(h_card)

        # Server URL Card
        srv_card = CardBox(bg_color=C_SURFACE, orientation='vertical', size_hint_y=None, height=dp(160), padding=dp(12), spacing=dp(8))
        srv_card.add_widget(ArLabel(text="رابط خادم الكمبيوتر (Server URL):", font_size='13sp', bold=True))
        self.url_input = TextInput(text=self.client.server_url, multiline=False, size_hint_y=None, height=dp(40), font_size='14sp')
        srv_card.add_widget(self.url_input)

        srv_help = ArLabel(text="مثال: http://192.168.1.15:8000 (تأكد من كتابة http والبورت 8000)", font_size='11sp', color=C_MUTED)
        srv_card.add_widget(srv_help)

        test_btn = ArButton(text="⚡ فحص الاتصال بالخادم الآن", bg_color=C_PRIMARY, size_hint_y=None, height=dp(40))
        test_btn.bind(on_press=self.test_connection)
        srv_card.add_widget(test_btn)
        box.add_widget(srv_card)

        # Status Label
        self.status_box = CardBox(bg_color=C_CARD, size_hint_y=None, height=dp(50), padding=dp(8))
        self.status_lbl = ArLabel(text="جاهز للفحص والتوصيل", font_size='12sp', color=C_MUTED)
        self.status_box.add_widget(self.status_lbl)
        box.add_widget(self.status_box)

        # Mode Selection Card
        mode_card = CardBox(bg_color=C_SURFACE, orientation='vertical', size_hint_y=None, height=dp(100), padding=dp(10), spacing=dp(6))
        mode_card.add_widget(ArLabel(text="وضع التشغيل:", font_size='13sp', bold=True))
        self.mode_spinner = Spinner(
            text=ar("خادم الواي فاي (مزامنة مباشرة مع الكمبيوتر)"),
            values=[
                ar("خادم الواي فاي (مزامنة مباشرة مع الكمبيوتر)"),
                ar("قاعدة بيانات SQLite محلية (أوفلاين)")
            ],
            font_name=FONT_NAME,
            size_hint_y=None,
            height=dp(40)
        )
        mode_card.add_widget(self.mode_spinner)
        box.add_widget(mode_card)

        # Save Button
        save_btn = ArButton(text="💾 حفظ وتطبيق الإعدادات", bg_color=C_SUCCESS, size_hint_y=None, height=dp(48))
        save_btn.bind(on_press=self.save_settings)
        box.add_widget(save_btn)

        scroll.add_widget(box)
        root.add_widget(scroll)
        self.add_widget(root)

    def test_connection(self, instance):
        url = self.url_input.text.strip().rstrip("/")
        self.client.server_url = url
        res = self.client.test_connection()
        if res.get("success"):
            self.status_lbl.set_arabic_text(f"✅ متصل بنجاح: {res.get('message')}")
            self.status_lbl.color = C_SUCCESS
        else:
            self.status_lbl.set_arabic_text(f"❌ خطأ: {res.get('message')}")
            self.status_lbl.color = C_DANGER

    def save_settings(self, instance):
        url = self.url_input.text.strip().rstrip("/")
        mode = "server" if "خادم" in self.mode_spinner.text else "sqlite"
        self.client.save_config(server_url=url, mode=mode)
        self.status_lbl.set_arabic_text("✅ تم حفظ الإعدادات بنجاح!")
        self.status_lbl.color = C_SUCCESS
        if self.on_settings_saved_callback:
            self.on_settings_saved_callback()


# =============================================================================
# Main Root Widget (Top Bar + ScreenManager + Bottom NavBar)
# =============================================================================
class MobileAppRoot(BoxLayout):
    def __init__(self, client: MobileDataClient, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.client = client
        self.init_ui()

    def init_ui(self):
        # 1. Global App Top Bar
        top_bar = CardBox(bg_color=C_SURFACE, orientation='horizontal', size_hint_y=None, height=dp(52), padding=dp(8), spacing=dp(8))
        
        self.conn_badge = ArLabel(text="📶 جاري الفحص...", font_size='11sp', color=C_MUTED, size_hint_x=0.35)
        top_bar.add_widget(self.conn_badge)
        
        title_lbl = ArLabel(text="البنيان ERP", font_size='16sp', bold=True, size_hint_x=0.45)
        top_bar.add_widget(title_lbl)

        refresh_btn = ArButton(text="🔄", bg_color=C_CARD, size_hint_x=0.20)
        refresh_btn.bind(on_press=self.refresh_current_screen)
        top_bar.add_widget(refresh_btn)

        self.add_widget(top_bar)

        # 2. Screens
        self.sm = ScreenManager()
        self.screen_dashboard = DashboardScreen(self.client, name="dashboard")
        self.screen_journal = JournalScreen(self.client, name="journal")
        self.screen_inventory = InventoryScreen(self.client, name="inventory")
        self.screen_customers = CustomersScreen(self.client, name="customers")
        self.screen_settings = SettingsScreen(self.client, on_settings_saved_callback=self.check_connection_status, name="settings")

        self.sm.add_widget(self.screen_dashboard)
        self.sm.add_widget(self.screen_journal)
        self.sm.add_widget(self.screen_inventory)
        self.sm.add_widget(self.screen_customers)
        self.sm.add_widget(self.screen_settings)

        self.add_widget(self.sm)

        # 3. Bottom Navigation Bar
        nav_bar = CardBox(bg_color=C_SURFACE, orientation='horizontal', size_hint_y=None, height=dp(58), padding=dp(4), spacing=dp(4))
        
        self.nav_btns = {}
        tabs = [
            ("dashboard", "الرئيسية"),
            ("journal", "اليومية"),
            ("inventory", "المخزون"),
            ("customers", "العملاء"),
            ("settings", "الإعدادات")
        ]

        for screen_name, label in tabs:
            btn = ArButton(text=label, bg_color=C_PRIMARY if screen_name == "dashboard" else C_SURFACE)
            btn.bind(on_press=lambda inst, sn=screen_name: self.switch_screen(sn))
            self.nav_btns[screen_name] = btn
            nav_bar.add_widget(btn)

        self.add_widget(nav_bar)

        # Initial connection check
        Clock.schedule_once(lambda dt: self.check_connection_status(), 0.5)

    def switch_screen(self, screen_name: str):
        self.sm.current = screen_name
        for name, btn in self.nav_btns.items():
            btn.background_color = C_PRIMARY if name == screen_name else C_SURFACE

    def refresh_current_screen(self, instance=None):
        curr = self.sm.current_screen
        if hasattr(curr, "refresh_data"):
            curr.refresh_data()
        self.check_connection_status()

    def check_connection_status(self):
        res = self.client.test_connection()
        if res.get("success"):
            self.conn_badge.set_arabic_text("🟢 متصل بالكمبيوتر")
            self.conn_badge.color = C_SUCCESS
        else:
            self.conn_badge.set_arabic_text("⚪ وضع أوفلاين")
            self.conn_badge.color = C_MUTED
