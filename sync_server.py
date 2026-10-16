# -*- coding: utf-8 -*-
"""
Local Sync Server for Al-Bonyan ERP (خادم المزامنة اللاسلكي المحلي)
Connects Desktop SQLite database with Android Mobile Application over local Wi-Fi.
Run standalone: python sync_server.py
"""
import os
import sys
import socket
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from database import DatabaseManager
from config import APP_NAME, APP_VERSION, CURRENCY, CURRENCY_NAME, ITEM_CATEGORIES, FLOW_TYPES, JOURNAL_CATEGORIES, PAYMENT_METHODS


def get_local_ip() -> str:
    """Detect the local machine IP on Wi-Fi/LAN."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually send traffic, just determines outbound interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def create_sync_app(db: Optional[DatabaseManager] = None) -> FastAPI:
    if db is None:
        db = DatabaseManager()

    app = FastAPI(
        title=f"{APP_NAME} - API",
        version=APP_VERSION,
        description="Local Wi-Fi Synchronization API for Android Mobile App"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --------------------------------------------------------------------------
    # Ping & Network Info
    # --------------------------------------------------------------------------
    @app.get("/api/ping")
    def ping():
        local_ip = get_local_ip()
        stats = db.get_dashboard_summary()
        return {
            "status": "online",
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "currency": CURRENCY,
            "currency_name": CURRENCY_NAME,
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "local_ip": local_ip,
            "hostname": socket.gethostname(),
            "items_count": stats.get("item_count", 0),
            "cash_in": stats.get("total_cash_in", 0.0),
            "cash_out": stats.get("total_cash_out", 0.0)
        }

    # --------------------------------------------------------------------------
    # 1. Dashboard
    # --------------------------------------------------------------------------
    @app.get("/api/dashboard")
    def get_dashboard():
        stats = db.get_dashboard_summary()
        recents = db.get_journal_entries()[:10]
        return {
            "success": True,
            "kpis": {
                "total_cash_in": stats.get("total_cash_in", 0),
                "total_cash_out": stats.get("total_cash_out", 0),
                "net_cash": stats.get("net_cash", 0),
                "inventory_valuation": stats.get("cost_valuation", 0),
                "customers_balance": stats.get("total_receivables", 0),
                "suppliers_balance": stats.get("total_payables", 0),
                "sales_total": stats.get("sales_total", 0),
                "purchases_total": stats.get("purchases_total", 0)
            },
            "summary": stats,
            "recent_transactions": recents
        }

    # --------------------------------------------------------------------------
    # 2. Daily Journal & Transactions (سجل اليومية وحركة النقدية)
    # --------------------------------------------------------------------------
    @app.get("/api/journal")
    def get_journal(
        search: str = Query("", description="بحث برقم الحركة أو البيان"),
        category: str = Query("", description="تصفية ببند المعاملة"),
        flow_filter: str = Query("", description="تصفية باتجاه الحركة (وارد/صادر)")
    ):
        entries = db.get_journal_entries(search=search, category=category, flow_filter=flow_filter)
        return {"success": True, "entries": entries, "count": len(entries)}

    @app.post("/api/journal")
    def add_journal(data: Dict[str, Any] = Body(...)):
        amt = float(data.get("amount", 0.0))
        entry_type = data.get("entry_type", "")
        flow = data.get("flow_type", "")
        cat = data.get("category", "مبيعات حديد وأسمنت")

        if entry_type in ('sale', 'receipt', 'cust_pay') or "وارد" in flow or "قبض" in flow:
            cash_in, cash_out = amt, 0.0
            if not flow:
                flow = "وارد / قبض (إيراد أو تحصيل نقدية)"
        elif entry_type in ('purchase', 'payment', 'expense', 'supp_pay', 'payroll') or "صادر" in flow or "صرف" in flow:
            cash_in, cash_out = 0.0, amt
            if not flow:
                flow = "صادر / صرف (مشتريات أو مصروفات)"
        else:
            cash_in, cash_out = (amt, 0.0) if "مبيعات" in cat else (0.0, amt)
            if not flow:
                flow = "وارد / قبض (إيراد أو تحصيل نقدية)" if cash_in > 0 else "صادر / صرف (مشتريات أو مصروفات)"

        payload = {
            "entry_no": data.get("entry_no") or db.get_next_journal_no(),
            "entry_date": data.get("entry_date") or datetime.now().strftime("%Y-%m-%d"),
            "category": cat,
            "flow_type": flow,
            "safe_name": data.get("safe_name", "الخزينة الرئيسية"),
            "description": data.get("description", "معاملة مسجلة من تطبيق الموبايل"),
            "cash_in": cash_in,
            "cash_out": cash_out,
            "payment_method": data.get("payment_method", "نقدي بالخزينة (Cash)"),
            "party_name": data.get("party_name", ""),
            "notes": data.get("notes", "مسجل عبر تطبيق الهاتف")
        }
        entry_id = db.add_journal_entry(payload)
        return {"success": True, "id": entry_id, "entry_no": payload["entry_no"]}

    # --------------------------------------------------------------------------
    # 3. Inventory & Warehouses (أرصدة الحديد والأسمنت والمخازن)
    # --------------------------------------------------------------------------
    @app.get("/api/warehouses")
    def get_warehouses():
        return db.get_warehouses()

    @app.get("/api/inventory")
    def get_inventory(
        warehouse_id: Optional[int] = Query(None),
        category: str = Query(""),
        search: str = Query(""),
        low_stock_only: bool = Query(False)
    ):
        return db.get_items(warehouse_id=warehouse_id, category=category, search=search, low_stock_only=low_stock_only)

    @app.post("/api/inventory/movements")
    def add_stock_movement(data: Dict[str, Any] = Body(...)):
        mov_id = db.add_stock_movement(data)
        return {"success": True, "movement_id": mov_id}

    # --------------------------------------------------------------------------
    # 4. Customers (العملاء وكشوف الحساب)
    # --------------------------------------------------------------------------
    @app.get("/api/customers")
    def get_customers(search: str = Query("")):
        return db.get_all_customers_with_balances(search=search)

    @app.get("/api/customers/{customer_id}/statement")
    def get_customer_statement(customer_id: int):
        cust, rows = db.get_customer_statement(customer_id)
        if not cust:
            raise HTTPException(status_code=404, detail="العميل غير موجود")
        return {"customer": cust, "statement": rows}

    @app.post("/api/customers/transaction")
    def add_customer_transaction(data: Dict[str, Any] = Body(...)):
        db.add_customer_transaction(data, also_post_journal=data.get("also_post_journal", True))
        return {"success": True}

    # --------------------------------------------------------------------------
    # 5. Suppliers (الموردين والمصانع)
    # --------------------------------------------------------------------------
    @app.get("/api/suppliers")
    def get_suppliers(search: str = Query("")):
        return db.get_all_suppliers_with_balances(search=search)

    @app.get("/api/suppliers/{supplier_id}/statement")
    def get_supplier_statement(supplier_id: int):
        sup, rows = db.get_supplier_statement(supplier_id)
        if not sup:
            raise HTTPException(status_code=404, detail="المورد غير موجود")
        return {"supplier": sup, "statement": rows}

    @app.post("/api/suppliers/transaction")
    def add_supplier_transaction(data: Dict[str, Any] = Body(...)):
        db.add_supplier_transaction(data, also_post_journal=data.get("also_post_journal", True))
        return {"success": True}

    # --------------------------------------------------------------------------
    # 6. Payroll (الرواتب والموظفين)
    # --------------------------------------------------------------------------
    @app.get("/api/employees")
    def get_employees(search: str = Query("")):
        return db.get_employees(search=search)

    @app.get("/api/payroll")
    def get_payroll(month_year: str = Query("")):
        return db.get_payroll_records(month_year=month_year)

    @app.post("/api/payroll")
    def add_payroll(data: Dict[str, Any] = Body(...)):
        rec_id = db.add_payroll_record(data, post_to_journal=data.get("post_to_journal", True))
        return {"success": True, "payroll_id": rec_id}

    # --------------------------------------------------------------------------
    # 7. Mobile Web Progressive Interface (الواجهة المجهزة فوراً لكافة متصفحات الهواتف)
    # --------------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    @app.get("/mobile", response_class=HTMLResponse)
    def mobile_web_interface():
        return get_mobile_html_app()

    return app


def get_mobile_html_app() -> str:
    """
    Returns an ultra-clean, minimalist, responsive Arabic mobile web app
    that works seamlessly on all Android devices via browser or Add to Home Screen (PWA).
    """
    return """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>البنيان ERP - الموبايل</title>
    <meta name="theme-color" content="#0D1117">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-color: #0D1117;
            --surface: #161B22;
            --surface-hover: #21262D;
            --border: #30363D;
            --text: #F0F6FC;
            --text-muted: #8B949E;
            --primary: #3B82F6;
            --success: #10B981;
            --danger: #EF4444;
            --warning: #F59E0B;
            --accent: #D97706;
            --radius: 12px;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, Arial, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text);
            padding-bottom: 70px;
        }
        /* App Header */
        header {
            position: sticky;
            top: 0;
            z-index: 100;
            background: rgba(22, 27, 34, 0.95);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid var(--border);
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header-title {
            font-size: 16px;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: var(--success);
            box-shadow: 0 0 8px var(--success);
        }
        .refresh-btn {
            background: var(--surface-hover);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 6px 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        /* Main Container */
        .container {
            padding: 14px;
            max-width: 600px;
            margin: 0 auto;
        }
        /* KPI Cards */
        .kpi-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 16px;
        }
        .kpi-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 12px;
            position: relative;
            overflow: hidden;
        }
        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 4px;
            height: 100%;
            background: var(--primary);
        }
        .kpi-card.green::before { background: var(--success); }
        .kpi-card.red::before { background: var(--danger); }
        .kpi-card.gold::before { background: var(--warning); }
        .kpi-title {
            font-size: 11px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }
        .kpi-value {
            font-size: 16px;
            font-weight: bold;
            color: var(--text);
        }
        /* Sections & Cards */
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 14px;
            margin-bottom: 14px;
        }
        .card-header {
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--text);
        }
        /* Form Inputs */
        .form-group {
            margin-bottom: 10px;
        }
        .form-label {
            display: block;
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }
        .form-input, .form-select {
            width: 100%;
            background: #0D1117;
            border: 1px solid var(--border);
            color: var(--text);
            padding: 9px 12px;
            border-radius: 8px;
            font-size: 14px;
            outline: none;
        }
        .form-input:focus, .form-select:focus {
            border-color: var(--primary);
        }
        .btn-submit {
            width: 100%;
            background: var(--success);
            color: #fff;
            border: none;
            padding: 11px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        /* List Items */
        .item-list {
            list-style: none;
        }
        .list-entry {
            background: #0D1117;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .entry-title {
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 3px;
        }
        .entry-subtitle {
            font-size: 11px;
            color: var(--text-muted);
        }
        .entry-amount {
            font-size: 14px;
            font-weight: bold;
            text-align: left;
        }
        .amount-green { color: var(--success); }
        .amount-red { color: var(--danger); }
        .amount-gold { color: var(--warning); }
        /* Bottom Tab Navigation Bar */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 60px;
            background: rgba(22, 27, 34, 0.98);
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-around;
            align-items: center;
            z-index: 100;
        }
        .nav-tab {
            color: var(--text-muted);
            text-decoration: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 3px;
            font-size: 11px;
            cursor: pointer;
            flex: 1;
            padding: 6px 0;
        }
        .nav-tab.active {
            color: var(--primary);
            font-weight: bold;
        }
        .nav-tab i {
            font-size: 18px;
        }
        /* Views */
        .tab-view {
            display: none;
        }
        .tab-view.active {
            display: block;
        }
        .badge {
            display: inline-block;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            background: var(--surface-hover);
            color: var(--text-muted);
        }
    </style>
</head>
<body>

    <header>
        <div class="header-title">
            <span class="status-dot" id="statusDot"></span>
            <span>البنيان ERP (موبايل)</span>
        </div>
        <button class="refresh-btn" onclick="refreshCurrentTab()">
            <i class="fa fa-sync-alt" id="refreshIcon"></i>
            <span>تحديث</span>
        </button>
    </header>

    <div class="container">
        <!-- 1. DASHBOARD VIEW -->
        <div id="view-dashboard" class="tab-view active">
            <div class="kpi-grid">
                <div class="kpi-card green">
                    <div class="kpi-title">إجمالي المقبوضات (+)</div>
                    <div class="kpi-value" id="kpi-cash-in">0.00 ج.م</div>
                </div>
                <div class="kpi-card red">
                    <div class="kpi-title">إجمالي المدفوعات (-)</div>
                    <div class="kpi-value" id="kpi-cash-out">0.00 ج.م</div>
                </div>
                <div class="kpi-card gold">
                    <div class="kpi-title">تقييم المخزون الحالي</div>
                    <div class="kpi-value" id="kpi-inv">0.00 ج.م</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">صافي السيولة</div>
                    <div class="kpi-value" id="kpi-net">0.00 ج.م</div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span>⚡ أحدث حركات اليومية</span>
                    <span class="badge" id="journalCount">0 حركة</span>
                </div>
                <ul class="item-list" id="recentJournalList">
                    <li style="text-align: center; color: var(--text-muted); padding: 10px;">جاري التحميل...</li>
                </ul>
            </div>
        </div>

        <!-- 2. JOURNAL VIEW (إضافة وعرض حركات اليومية) -->
        <div id="view-journal" class="tab-view">
            <div class="card">
                <div class="card-header">
                    <span>➕ تسجيل حركة نقدية جديدة</span>
                </div>
                <form id="journalForm" onsubmit="submitJournal(event)">
                    <div class="form-group">
                        <label class="form-label">اتجاه الحركة</label>
                        <select class="form-select" id="j_flow">
                            <option value="وارد / قبض (إيراد أو تحصيل نقدية)">وارد / قبض (+) (مبيعات / تحصيل)</option>
                            <option value="صادر / صرف (مصروف أو سداد دفعة)">صادر / صرف (-) (مشتريات / سداد / نولون)</option>
                            <option value="معاملة آجلة (بيع أو شراء على الحساب)">آجل / على الحساب</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">بند المعاملة</label>
                        <select class="form-select" id="j_cat">
                            <option value="مبيعات حديد وأسمنت">مبيعات حديد وأسمنت</option>
                            <option value="تحصيل دفعة من عميل">تحصيل دفعة من عميل</option>
                            <option value="مشتريات وتوريدات مصانع">مشتريات وتوريدات مصانع</option>
                            <option value="سداد دفعة لمورد / مصنع">سداد دفعة لمورد / مصنع</option>
                            <option value="مصروفات تشغيل ونولون شحن">مصروفات تشغيل ونولون شحن</option>
                            <option value="رواتب وأجور وسلف موظفين">رواتب وأجور وسلف موظفين</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">المبلغ (ج.م)</label>
                        <input type="number" step="0.01" class="form-input" id="j_amt" placeholder="أدخل المبلغ..." required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">العميل / المورد / السائق</label>
                        <input type="text" class="form-input" id="j_party" placeholder="اسم الطرف (اختياري)">
                    </div>
                    <div class="form-group">
                        <label class="form-label">البيان والتفاصيل</label>
                        <input type="text" class="form-input" id="j_desc" placeholder="مثال: بيع 10 طن حديد عز..." required>
                    </div>
                    <button type="submit" class="btn-submit">
                        <i class="fa fa-save"></i> حفظ الحركة فوراً
                    </button>
                </form>
            </div>

            <div class="card">
                <div class="card-header">
                    <span>📋 حركات اليومية المسجلة</span>
                </div>
                <ul class="item-list" id="allJournalList"></ul>
            </div>
        </div>

        <!-- 3. INVENTORY VIEW (المخزون والأصناف) -->
        <div id="view-inventory" class="tab-view">
            <div class="card">
                <div class="card-header">
                    <span>🏗️ جرد أصناف الحديد والأسمنت</span>
                    <span class="badge" id="invCount">0 صنف</span>
                </div>
                <ul class="item-list" id="inventoryList"></ul>
            </div>
        </div>

        <!-- 4. CUSTOMERS VIEW (العملاء والمطابقات) -->
        <div id="view-customers" class="tab-view">
            <div class="card">
                <div class="card-header">
                    <span>👥 دليل العملاء والأرصدة المستحقة</span>
                </div>
                <ul class="item-list" id="customersList"></ul>
            </div>
        </div>

        <!-- 5. SETTINGS VIEW (إعدادات الربط والشبكة) -->
        <div id="view-settings" class="tab-view">
            <div class="card">
                <div class="card-header">
                    <span>📡 إعدادات ربط المزامنة (Wi-Fi Sync)</span>
                </div>
                <div class="form-group">
                    <label class="form-label">عنوان خادم الكمبيوتر (Server IP)</label>
                    <input type="text" class="form-input" id="cfg_server_url" placeholder="مثال: http://192.168.1.10:8000">
                </div>
                <button type="button" class="btn-submit" style="background: var(--primary);" onclick="saveServerConfig()">
                    <i class="fa fa-plug"></i> حفظ واختبار الاتصال
                </button>
                <div id="connResult" style="margin-top: 10px; font-size: 12px; text-align: center;"></div>
            </div>

            <div class="card" style="text-align: center; color: var(--text-muted); font-size: 12px;">
                <p><strong>نظام البنيان للحديد والأسمنت - تطبيق الهاتف المحمول</strong></p>
                <p style="margin-top: 4px;">متصل بالخادم المحلي وقاعدة بيانات SQLite المشتركة</p>
            </div>
        </div>
    </div>

    <!-- Bottom Navigation -->
    <nav class="bottom-nav">
        <div class="nav-tab active" onclick="switchTab('dashboard')">
            <i class="fa fa-chart-pie"></i>
            <span>الرئيسية</span>
        </div>
        <div class="nav-tab" onclick="switchTab('journal')">
            <i class="fa fa-book"></i>
            <span>اليومية</span>
        </div>
        <div class="nav-tab" onclick="switchTab('inventory')">
            <i class="fa fa-cubes"></i>
            <span>المخزون</span>
        </div>
        <div class="nav-tab" onclick="switchTab('customers')">
            <i class="fa fa-users"></i>
            <span>العملاء</span>
        </div>
        <div class="nav-tab" onclick="switchTab('settings')">
            <i class="fa fa-cog"></i>
            <span>الاتصال</span>
        </div>
    </nav>

    <script>
        let currentTab = 'dashboard';
        let serverUrl = localStorage.getItem('erp_server_url') || window.location.origin;

        document.getElementById('cfg_server_url').value = serverUrl;

        function switchTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));

            const view = document.getElementById('view-' + tab);
            if (view) view.classList.add('active');

            const tabs = ['dashboard', 'journal', 'inventory', 'customers', 'settings'];
            const idx = tabs.indexOf(tab);
            if (idx >= 0) {
                document.querySelectorAll('.nav-tab')[idx].classList.add('active');
            }
            refreshCurrentTab();
        }

        async function fetchAPI(endpoint, options = {}) {
            try {
                const res = await fetch(serverUrl + endpoint, options);
                if (!res.ok) throw new Error('Network error');
                document.getElementById('statusDot').style.background = 'var(--success)';
                return await res.json();
            } catch (err) {
                document.getElementById('statusDot').style.background = 'var(--danger)';
                throw err;
            }
        }

        async function refreshCurrentTab() {
            const icon = document.getElementById('refreshIcon');
            icon.classList.add('fa-spin');
            try {
                if (currentTab === 'dashboard') await loadDashboard();
                else if (currentTab === 'journal') await loadJournal();
                else if (currentTab === 'inventory') await loadInventory();
                else if (currentTab === 'customers') await loadCustomers();
            } catch(e) {
                console.error(e);
            } finally {
                setTimeout(() => icon.classList.remove('fa-spin'), 400);
            }
        }

        async function loadDashboard() {
            const data = await fetchAPI('/api/dashboard');
            document.getElementById('kpi-cash-in').innerText = Number(data.total_cash_in).toLocaleString() + ' ج.م';
            document.getElementById('kpi-cash-out').innerText = Number(data.total_cash_out).toLocaleString() + ' ج.م';
            document.getElementById('kpi-inv').innerText = Number(data.cost_valuation).toLocaleString() + ' ج.م';
            document.getElementById('kpi-net').innerText = Number(data.net_cash).toLocaleString() + ' ج.م';

            const journal = await fetchAPI('/api/journal');
            document.getElementById('journalCount').innerText = journal.length + ' حركة';
            const list = document.getElementById('recentJournalList');
            list.innerHTML = '';
            journal.slice(0, 5).forEach(j => {
                const isPositive = Number(j.debit_amount) > 0;
                const amt = isPositive ? j.debit_amount : j.credit_amount;
                const cls = isPositive ? 'amount-green' : 'amount-red';
                const sign = isPositive ? '+' : '-';
                list.innerHTML += `
                    <li class="list-entry">
                        <div>
                            <div class="entry-title">${j.description}</div>
                            <div class="entry-subtitle">${j.entry_date} • ${j.party_name || j.category}</div>
                        </div>
                        <div class="entry-amount ${cls}">${sign}${Number(amt).toLocaleString()} ج.م</div>
                    </li>
                `;
            });
        }

        async function loadJournal() {
            const journal = await fetchAPI('/api/journal');
            const list = document.getElementById('allJournalList');
            list.innerHTML = '';
            journal.forEach(j => {
                const isPositive = Number(j.debit_amount) > 0;
                const amt = isPositive ? j.debit_amount : j.credit_amount;
                const cls = isPositive ? 'amount-green' : 'amount-red';
                const sign = isPositive ? '+' : '-';
                list.innerHTML += `
                    <li class="list-entry">
                        <div>
                            <div class="entry-title">${j.entry_no}: ${j.description}</div>
                            <div class="entry-subtitle">${j.entry_date} • ${j.party_name || j.category} • ${j.payment_method}</div>
                        </div>
                        <div class="entry-amount ${cls}">${sign}${Number(amt).toLocaleString()} ج.م</div>
                    </li>
                `;
            });
        }

        async function submitJournal(e) {
            e.preventDefault();
            const payload = {
                flow_type: document.getElementById('j_flow').value,
                category: document.getElementById('j_cat').value,
                amount: parseFloat(document.getElementById('j_amt').value),
                party_name: document.getElementById('j_party').value.trim(),
                description: document.getElementById('j_desc').value.trim()
            };
            try {
                await fetchAPI('/api/journal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                alert('✅ تم حفظ المعاملة بنجاح في قاعدة البيانات المشتركة');
                document.getElementById('j_amt').value = '';
                document.getElementById('j_party').value = '';
                document.getElementById('j_desc').value = '';
                loadJournal();
            } catch (err) {
                alert('❌ تعذر الحفظ. تأكد من الاتصال بخادم الكمبيوتر.');
            }
        }

        async function loadInventory() {
            const items = await fetchAPI('/api/inventory');
            document.getElementById('invCount').innerText = items.length + ' صنف';
            const list = document.getElementById('inventoryList');
            list.innerHTML = '';
            items.forEach(it => {
                list.innerHTML += `
                    <li class="list-entry">
                        <div>
                            <div class="entry-title">${it.name}</div>
                            <div class="entry-subtitle">كود: ${it.code} • ${it.category} • ${it.warehouse_name}</div>
                        </div>
                        <div class="entry-amount amount-gold">
                            ${Number(it.quantity).toFixed(1)} ${it.unit}
                            <div style="font-size: 11px; color: var(--text-muted);">${Number(it.sale_price).toLocaleString()} ج.م</div>
                        </div>
                    </li>
                `;
            });
        }

        async function loadCustomers() {
            const custs = await fetchAPI('/api/customers');
            const list = document.getElementById('customersList');
            list.innerHTML = '';
            custs.forEach(c => {
                const bal = Number(c.current_balance);
                const cls = bal > 0 ? 'amount-green' : 'amount-red';
                list.innerHTML += `
                    <li class="list-entry">
                        <div>
                            <div class="entry-title">${c.name}</div>
                            <div class="entry-subtitle">${c.phone || 'بدون هاتف'} • ${c.pricing_tier}</div>
                        </div>
                        <div class="entry-amount ${cls}">
                            ${bal.toLocaleString()} ج.م
                            <div style="font-size: 10px; color: var(--text-muted);">${bal >= 0 ? 'رصيد لنا' : 'رصيد عليه'}</div>
                        </div>
                    </li>
                `;
            });
        }

        async function saveServerConfig() {
            const url = document.getElementById('cfg_server_url').value.trim();
            serverUrl = url;
            localStorage.setItem('erp_server_url', url);
            const resDiv = document.getElementById('connResult');
            resDiv.innerHTML = '<span style="color: var(--warning);">جاري اختبار الاتصال...</span>';
            try {
                const data = await fetchAPI('/api/ping');
                resDiv.innerHTML = `<span style="color: var(--success);">✅ متصل بنجاح مع ${data.hostname} (${data.app_name})</span>`;
            } catch(e) {
                resDiv.innerHTML = '<span style="color: var(--danger);">❌ فشل الاتصال. تأكد أن الهاتف والكمبيوتر متصلان بنفس شبكة Wi-Fi.</span>';
            }
        }

        // Initial Load
        loadDashboard();
    </script>
</body>
</html>
"""


class SyncServerThread(threading.Thread):
    """Background daemon thread to run the FastAPI sync server inside Desktop app."""
    def __init__(self, host: str = "0.0.0.0", port: int = 8000, db: Optional[DatabaseManager] = None):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.db = db
        self.server = None
        self.is_running = False

    def run(self):
        app = create_sync_app(self.db)
        config = uvicorn.Config(app=app, host=self.host, port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.is_running = True
        self.server.run()
        self.is_running = False

    def stop(self):
        if self.server:
            self.server.should_exit = True


_global_server_thread: Optional[SyncServerThread] = None


def start_sync_server(db: Optional[DatabaseManager] = None, host: str = "0.0.0.0", port: int = 8000) -> SyncServerThread:
    global _global_server_thread
    # Handle case where user passes host as first arg
    if isinstance(db, str):
        host = db
        db = None
    if _global_server_thread and _global_server_thread.is_alive():
        return _global_server_thread
    _global_server_thread = SyncServerThread(host=host, port=port, db=db)
    _global_server_thread.start()
    return _global_server_thread


def stop_sync_server():
    global _global_server_thread
    if _global_server_thread:
        _global_server_thread.stop()
        _global_server_thread = None


if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000
    print("=" * 60)
    print("  Al-Bonyan ERP - Local Wi-Fi Sync Server")
    print(f"  Local Machine IP : {local_ip}")
    print(f"  Mobile Web App   : http://{local_ip}:{port}/mobile")
    print(f"  API Docs         : http://{local_ip}:{port}/docs")
    print("=" * 60)
    app = create_sync_app()
    uvicorn.run(app, host="0.0.0.0", port=port)
