# -*- coding: utf-8 -*-
"""
Database Manager and Schema for Iron & Cement ERP (SQLite)
Pure Live-Transaction Accounting Logic (No Opening Balance / بدون رصيد افتتاحي):
- Daily Transactions & Journal: Cash-In (وارد / قبض), Cash-Out (صادر / صرف), or Credit Transaction.
- Customers & Suppliers Balance Formula:
  الرصيد الحالي = إجمالي المشتريات/التوريدات - إجمالي المدفوعات المسددة
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from config import DB_PATH


class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()
        self.seed_if_empty()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=20.0)
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            c = conn.cursor()

            # 1. Settings Table
            c.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # 2. Warehouses Table
            c.execute("""
                CREATE TABLE IF NOT EXISTS warehouses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    location TEXT DEFAULT '',
                    manager TEXT DEFAULT '',
                    capacity_tons REAL DEFAULT 1000.0,
                    notes TEXT DEFAULT ''
                )
            """)

            # 3. Inventory Items Table
            c.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    warehouse_id INTEGER NOT NULL,
                    unit TEXT NOT NULL DEFAULT 'طن (Ton)',
                    quantity REAL NOT NULL DEFAULT 0.0,
                    weight_per_unit_kg REAL NOT NULL DEFAULT 1000.0,
                    min_stock REAL NOT NULL DEFAULT 10.0,
                    purchase_price REAL NOT NULL DEFAULT 0.0,
                    sale_price REAL NOT NULL DEFAULT 0.0,
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE RESTRICT
                )
            """)

            # 4. Stock Movements Table
            c.execute("""
                CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    movement_date TEXT NOT NULL,
                    item_id INTEGER NOT NULL,
                    warehouse_id INTEGER NOT NULL,
                    movement_type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price REAL NOT NULL DEFAULT 0.0,
                    total_value REAL NOT NULL DEFAULT 0.0,
                    reference_party TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
                    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE
                )
            """)

            # 5. Customers Table (No opening_balance column)
            c.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    name TEXT NOT NULL,
                    phone TEXT DEFAULT '',
                    address TEXT DEFAULT '',
                    pricing_tier TEXT DEFAULT 'تجزئة / مستهلك (Retail)',
                    tax_number TEXT DEFAULT '',
                    credit_limit REAL NOT NULL DEFAULT 500000.0,
                    notes TEXT DEFAULT ''
                )
            """)

            # 6. Customer Custom Prices Table
            c.execute("""
                CREATE TABLE IF NOT EXISTS customer_custom_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    custom_price REAL NOT NULL,
                    discount_per_ton REAL DEFAULT 0.0,
                    updated_at TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    UNIQUE(customer_id, item_id),
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
                )
            """)

            # 7. Customer Transactions
            # debit column stores: المشتريات / المسحوبات (+)
            # credit column stores: المدفوعات المسددة (-)
            c.execute("""
                CREATE TABLE IF NOT EXISTS customer_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    tx_date TEXT NOT NULL,
                    tx_type TEXT NOT NULL,
                    reference_no TEXT DEFAULT '',
                    description TEXT NOT NULL,
                    debit REAL NOT NULL DEFAULT 0.0,  -- المشتريات / التوريدات (+)
                    credit REAL NOT NULL DEFAULT 0.0, -- المدفوعات المسددة (-)
                    payment_method TEXT DEFAULT 'آجل / على الحساب (Credit)',
                    due_date TEXT DEFAULT '',
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
                )
            """)

            # 8. Suppliers Table (No opening_balance column)
            c.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    name TEXT NOT NULL,
                    factory_type TEXT DEFAULT 'مصنع حديد تسليح',
                    phone TEXT DEFAULT '',
                    address TEXT DEFAULT '',
                    tax_number TEXT DEFAULT '',
                    notes TEXT DEFAULT ''
                )
            """)

            # 9. Supplier Transactions
            # credit column stores: المشتريات / التوريدات المستلمة (+)
            # debit column stores: المدفوعات المسددة للمورد (-)
            c.execute("""
                CREATE TABLE IF NOT EXISTS supplier_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id INTEGER NOT NULL,
                    tx_date TEXT NOT NULL,
                    tx_type TEXT NOT NULL,
                    reference_no TEXT DEFAULT '',
                    description TEXT NOT NULL,
                    debit REAL NOT NULL DEFAULT 0.0,  -- المدفوعات المسددة للمورد (-)
                    credit REAL NOT NULL DEFAULT 0.0, -- المشتريات / التوريدات المستلمة (+)
                    payment_method TEXT DEFAULT 'آجل / على الحساب (Credit)',
                    due_date TEXT DEFAULT '',
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
                )
            """)

            # 10. Simplified Daily Transactions / Cash-In & Cash-Out Log
            c.execute("""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_no TEXT NOT NULL,
                    entry_date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    debit_account TEXT NOT NULL,  -- نوع الحركة: وارد (قبض) / صادر (صرف) / معاملة آجلة
                    credit_account TEXT NOT NULL, -- الخزينة أو الحساب
                    description TEXT NOT NULL,
                    debit_amount REAL NOT NULL DEFAULT 0.0,  -- مبلغ الوارد / المقبوضات (Cash In)
                    credit_amount REAL NOT NULL DEFAULT 0.0, -- مبلغ الصادر / المصروفات (Cash Out)
                    payment_method TEXT DEFAULT 'نقدي بالخزينة (Cash)',
                    party_name TEXT DEFAULT '',
                    notes TEXT DEFAULT ''
                )
            """)

            # 11. Employees Table
            c.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    department TEXT DEFAULT 'الإدارة والمحاسبة',
                    phone TEXT DEFAULT '',
                    national_id TEXT DEFAULT '',
                    hire_date TEXT NOT NULL,
                    base_salary REAL NOT NULL DEFAULT 0.0,
                    housing_allowance REAL NOT NULL DEFAULT 0.0,
                    status TEXT DEFAULT 'نشط'
                )
            """)

            # 12. Payroll Records Table
            c.execute("""
                CREATE TABLE IF NOT EXISTS payroll_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    month_year TEXT NOT NULL,
                    payment_date TEXT NOT NULL,
                    base_salary REAL NOT NULL DEFAULT 0.0,
                    bonuses REAL NOT NULL DEFAULT 0.0,
                    deductions REAL NOT NULL DEFAULT 0.0,
                    advances REAL NOT NULL DEFAULT 0.0,
                    net_salary REAL NOT NULL DEFAULT 0.0,
                    status TEXT DEFAULT 'تم الصرف',
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            self._migrate_remove_opening_balance_if_needed(conn)
            self._migrate_existing_journal_if_needed(conn)

    def _migrate_remove_opening_balance_if_needed(self, conn: sqlite3.Connection):
        """Drop opening_balance column from existing customers and suppliers tables if present."""
        cust_cols = [r["name"] for r in conn.execute("PRAGMA table_info(customers)").fetchall()]
        if "opening_balance" in cust_cols:
            try:
                conn.execute("ALTER TABLE customers DROP COLUMN opening_balance")
                conn.commit()
            except sqlite3.OperationalError:
                pass

        sup_cols = [r["name"] for r in conn.execute("PRAGMA table_info(suppliers)").fetchall()]
        if "opening_balance" in sup_cols:
            try:
                conn.execute("ALTER TABLE suppliers DROP COLUMN opening_balance")
                conn.commit()
            except sqlite3.OperationalError:
                pass

    def _migrate_existing_journal_if_needed(self, conn: sqlite3.Connection):
        """Ensure any older double-entry rows are converted cleanly into simplified Cash-In / Cash-Out records."""
        rows = conn.execute("SELECT * FROM journal_entries").fetchall()
        for r in rows:
            flow = r["debit_account"] or ""
            if flow not in (
                "وارد / قبض (إيراد أو تحصيل نقدية)",
                "صادر / صرف (مصروف أو سداد دفعة)",
                "معاملة آجلة (بيع أو شراء على الحساب)"
            ):
                cat = r["category"] or ""
                amt = max(float(r["debit_amount"] or 0), float(r["credit_amount"] or 0))
                if "تحصيل" in cat or ("مبيعات" in cat and "آجل" not in (r["payment_method"] or "")):
                    new_flow = "وارد / قبض (إيراد أو تحصيل نقدية)"
                    cash_in, cash_out = amt, 0.0
                elif "سداد" in cat or "مصروف" in cat or "رواتب" in cat or ("مشتريات" in cat and "آجل" not in (r["payment_method"] or "")):
                    new_flow = "صادر / صرف (مصروف أو سداد دفعة)"
                    cash_in, cash_out = 0.0, amt
                elif "مبيعات" in cat:
                    new_flow = "وارد / قبض (إيراد أو تحصيل نقدية)"
                    cash_in, cash_out = amt, 0.0
                else:
                    new_flow = "صادر / صرف (مصروف أو سداد دفعة)"
                    cash_in, cash_out = 0.0, amt

                conn.execute("""
                    UPDATE journal_entries
                    SET debit_account = ?, debit_amount = ?, credit_amount = ?
                    WHERE id = ?
                """, (new_flow, cash_in, cash_out, r["id"]))
        conn.commit()

    def seed_if_empty(self):
        """Seed rich, realistic Egyptian Iron & Cement trading company data on first run."""
        with self.get_connection() as conn:
            c = conn.cursor()
            count = c.execute("SELECT COUNT(*) as cnt FROM warehouses").fetchone()["cnt"]
            if count > 0:
                return

            default_settings = [
                ("company_name", "شركة البنيان لتجارة وتوزيع الحديد والأسمنت"),
                ("company_address", "القاهرة - مدينة نصر - المنطقة الصناعية"),
                ("company_phone", "01001234567"),
                ("manager_whatsapp", "201001234567"),
                ("theme", "dark"),
                ("font_scale", "100"),
                ("gemini_api_key", "")
            ]
            c.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", default_settings)

            warehouses = [
                ("مخزن العاشر من رمضان الرئيسي (حديد)", "المنطقة الصناعية الثالثة - العاشر", "م. محمود عبد السلام", 5000.0, "مخزن رئيسي لحديد التسليح والقطاعات"),
                ("مخزن القطامية المركزي (أسمنت)", "طريق العين السخنة - القطامية", "أ. سعيد الجوهري", 3500.0, "مخزن مخصص للأسمنت البورتلاندي والمقاوم"),
                ("مخزن فرع الجيزة وأكتوبر", "المنطقة الصناعية - 6 أكتوبر", "أ. كريم عادل", 2000.0, "مخزن التوزيع السريع لمشاريع غرب القاهرة")
            ]
            c.executemany("""
                INSERT INTO warehouses (name, location, manager, capacity_tons, notes)
                VALUES (?, ?, ?, ?, ?)
            """, warehouses)

            items = [
                ("IRN-EZZ-16", "حديد عز تسليح 16 مم (أطوال)", "حديد تسليح (Rebar)", 1, "طن (Ton)", 145.5, 1000.0, 25.0, 39800.0, 41200.0, "مطابق للمواصفات القياسية المصرية"),
                ("IRN-EZZ-12", "حديد عز تسليح 12 مم (أطوال)", "حديد تسليح (Rebar)", 1, "طن (Ton)", 92.0, 1000.0, 20.0, 40000.0, 41500.0, "الأكثر طلباً للأعمدة والأسقف"),
                ("IRN-BSH-16", "حديد بشاي تسليح 16 مم", "حديد تسليح (Rebar)", 1, "طن (Ton)", 64.0, 1000.0, 15.0, 39200.0, 40600.0, "توريد مصنع بشاي للصلب"),
                ("IRN-SWI-10", "حديد السويس للصلب 10 مم (لفائف)", "حديد تسليح (Rebar)", 3, "طن (Ton)", 11.5, 1000.0, 15.0, 38900.0, 40300.0, "رصيد منخفض - يحتاج طلب توريد"),
                ("IRN-MRK-14", "حديد المراكبي تسليح 14 مم", "حديد تسليح (Rebar)", 3, "طن (Ton)", 48.0, 1000.0, 15.0, 38600.0, 40000.0, "متوفر بمخزن أكتوبر"),
                ("CEM-SWD-OPC", "أسمنت السويدي بورتلاندي عادي (رتبة 42.5)", "أسمنت بورتلاندي عادي (OPC)", 2, "طن (Ton)", 210.0, 1000.0, 40.0, 2680.0, 2850.0, "الطن = 20 شيكارة (50 كجم)"),
                ("CEM-SWD-SRC", "أسمنت السويدي مقاوم للملوحة (سي ووتر)", "أسمنت مقاوم للملوحة (SRC)", 2, "طن (Ton)", 85.0, 1000.0, 25.0, 2820.0, 3020.0, "مخصص للأساسات والقواعد"),
                ("CEM-ARSH-OPC", "أسمنت العريش (العسكري) بورتلاندي 42.5", "أسمنت بورتلاندي عادي (OPC)", 2, "طن (Ton)", 160.0, 1000.0, 30.0, 2550.0, 2720.0, "سعر تنافسي للمقاولين"),
                ("CEM-hlwn-BAG", "أسمنت حلوان بورتلاندي (بالشيكارة 50 كجم)", "أسمنت بورتلاندي عادي (OPC)", 3, "شيكارة 50 كجم (Bag)", 120.0, 50.0, 200.0, 132.0, 145.0, "بيع تجزئة بالشيكارة - رصيد منخفض"),
                ("CEM-SIN-WHT", "أسمنت سيناء الأبيض سوبر سيناء", "أسمنت أبيض وتشطيبات (White Cement)", 2, "طن (Ton)", 18.0, 1000.0, 10.0, 3950.0, 4250.0, "لأعمال الواجهات والتشطيبات")
            ]
            c.executemany("""
                INSERT INTO items (code, name, category, warehouse_id, unit, quantity, weight_per_unit_kg, min_stock, purchase_price, sale_price, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, items)

            today = datetime.now().strftime("%Y-%m-%d")
            d_minus_5 = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            d_minus_3 = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            d_minus_1 = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            movements = [
                (d_minus_5, 1, 1, "وارد (شراء/إضافة)", 100.0, 39800.0, 3980000.0, "مجموعة حديد عز", "توريد تريلا رقم 4521"),
                (d_minus_5, 6, 2, "وارد (شراء/إضافة)", 150.0, 2680.0, 402000.0, "شركة السويدي للأسمنت", "توريد دفعة أسمنت عادي"),
                (d_minus_3, 1, 1, "صادر (بيع/صرف)", 25.0, 40900.0, 1022500.0, "شركة المقاولون المتحدون للإنشاءات", "فاتورة مبيعات INV-1001"),
                (d_minus_1, 6, 2, "صادر (بيع/صرف)", 40.0, 2800.0, 112000.0, "مكتب المهندس طارق علام للمقاولات", "فاتورة مبيعات INV-1002"),
            ]
            c.executemany("""
                INSERT INTO stock_movements (movement_date, item_id, warehouse_id, movement_type, quantity, unit_price, total_value, reference_party, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, movements)

            customers = [
                ("CUST-001", "شركة المقاولون المتحدون للإنشاءات", "201011223344", "التجمع الخامس - القاهرة الجديدة", "مشاريع خاصة (VIP Projects)", "412-889-102", 3000000.0, "عميل استراتيجي - سداد شيكات وتحويلات بنكية"),
                ("CUST-002", "مكتب المهندس طارق علام للمقاولات", "201122334455", "المهندسين - الجيزة", "نصف جملة / مقاول (Contractor)", "319-554-881", 1000000.0, "مشاريع سكنية بمنطقة حدائق أكتوبر"),
                ("CUST-003", "معرض النور لتجارة مواد البناء (الحاج عبد الرحمن)", "201233445566", "شبرا الخيمة - القليوبية", "جملة / تاجر معتمد (Wholesale)", "298-112-409", 800000.0, "تاجر جملة - مسحوبات أسبوعية منتظمة"),
                ("CUST-004", "شركة الصفوة للتطوير العقاري", "201099887766", "الشيخ زايد - الحي الثامن", "مشاريع خاصة (VIP Projects)", "588-320-119", 2500000.0, "مشروع كمبوند الصفوة بارك")
            ]
            c.executemany("""
                INSERT INTO customers (code, name, phone, address, pricing_tier, tax_number, credit_limit, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, customers)

            custom_prices = [
                (1, 1, 40850.0, 350.0, today, "سعر خاص لمشروع التجمع الخامس (خصم 350 ج.م بالطن)"),
                (1, 2, 41100.0, 400.0, today, "سعر توريد خاص لحديد عز 12 مم"),
                (1, 6, 2790.0, 60.0, today, "سعر عقد سنوي لأسمنت السويدي"),
                (2, 1, 41000.0, 200.0, today, "سعر مقاول معتمد"),
                (2, 6, 2810.0, 40.0, today, "خصم مقاول 40 ج.م للطن"),
                (3, 8, 2670.0, 50.0, today, "سعر تاجر جملة لأسمنت العريش")
            ]
            c.executemany("""
                INSERT INTO customer_custom_prices (customer_id, item_id, custom_price, discount_per_ton, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, custom_prices)

            cust_txs = [
                (1, d_minus_5, "فاتورة مبيعات / توريد", "INV-1001", "توريد 25 طن حديد عز 16 مم لموقع التجمع", 1021250.0, 0.0, "آجل / على الحساب (Credit)", today),
                (1, d_minus_3, "دفعة مسددة من العميل", "REC-501", "تحصيل دفعة تحت الحساب - تحويل بنكي CIB", 0.0, 800000.0, "تحويل بنكي (Bank Transfer)", ""),
                (1, d_minus_1, "فاتورة مبيعات / توريد", "INV-1004", "توريد 50 طن أسمنت السويدي مقاوم للملوحة", 151000.0, 0.0, "آجل / على الحساب (Credit)", today),
                (2, d_minus_3, "فاتورة مبيعات / توريد", "INV-1002", "توريد 40 طن أسمنت السويدي بورتلاندي عادي", 112400.0, 0.0, "آجل / على الحساب (Credit)", today),
                (2, d_minus_1, "دفعة مسددة من العميل", "REC-502", "تحصيل نقدي وإنستاباي من م. طارق علام", 0.0, 95000.0, "إنستاباي (InstaPay)", ""),
                (3, d_minus_5, "فاتورة مبيعات / توريد", "INV-1003", "توريد 10 طن حديد بشاي 16 مم", 406000.0, 0.0, "آجل / على الحساب (Credit)", today),
                (3, d_minus_1, "دفعة مسددة من العميل", "REC-503", "سداد نقدي بالخزينة من معرض النور", 0.0, 250000.0, "نقدي بالخزينة (Cash)", "")
            ]
            c.executemany("""
                INSERT INTO customer_transactions (customer_id, tx_date, tx_type, reference_no, description, debit, credit, payment_method, due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, cust_txs)

            suppliers = [
                ("SUP-001", "مجموعة حديد عز (Ezz Steel)", "مصنع حديد تسليح", "201005556677", "الدخيلة - الإسكندرية / السادات", "100-200-300", "الوكيل الأول - تسوية الحوافز ربع سنوية"),
                ("SUP-002", "شركة السويدي للأسمنت (El Sewedy Cement)", "مصنع أسمنت", "201008889900", "العين السخنة - السويس", "200-300-400", "توريد أسمنت بورتلاندي ومقاوم"),
                ("SUP-003", "مصنع حديد بشاي للصلب", "مصنع حديد تسليح", "201224445566", "مدينة السادات - المنوفية", "300-400-500", "عقود توريد شهرية"),
                ("SUP-004", "شركة أسمنت العريش (الوطنية للأسمنت)", "مصنع أسمنت", "201113334455", "القاهرة - مدينة نصر", "400-500-600", "توريد مباشر للمخازن")
            ]
            c.executemany("""
                INSERT INTO suppliers (code, name, factory_type, phone, address, tax_number, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, suppliers)

            d_minus_75 = (datetime.now() - timedelta(days=75)).strftime("%Y-%m-%d")
            d_minus_45 = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
            d_minus_15 = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")

            sup_txs = [
                (1, d_minus_75, "مشتريات / توريد بضاعة", "PUR-801", "توريد 100 طن حديد عز 16 مم و 12 مم", 0.0, 3980000.0, "آجل / على الحساب (Credit)", d_minus_45),
                (1, d_minus_45, "سداد دفعة للمورد", "PAY-301", "تحويل بنكي لحساب حديد عز - البنك الأهلي", 3200000.0, 0.0, "تحويل بنكي (Bank Transfer)", ""),
                (2, d_minus_45, "مشتريات / توريد بضاعة", "PUR-802", "توريد 150 طن أسمنت السويدي بورتلاندي", 0.0, 402000.0, "آجل / على الحساب (Credit)", d_minus_15),
                (2, d_minus_15, "سداد دفعة للمورد", "PAY-302", "سداد شيك بنكي لشركة السويدي للأسمنت", 250000.0, 0.0, "شيك بنكي (Cheque)", ""),
                (3, d_minus_15, "مشتريات / توريد بضاعة", "PUR-803", "توريد 30 طن حديد بشاي 16 مم", 0.0, 1176000.0, "آجل / على الحساب (Credit)", today),
                (3, d_minus_3, "سداد دفعة للمورد", "PAY-303", "تحويل بنكي لمصنع حديد بشاي", 900000.0, 0.0, "تحويل بنكي (Bank Transfer)", "")
            ]
            c.executemany("""
                INSERT INTO supplier_transactions (supplier_id, tx_date, tx_type, reference_no, description, debit, credit, payment_method, due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, sup_txs)

            # Simplified Cash-In / Cash-Out Daily Transactions
            journal = [
                ("TRX-2026-001", d_minus_5, "مبيعات حديد وأسمنت", "وارد / قبض (إيراد أو تحصيل نقدية)", "الخزينة الرئيسية", "مبيعات نقدية لعدد 10 طن حديد عز 12 مم", 415000.0, 0.0, "نقدي بالخزينة (Cash)", "عميل نقدي بالمعرض", "فاتورة نقدية"),
                ("TRX-2026-002", d_minus_3, "تحصيل دفعة من عميل", "وارد / قبض (إيراد أو تحصيل نقدية)", "الحساب البنكي CIB", "تحصيل دفعة من حساب شركة المقاولون المتحدون", 800000.0, 0.0, "تحويل بنكي (Bank Transfer)", "شركة المقاولون المتحدون للإنشاءات", "إيصال REC-501"),
                ("TRX-2026-003", d_minus_3, "تحصيل دفعة من عميل", "وارد / قبض (إيراد أو تحصيل نقدية)", "إنستاباي InstaPay", "تحصيل دفعة من مكتب المهندس طارق علام", 95000.0, 0.0, "إنستاباي (InstaPay)", "مكتب المهندس طارق علام للمقاولات", "إيصال REC-502"),
                ("TRX-2026-004", d_minus_1, "تحصيل دفعة من عميل", "وارد / قبض (إيراد أو تحصيل نقدية)", "الخزينة الرئيسية", "سداد نقدي من معرض النور لتجارة مواد البناء", 250000.0, 0.0, "نقدي بالخزينة (Cash)", "معرض النور لتجارة مواد البناء", "إيصال REC-503"),
                ("TRX-2026-005", d_minus_1, "مصروفات تشغيل ونولون شحن", "صادر / صرف (مصروف أو سداد دفعة)", "الخزينة الرئيسية", "سداد نولون نقل تريلات الحديد والأسمنت وأوناش التعتيق", 0.0, 18500.0, "نقدي بالخزينة (Cash)", "مكتب الكابتن للنقل الثقيل", "3 تريلات"),
                ("TRX-2026-006", today, "سداد دفعة لمورد / مصنع", "صادر / صرف (مصروف أو سداد دفعة)", "البنك الأهلي المصري", "سداد دفعة للمورد مصنع حديد بشاي للصلب", 0.0, 900000.0, "تحويل بنكي (Bank Transfer)", "مصنع حديد بشاي للصلب", "إيصال PAY-303")
            ]
            c.executemany("""
                INSERT INTO journal_entries (entry_no, entry_date, category, debit_account, credit_account, description, debit_amount, credit_amount, payment_method, party_name, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, journal)

            employees = [
                ("EMP-001", "أحمد محمد الشناوي", "مدير الحسابات العام (General Accountant)", "الإدارة المالية والمحاسبة", "201012349876", "29005120101234", "2022-01-15", 18500.0, 2000.0, "نشط"),
                ("EMP-002", "محمود عبد السلام حسن", "أمين مخزن العاشر الرئيسي", "إدارة المخازن والأوناش", "201123456789", "28809101302345", "2022-06-01", 11000.0, 1500.0, "نشط"),
                ("EMP-003", "سعيد الجوهري إبراهيم", "أمين مخزن القطامية (الأسمنت)", "إدارة المخازن والأوناش", "201234567890", "29103040104567", "2023-02-10", 10500.0, 1200.0, "نشط"),
                ("EMP-004", "كريم عادل مصطفى", "مسؤول مبيعات كبار العملاء والمقاولين", "المبيعات وكبار العملاء", "201098765432", "29411200106789", "2023-08-01", 12000.0, 1500.0, "نشط"),
                ("EMP-005", "حسن فتحي عبد الجواد", "سائق تريلا نقل ثقيل (نقل الحديد)", "النقل الثقيل والتريلات", "201187654321", "28507011408912", "2021-11-01", 13500.0, 1000.0, "نشط")
            ]
            c.executemany("""
                INSERT INTO employees (code, name, role, department, phone, national_id, hire_date, base_salary, housing_allowance, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, employees)

            curr_month = datetime.now().strftime("%Y-%m")
            payrolls = [
                (1, curr_month, today, 20500.0, 2500.0, 0.0, 1000.0, 22000.0, "تم الصرف", "شامل بدل السكن ومكافأة إقفال الربع"),
                (2, curr_month, today, 12500.0, 1000.0, 250.0, 500.0, 12750.0, "تم الصرف", "صرف راتب شهر أكتوبر"),
                (3, curr_month, today, 11700.0, 800.0, 0.0, 0.0, 12500.0, "تم الصرف", "صرف راتب شهر أكتوبر"),
                (4, curr_month, today, 13500.0, 3200.0, 0.0, 1500.0, 15200.0, "تم الصرف", "شامل عمولة مبيعات الحديد"),
                (5, curr_month, today, 14500.0, 1800.0, 300.0, 1000.0, 15000.0, "تم الصرف", "شامل حافز نقل التريلات")
            ]
            c.executemany("""
                INSERT INTO payroll_records (employee_id, month_year, payment_date, base_salary, bonuses, deductions, advances, net_salary, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, payrolls)

            conn.commit()

    # ==========================================================================
    # Settings & Backup/Restore Methods
    # ==========================================================================
    def get_setting(self, key: str, default: str = "") -> str:
        with self.get_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row and row["value"] is not None else default

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()

    def backup_database(self, dest_path: str):
        """Create an atomic, WAL-safe backup of the live SQLite database to dest_path."""
        import os
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        with sqlite3.connect(self.db_path, timeout=20.0) as src_conn:
            with sqlite3.connect(dest_path) as dst_conn:
                src_conn.backup(dst_conn)

    def restore_database(self, src_path: str):
        """Restore the live SQLite database from src_path after verifying SQLite integrity."""
        import os
        if not os.path.exists(src_path):
            raise FileNotFoundError("ملف النسخة الاحتياطية غير موجود.")
        with sqlite3.connect(src_path) as check_conn:
            tables = [
                r[0] for r in check_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            if "settings" not in tables and "warehouses" not in tables:
                raise ValueError("الملف المختار ليس قاعدة بيانات صالحة لنظام البنيان المحاسبي.")

        with sqlite3.connect(src_path) as src_conn:
            with sqlite3.connect(self.db_path, timeout=20.0) as dst_conn:
                src_conn.backup(dst_conn)
        self.init_db()


    # ==========================================================================
    # Dashboard KPIs Summary (Pure Live-Transaction Balances)
    # ==========================================================================
    def get_dashboard_summary(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            c = conn.cursor()
            j_totals = c.execute("""
                SELECT COALESCE(SUM(debit_amount), 0) as total_cash_in,
                       COALESCE(SUM(credit_amount), 0) as total_cash_out
                FROM journal_entries
            """).fetchone()

            expenses_total = c.execute("""
                SELECT COALESCE(SUM(credit_amount), 0) as val FROM journal_entries
                WHERE category LIKE '%مصروف%' OR category LIKE '%رواتب%'
            """).fetchone()["val"]

            inv_stats = c.execute("""
                SELECT COUNT(*) as item_count,
                       COALESCE(SUM(quantity * purchase_price), 0) as cost_valuation,
                       COALESCE(SUM(quantity * sale_price), 0) as market_valuation,
                       SUM(CASE WHEN quantity <= min_stock THEN 1 ELSE 0 END) as low_stock_count
                FROM items
            """).fetchone()

            cust_rows = self.get_all_customers_with_balances()
            total_receivables = sum(r["current_balance"] for r in cust_rows if r["current_balance"] > 0)
            total_cust_purchases = sum(r["total_debit"] for r in cust_rows)

            sup_rows = self.get_all_suppliers_with_balances()
            total_payables = sum(r["current_balance"] for r in sup_rows if r["current_balance"] > 0)
            total_sup_purchases = sum(r["total_credit"] for r in sup_rows)

            return {
                "total_cash_in": j_totals["total_cash_in"],
                "total_cash_out": j_totals["total_cash_out"],
                "net_cash": j_totals["total_cash_in"] - j_totals["total_cash_out"],
                "sales_total": total_cust_purchases + j_totals["total_cash_in"],
                "purchases_total": total_sup_purchases,
                "expenses_total": expenses_total,
                "item_count": inv_stats["item_count"] or 0,
                "cost_valuation": inv_stats["cost_valuation"] or 0.0,
                "market_valuation": inv_stats["market_valuation"] or 0.0,
                "low_stock_count": inv_stats["low_stock_count"] or 0,
                "total_receivables": total_receivables,
                "total_payables": total_payables
            }

    # ==========================================================================
    # Module 1: Simplified Daily Transactions & Cash-In / Cash-Out Log
    # ==========================================================================
    def get_journal_entries(self, search: str = "", category: str = "", flow_filter: str = "") -> List[Dict[str, Any]]:
        query = "SELECT * FROM journal_entries WHERE 1=1"
        params = []
        if category and not category.startswith("كل") and category != "الكل" and category.lower() != "all":
            query += " AND category = ?"
            params.append(category)
        if flow_filter and not flow_filter.startswith("كل") and flow_filter != "الكل" and flow_filter.lower() != "all":
            query += " AND debit_account = ?"
            params.append(flow_filter)
        if search:
            query += " AND (entry_no LIKE ? OR description LIKE ? OR party_name LIKE ? OR notes LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s])
        query += " ORDER BY entry_date DESC, id DESC"
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def add_journal_entry(self, data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO journal_entries (
                    entry_no, entry_date, category, debit_account, credit_account,
                    description, debit_amount, credit_amount, payment_method, party_name, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["entry_no"],
                data["entry_date"],
                data["category"],
                data.get("flow_type", data.get("debit_account", "وارد / قبض (إيراد أو تحصيل نقدية)")),
                data.get("safe_name", data.get("credit_account", "الخزينة الرئيسية")),
                data["description"],
                float(data.get("cash_in", data.get("debit_amount", 0.0))),
                float(data.get("cash_out", data.get("credit_amount", 0.0))),
                data.get("payment_method", ""),
                data.get("party_name", ""),
                data.get("notes", "")
            ))
            conn.commit()
            return cur.lastrowid

    def update_journal_entry(self, entry_id: int, data: Dict[str, Any]):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE journal_entries SET
                    entry_no = ?, entry_date = ?, category = ?,
                    debit_account = ?, credit_account = ?, description = ?,
                    debit_amount = ?, credit_amount = ?, payment_method = ?,
                    party_name = ?, notes = ?
                WHERE id = ?
            """, (
                data["entry_no"],
                data["entry_date"],
                data["category"],
                data.get("flow_type", data.get("debit_account", "وارد / قبض (إيراد أو تحصيل نقدية)")),
                data.get("safe_name", data.get("credit_account", "الخزينة الرئيسية")),
                data["description"],
                float(data.get("cash_in", data.get("debit_amount", 0.0))),
                float(data.get("cash_out", data.get("credit_amount", 0.0))),
                data.get("payment_method", ""),
                data.get("party_name", ""),
                data.get("notes", ""),
                entry_id
            ))
            conn.commit()

    def delete_journal_entry(self, entry_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
            conn.commit()

    def get_next_journal_no(self) -> str:
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM journal_entries").fetchone()
            nxt = (row["cnt"] or 0) + 1
            return f"TRX-{datetime.now().strftime('%Y')}-{nxt:03d}"

    # ==========================================================================
    # Module 2: Warehouses & Inventory Management
    # ==========================================================================
    def get_warehouses(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return conn.execute("""
                SELECT w.*,
                       COUNT(i.id) as items_count,
                       COALESCE(SUM(i.quantity * i.purchase_price), 0) as total_cost_value
                FROM warehouses w
                LEFT JOIN items i ON i.warehouse_id = w.id
                GROUP BY w.id
                ORDER BY w.id ASC
            """).fetchall()

    def add_warehouse(self, name: str, location: str, manager: str, capacity_tons: float, notes: str = ""):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO warehouses (name, location, manager, capacity_tons, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (name, location, manager, float(capacity_tons), notes))
            conn.commit()

    def update_warehouse(self, wh_id: int, name: str, location: str, manager: str, capacity_tons: float, notes: str = ""):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE warehouses SET name=?, location=?, manager=?, capacity_tons=?, notes=?
                WHERE id=?
            """, (name, location, manager, float(capacity_tons), notes, wh_id))
            conn.commit()

    def delete_warehouse(self, wh_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM warehouses WHERE id=?", (wh_id,))
            conn.commit()

    def get_items(self, warehouse_id: Optional[int] = None, category: str = "", search: str = "", low_stock_only: bool = False) -> List[Dict[str, Any]]:
        query = """
            SELECT i.*, w.name as warehouse_name,
                   (i.quantity * i.purchase_price) as total_cost,
                   (i.quantity * i.sale_price) as total_sale_value,
                   ((i.quantity * i.weight_per_unit_kg) / 1000.0) as total_weight_tons
            FROM items i
            JOIN warehouses w ON i.warehouse_id = w.id
            WHERE 1=1
        """
        params = []
        if warehouse_id:
            query += " AND i.warehouse_id = ?"
            params.append(warehouse_id)
        if category and not category.startswith("كل") and category != "الكل" and category.lower() != "all":
            query += " AND i.category = ?"
            params.append(category)
        if search:
            query += " AND (i.code LIKE ? OR i.name LIKE ? OR i.notes LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])
        if low_stock_only:
            query += " AND i.quantity <= i.min_stock"
        query += " ORDER BY i.id ASC"
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def add_item(self, data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO items (
                    code, name, category, warehouse_id, unit, quantity,
                    weight_per_unit_kg, min_stock, purchase_price, sale_price, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["code"], data["name"], data["category"], int(data["warehouse_id"]),
                data["unit"], float(data["quantity"]), float(data.get("weight_per_unit_kg", 1000.0)),
                float(data["min_stock"]), float(data["purchase_price"]), float(data["sale_price"]),
                data.get("notes", "")
            ))
            conn.commit()
            return cur.lastrowid

    def update_item(self, item_id: int, data: Dict[str, Any]):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE items SET
                    code=?, name=?, category=?, warehouse_id=?, unit=?,
                    quantity=?, weight_per_unit_kg=?, min_stock=?,
                    purchase_price=?, sale_price=?, notes=?
                WHERE id=?
            """, (
                data["code"], data["name"], data["category"], int(data["warehouse_id"]),
                data["unit"], float(data["quantity"]), float(data.get("weight_per_unit_kg", 1000.0)),
                float(data["min_stock"]), float(data["purchase_price"]), float(data["sale_price"]),
                data.get("notes", ""), item_id
            ))
            conn.commit()

    def delete_item(self, item_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM items WHERE id=?", (item_id,))
            conn.commit()

    def record_stock_movement(self, data: Dict[str, Any]):
        with self.get_connection() as conn:
            c = conn.cursor()
            item = c.execute("SELECT * FROM items WHERE id=?", (int(data["item_id"]),)).fetchone()
            if not item:
                raise ValueError("الصنف غير موجود")

            qty = float(data["quantity"])
            m_type = data["movement_type"]
            new_qty = item["quantity"]
            if "وارد" in m_type or "شراء" in m_type or "إضافة" in m_type:
                new_qty += qty
            elif "صادر" in m_type or "بيع" in m_type or "صرف" in m_type:
                if item["quantity"] < qty:
                    raise ValueError(f"الرصيد المتاح ({item['quantity']} {item['unit']}) لا يكفي لصرف ({qty})")
                new_qty -= qty
            else:
                new_qty = qty

            unit_price = float(data.get("unit_price", item["purchase_price"]))
            total_val = qty * unit_price

            c.execute("UPDATE items SET quantity=? WHERE id=?", (new_qty, item["id"]))
            c.execute("""
                INSERT INTO stock_movements (
                    movement_date, item_id, warehouse_id, movement_type,
                    quantity, unit_price, total_value, reference_party, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["movement_date"], item["id"], item["warehouse_id"], m_type,
                qty, unit_price, total_val, data.get("reference_party", ""), data.get("notes", "")
            ))
            conn.commit()

    def get_stock_movements(self, item_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT m.*, i.code as item_code, i.name as item_name, i.unit as item_unit, w.name as warehouse_name
            FROM stock_movements m
            JOIN items i ON m.item_id = i.id
            JOIN warehouses w ON m.warehouse_id = w.id
            WHERE 1=1
        """
        params = []
        if item_id:
            query += " AND m.item_id = ?"
            params.append(item_id)
        query += " ORDER BY m.movement_date DESC, m.id DESC"
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    # ==========================================================================
    # Module 3: Customers & Custom Pricing & Account Statements (No Opening Balance)
    # الرصيد الحالي = إجمالي المشتريات/التوريدات - إجمالي المدفوعات
    # ==========================================================================
    def get_all_customers_with_balances(self, search: str = "") -> List[Dict[str, Any]]:
        query = """
            SELECT c.*,
                   COALESCE(SUM(t.debit), 0.0) as total_debit,
                   COALESCE(SUM(t.credit), 0.0) as total_credit,
                   (COALESCE(SUM(t.debit), 0.0) - COALESCE(SUM(t.credit), 0.0)) as current_balance,
                   (SELECT COUNT(*) FROM customer_custom_prices cp WHERE cp.customer_id = c.id) as custom_prices_count
            FROM customers c
            LEFT JOIN customer_transactions t ON t.customer_id = c.id
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (c.name LIKE ? OR c.code LIKE ? OR c.phone LIKE ? OR c.address LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s])
        query += " GROUP BY c.id ORDER BY c.id ASC"
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def add_customer(self, data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO customers (code, name, phone, address, pricing_tier, tax_number, credit_limit, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["code"], data["name"], data.get("phone", ""), data.get("address", ""),
                data.get("pricing_tier", "تجزئة / مستهلك (Retail)"), data.get("tax_number", ""),
                float(data.get("credit_limit", 500000.0)),
                data.get("notes", "")
            ))
            conn.commit()
            return cur.lastrowid

    def update_customer(self, cust_id: int, data: Dict[str, Any]):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE customers SET
                    code=?, name=?, phone=?, address=?, pricing_tier=?,
                    tax_number=?, credit_limit=?, notes=?
                WHERE id=?
            """, (
                data["code"], data["name"], data.get("phone", ""), data.get("address", ""),
                data.get("pricing_tier", ""), data.get("tax_number", ""),
                float(data.get("credit_limit", 500000.0)),
                data.get("notes", ""), cust_id
            ))
            conn.commit()

    def delete_customer(self, cust_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM customers WHERE id=?", (cust_id,))
            conn.commit()

    def get_customer_custom_prices(self, customer_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return conn.execute("""
                SELECT cp.*, i.code as item_code, i.name as item_name, i.category as item_category,
                       i.unit as item_unit, i.sale_price as standard_price,
                       (i.sale_price - cp.custom_price) as price_difference
                FROM customer_custom_prices cp
                JOIN items i ON cp.item_id = i.id
                WHERE cp.customer_id = ?
                ORDER BY i.id ASC
            """, (customer_id,)).fetchall()

    def set_customer_custom_price(self, customer_id: int, item_id: int, custom_price: float, notes: str = ""):
        with self.get_connection() as conn:
            item = conn.execute("SELECT sale_price FROM items WHERE id=?", (item_id,)).fetchone()
            std_price = item["sale_price"] if item else custom_price
            disc = max(0.0, std_price - float(custom_price))
            today = datetime.now().strftime("%Y-%m-%d")
            conn.execute("""
                INSERT INTO customer_custom_prices (customer_id, item_id, custom_price, discount_per_ton, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(customer_id, item_id) DO UPDATE SET
                    custom_price=excluded.custom_price,
                    discount_per_ton=excluded.discount_per_ton,
                    updated_at=excluded.updated_at,
                    notes=excluded.notes
            """, (customer_id, item_id, float(custom_price), disc, today, notes))
            conn.commit()

    def delete_customer_custom_price(self, price_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM customer_custom_prices WHERE id=?", (price_id,))
            conn.commit()

    def get_customer_statement(self, customer_id: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Returns customer info and chronological ledger starting purely from live transactions (0.00):
        الرصيد الحالي = إجمالي المشتريات (debit) - إجمالي المدفوعات (credit)
        """
        with self.get_connection() as conn:
            cust = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
            if not cust:
                return {}, []
            txs = conn.execute("""
                SELECT * FROM customer_transactions
                WHERE customer_id=?
                ORDER BY tx_date ASC, id ASC
            """, (customer_id,)).fetchall()

            running = 0.0
            statement_rows = []
            for tx in txs:
                running = running + float(tx["debit"]) - float(tx["credit"])
                row_copy = dict(tx)
                row_copy["running_balance"] = running
                statement_rows.append(row_copy)
            cust["current_balance"] = running
            cust["total_debit"] = sum(float(t["debit"]) for t in txs)   # إجمالي المشتريات / المسحوبات
            cust["total_credit"] = sum(float(t["credit"]) for t in txs) # إجمالي المدفوعات
            return cust, statement_rows

    def add_customer_transaction(self, data: Dict[str, Any], also_post_journal: bool = True):
        with self.get_connection() as conn:
            c = conn.cursor()
            purchases_amt = float(data.get("debit", 0.0))
            payments_amt = float(data.get("credit", 0.0))
            c.execute("""
                INSERT INTO customer_transactions (
                    customer_id, tx_date, tx_type, reference_no, description,
                    debit, credit, payment_method, due_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(data["customer_id"]), data["tx_date"], data["tx_type"],
                data.get("reference_no", ""), data["description"],
                purchases_amt, payments_amt,
                data.get("payment_method", ""), data.get("due_date", "")
            ))
            if also_post_journal:
                cust = c.execute("SELECT name FROM customers WHERE id=?", (int(data["customer_id"]),)).fetchone()
                cust_name = cust["name"] if cust else "عميل"
                j_no = f"TRX-{datetime.now().strftime('%m%d-%H%M%S')}"
                if payments_amt > 0:
                    c.execute("""
                        INSERT INTO journal_entries (
                            entry_no, entry_date, category, debit_account, credit_account,
                            description, debit_amount, credit_amount, payment_method, party_name, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        j_no, data["tx_date"], "تحصيل دفعة من عميل",
                        "وارد / قبض (إيراد أو تحصيل نقدية)", data.get("payment_method", "الخزينة"),
                        data["description"], payments_amt, 0.0,
                        data.get("payment_method", ""), cust_name, data.get("reference_no", "")
                    ))
                elif purchases_amt > 0:
                    is_credit = "آجل" in data.get("payment_method", "")
                    flow = "معاملة آجلة (بيع أو شراء على الحساب)" if is_credit else "وارد / قبض (إيراد أو تحصيل نقدية)"
                    c.execute("""
                        INSERT INTO journal_entries (
                            entry_no, entry_date, category, debit_account, credit_account,
                            description, debit_amount, credit_amount, payment_method, party_name, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        j_no, data["tx_date"], "مبيعات حديد وأسمنت",
                        flow, data.get("payment_method", "الخزينة"),
                        data["description"], purchases_amt, 0.0,
                        data.get("payment_method", ""), cust_name, data.get("reference_no", "")
                    ))
            conn.commit()

    def delete_customer_transaction(self, tx_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM customer_transactions WHERE id=?", (tx_id,))
            conn.commit()

    # ==========================================================================
    # Module 4: Suppliers & Payables & Aging Reports (No Opening Balance)
    # الرصيد الحالي = إجمالي المشتريات/التوريدات - إجمالي المدفوعات
    # ==========================================================================
    def get_all_suppliers_with_balances(self, search: str = "") -> List[Dict[str, Any]]:
        query = """
            SELECT s.*,
                   COALESCE(SUM(t.debit), 0.0) as total_debit,
                   COALESCE(SUM(t.credit), 0.0) as total_credit,
                   (COALESCE(SUM(t.credit), 0.0) - COALESCE(SUM(t.debit), 0.0)) as current_balance
            FROM suppliers s
            LEFT JOIN supplier_transactions t ON t.supplier_id = s.id
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (s.name LIKE ? OR s.code LIKE ? OR s.factory_type LIKE ? OR s.phone LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s])
        query += " GROUP BY s.id ORDER BY s.id ASC"
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def add_supplier(self, data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO suppliers (code, name, factory_type, phone, address, tax_number, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data["code"], data["name"], data.get("factory_type", "مصنع حديد تسليح"),
                data.get("phone", ""), data.get("address", ""), data.get("tax_number", ""),
                data.get("notes", "")
            ))
            conn.commit()
            return cur.lastrowid

    def update_supplier(self, sup_id: int, data: Dict[str, Any]):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE suppliers SET
                    code=?, name=?, factory_type=?, phone=?, address=?,
                    tax_number=?, notes=?
                WHERE id=?
            """, (
                data["code"], data["name"], data.get("factory_type", ""),
                data.get("phone", ""), data.get("address", ""), data.get("tax_number", ""),
                data.get("notes", ""), sup_id
            ))
            conn.commit()

    def delete_supplier(self, sup_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM suppliers WHERE id=?", (sup_id,))
            conn.commit()

    def get_supplier_statement(self, supplier_id: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Returns supplier info and chronological ledger starting purely from live transactions (0.00):
        الرصيد الحالي = إجمالي المشتريات/التوريدات (credit) - إجمالي المدفوعات المسددة (debit)
        """
        with self.get_connection() as conn:
            sup = conn.execute("SELECT * FROM suppliers WHERE id=?", (supplier_id,)).fetchone()
            if not sup:
                return {}, []
            txs = conn.execute("""
                SELECT * FROM supplier_transactions
                WHERE supplier_id=?
                ORDER BY tx_date ASC, id ASC
            """, (supplier_id,)).fetchall()

            running = 0.0
            statement_rows = []
            for tx in txs:
                running = running + float(tx["credit"]) - float(tx["debit"])
                row_copy = dict(tx)
                row_copy["running_balance"] = running
                statement_rows.append(row_copy)
            sup["current_balance"] = running
            sup["total_debit"] = sum(float(t["debit"]) for t in txs)   # إجمالي المدفوعات المسددة
            sup["total_credit"] = sum(float(t["credit"]) for t in txs) # إجمالي المشتريات والتوريدات
            return sup, statement_rows

    def add_supplier_transaction(self, data: Dict[str, Any], also_post_journal: bool = True):
        with self.get_connection() as conn:
            c = conn.cursor()
            payments_amt = float(data.get("debit", 0.0))
            purchases_amt = float(data.get("credit", 0.0))
            c.execute("""
                INSERT INTO supplier_transactions (
                    supplier_id, tx_date, tx_type, reference_no, description,
                    debit, credit, payment_method, due_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(data["supplier_id"]), data["tx_date"], data["tx_type"],
                data.get("reference_no", ""), data["description"],
                payments_amt, purchases_amt,
                data.get("payment_method", ""), data.get("due_date", "")
            ))
            if also_post_journal:
                sup = c.execute("SELECT name FROM suppliers WHERE id=?", (int(data["supplier_id"]),)).fetchone()
                sup_name = sup["name"] if sup else "مورد"
                j_no = f"TRX-{datetime.now().strftime('%m%d-%H%M%S')}"
                if payments_amt > 0:
                    c.execute("""
                        INSERT INTO journal_entries (
                            entry_no, entry_date, category, debit_account, credit_account,
                            description, debit_amount, credit_amount, payment_method, party_name, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        j_no, data["tx_date"], "سداد دفعة لمورد / مصنع",
                        "صادر / صرف (مصروف أو سداد دفعة)", data.get("payment_method", "الخزينة"),
                        data["description"], 0.0, payments_amt,
                        data.get("payment_method", ""), sup_name, data.get("reference_no", "")
                    ))
                elif purchases_amt > 0:
                    is_credit = "آجل" in data.get("payment_method", "")
                    flow = "معاملة آجلة (بيع أو شراء على الحساب)" if is_credit else "صادر / صرف (مصروف أو سداد دفعة)"
                    c.execute("""
                        INSERT INTO journal_entries (
                            entry_no, entry_date, category, debit_account, credit_account,
                            description, debit_amount, credit_amount, payment_method, party_name, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        j_no, data["tx_date"], "مشتريات وتوريدات مصانع",
                        flow, data.get("payment_method", "الخزينة"),
                        data["description"], 0.0, purchases_amt,
                        data.get("payment_method", ""), sup_name, data.get("reference_no", "")
                    ))
            conn.commit()

    def delete_supplier_transaction(self, tx_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM supplier_transactions WHERE id=?", (tx_id,))
            conn.commit()

    def get_suppliers_aging_report(self) -> List[Dict[str, Any]]:
        suppliers = self.get_all_suppliers_with_balances()
        now = datetime.now()
        report = []
        with self.get_connection() as conn:
            for sup in suppliers:
                balance = float(sup["current_balance"])
                if balance <= 0:
                    report.append({
                        "supplier_id": sup["id"],
                        "code": sup["code"],
                        "name": sup["name"],
                        "factory_type": sup["factory_type"],
                        "phone": sup["phone"],
                        "b_0_30": 0.0,
                        "b_31_60": 0.0,
                        "b_61_90": 0.0,
                        "b_90_plus": 0.0,
                        "total_due": balance
                    })
                    continue

                txs = conn.execute("""
                    SELECT tx_date, credit FROM supplier_transactions
                    WHERE supplier_id=? AND credit > 0
                    ORDER BY tx_date DESC
                """, (sup["id"],)).fetchall()

                rem = balance
                b_0_30 = b_31_60 = b_61_90 = b_90_plus = 0.0
                for tx in txs:
                    if rem <= 0:
                        break
                    alloc = min(rem, float(tx["credit"]))
                    rem -= alloc
                    try:
                        dt = datetime.strptime(tx["tx_date"], "%Y-%m-%d")
                        days = (now - dt).days
                    except ValueError:
                        days = 15
                    if days <= 30:
                        b_0_30 += alloc
                    elif days <= 60:
                        b_31_60 += alloc
                    elif days <= 90:
                        b_61_90 += alloc
                    else:
                        b_90_plus += alloc

                if rem > 0:
                    b_90_plus += rem

                report.append({
                    "supplier_id": sup["id"],
                    "code": sup["code"],
                    "name": sup["name"],
                    "factory_type": sup["factory_type"],
                    "phone": sup["phone"],
                    "b_0_30": b_0_30,
                    "b_31_60": b_31_60,
                    "b_61_90": b_61_90,
                    "b_90_plus": b_90_plus,
                    "total_due": balance
                })
        return report

    # ==========================================================================
    # Module 5: Employees & Payroll
    # ==========================================================================
    def get_employees(self, search: str = "") -> List[Dict[str, Any]]:
        query = "SELECT * FROM employees WHERE 1=1"
        params = []
        if search:
            query += " AND (name LIKE ? OR code LIKE ? OR role LIKE ? OR department LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s])
        query += " ORDER BY id ASC"
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def add_employee(self, data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO employees (code, name, role, department, phone, national_id, hire_date, base_salary, housing_allowance, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["code"], data["name"], data["role"], data.get("department", "الإدارة"),
                data.get("phone", ""), data.get("national_id", ""), data["hire_date"],
                float(data["base_salary"]), float(data.get("housing_allowance", 0.0)),
                data.get("status", "نشط")
            ))
            conn.commit()
            return cur.lastrowid

    def update_employee(self, emp_id: int, data: Dict[str, Any]):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE employees SET
                    code=?, name=?, role=?, department=?, phone=?,
                    national_id=?, hire_date=?, base_salary=?, housing_allowance=?, status=?
                WHERE id=?
            """, (
                data["code"], data["name"], data["role"], data.get("department", ""),
                data.get("phone", ""), data.get("national_id", ""), data["hire_date"],
                float(data["base_salary"]), float(data.get("housing_allowance", 0.0)),
                data.get("status", "نشط"), emp_id
            ))
            conn.commit()

    def delete_employee(self, emp_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))
            conn.commit()

    def get_payroll_records(self, month_year: str = "") -> List[Dict[str, Any]]:
        query = """
            SELECT p.*, e.code as emp_code, e.name as emp_name, e.role as emp_role, e.department as emp_dept, e.phone as emp_phone
            FROM payroll_records p
            JOIN employees e ON p.employee_id = e.id
            WHERE 1=1
        """
        params = []
        if month_year and not month_year.startswith("كل") and month_year != "الكل" and month_year.lower() != "all":
            query += " AND p.month_year = ?"
            params.append(month_year)
        query += " ORDER BY p.payment_date DESC, p.id DESC"
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def add_payroll_record(self, data: Dict[str, Any], post_to_journal: bool = True) -> int:
        base = float(data["base_salary"])
        bonuses = float(data.get("bonuses", 0.0))
        deductions = float(data.get("deductions", 0.0))
        advances = float(data.get("advances", 0.0))
        net = base + bonuses - deductions - advances

        with self.get_connection() as conn:
            c = conn.cursor()
            cur = c.execute("""
                INSERT INTO payroll_records (
                    employee_id, month_year, payment_date, base_salary,
                    bonuses, deductions, advances, net_salary, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(data["employee_id"]), data["month_year"], data["payment_date"],
                base, bonuses, deductions, advances, net,
                data.get("status", "تم الصرف"), data.get("notes", "")
            ))
            if post_to_journal and net > 0:
                emp = c.execute("SELECT name FROM employees WHERE id=?", (int(data["employee_id"]),)).fetchone()
                emp_name = emp["name"] if emp else "موظف"
                j_no = f"TRX-PAY-{datetime.now().strftime('%m%d%H%M%S')}"
                c.execute("""
                    INSERT INTO journal_entries (
                        entry_no, entry_date, category, debit_account, credit_account,
                        description, debit_amount, credit_amount, payment_method, party_name, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    j_no, data["payment_date"], "رواتب وأجور وسلف موظفين",
                    "صادر / صرف (مصروف أو سداد دفعة)", "الخزينة الرئيسية",
                    f"صرف راتب شهر {data['month_year']} للموظف: {emp_name}",
                    0.0, net, "نقدي بالخزينة (Cash)", emp_name, data.get("notes", "")
                ))
            conn.commit()
            return cur.lastrowid

    def delete_payroll_record(self, record_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM payroll_records WHERE id=?", (record_id,))
            conn.commit()
