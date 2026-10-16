# -*- coding: utf-8 -*-
"""
API Client & Data Sync Layer for Al-Bonyan ERP Mobile App.
Supports:
1. HTTP REST connection to desktop server (e.g., http://192.168.1.15:8000) over local Wi-Fi.
2. Direct DatabaseManager / SQLite access when running locally or offline with local DB.
3. Persistent configuration storage (server IP, port, mode).
"""
import os
import json
import sqlite3
import requests
from typing import Dict, Any, List, Optional

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "mobile_config.json")
DEFAULT_SERVER_URL = "http://127.0.0.1:8000"
FALLBACK_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "iron_cement_erp.db"))

_has_db_manager = False
try:
    from database import DatabaseManager
    _has_db_manager = True
except Exception:
    _has_db_manager = False


class MobileDataClient:
    def __init__(self):
        self.server_url = DEFAULT_SERVER_URL
        self.db_path = FALLBACK_DB_PATH
        self.mode = "server"  # 'server' or 'sqlite'
        self.timeout = 5
        self._local_db_instance = None
        self.session = requests.Session()
        self.session.trust_env = False
        self.load_config()

    def _get_local_db(self):
        if _has_db_manager and os.path.exists(self.db_path):
            if not self._local_db_instance or getattr(self._local_db_instance, "db_path", None) != self.db_path:
                try:
                    self._local_db_instance = DatabaseManager(self.db_path)
                except Exception as e:
                    print(f"Error initializing local DatabaseManager: {e}")
            return self._local_db_instance
        return None

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.server_url = cfg.get("server_url", DEFAULT_SERVER_URL)
                    self.db_path = cfg.get("db_path", FALLBACK_DB_PATH)
                    self.mode = cfg.get("mode", "server")
            except Exception as e:
                print(f"Error loading mobile config: {e}")

    def save_config(self, server_url: str, db_path: Optional[str] = None, mode: Optional[str] = None):
        self.server_url = server_url.rstrip("/")
        if db_path:
            self.db_path = db_path
        if mode:
            self.mode = mode
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "server_url": self.server_url,
                    "db_path": self.db_path,
                    "mode": self.mode
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving mobile config: {e}")

    def _parse_list(self, data: Any, key: Optional[str] = None) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if key and key in data and isinstance(data[key], list):
                return data[key]
            for k in ["items", "entries", "customers", "suppliers", "data"]:
                if k in data and isinstance(data[k], list):
                    return data[k]
        return []

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to the desktop sync server."""
        try:
            r = self.session.get(f"{self.server_url}/api/ping", timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                return {"success": True, "message": "متصل بنجاح بخادم سطح المكتب", "data": data}
            return {"success": False, "message": f"خطأ في الاستجابة: كود {r.status_code}"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "تعذر الاتصال بالخادم. تأكد من تشغيل البرنامج وتطابق شبكة الواي فاي."}
        except requests.exceptions.Timeout:
            return {"success": False, "message": "انتهت مهلة الاتصال بالخادم."}
        except Exception as e:
            return {"success": False, "message": f"خطأ في الاتصال: {str(e)}"}

    # =========================================================================
    # Dashboard KPIs
    # =========================================================================
    def get_dashboard(self) -> Dict[str, Any]:
        if self.mode == "server":
            try:
                r = self.session.get(f"{self.server_url}/api/dashboard", timeout=self.timeout)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                print(f"Server fetch failed, trying local DB fallback: {e}")

        # Local DB Fallback
        ldb = self._get_local_db()
        if ldb:
            try:
                stats = ldb.get_dashboard_summary()
                recents = ldb.get_journal_entries()[:10]
                return {
                    "success": True,
                    "kpis": {
                        "total_cash_in": stats.get("total_cash_in", 0),
                        "total_cash_out": stats.get("total_cash_out", 0),
                        "net_cash": stats.get("net_cash", 0),
                        "inventory_valuation": stats.get("cost_valuation", 0),
                        "customers_balance": stats.get("total_receivables", 0),
                        "suppliers_balance": stats.get("total_payables", 0)
                    },
                    "recent_transactions": recents
                }
            except Exception as e:
                print(f"Local DB get_dashboard failed: {e}")

        return {
            "success": False,
            "error": "تعذر الاتصال بالخادم ولا توجد قاعدة بيانات محلية",
            "kpis": {"total_cash_in": 0, "total_cash_out": 0, "net_cash": 0, "inventory_valuation": 0, "customers_balance": 0, "suppliers_balance": 0},
            "recent_transactions": []
        }

    # =========================================================================
    # Journal Entries
    # =========================================================================
    def get_journal_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self.mode == "server":
            try:
                r = self.session.get(f"{self.server_url}/api/journal", timeout=self.timeout)
                if r.status_code == 200:
                    return self._parse_list(r.json(), "entries")[:limit]
            except Exception as e:
                print(f"Server get_journal failed: {e}")

        ldb = self._get_local_db()
        if ldb:
            try:
                return ldb.get_journal_entries()[:limit]
            except Exception as e:
                print(f"Local get_journal failed: {e}")
        return []

    def add_journal_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        if self.mode == "server":
            try:
                r = self.session.post(f"{self.server_url}/api/journal", json=entry, timeout=self.timeout)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                return {"success": False, "message": f"فشل الإرسال للخادم: {str(e)}"}

        ldb = self._get_local_db()
        if ldb:
            try:
                amt = float(entry.get("amount", 0.0))
                e_type = entry.get("entry_type", "sale")
                if e_type in ('sale', 'receipt', 'cust_pay'):
                    cash_in, cash_out = amt, 0.0
                    flow = "وارد / قبض (إيراد أو تحصيل نقدية)"
                else:
                    cash_in, cash_out = 0.0, amt
                    flow = "صادر / صرف (مشتريات أو مصروفات)"

                payload = {
                    "entry_no": ldb.get_next_journal_no(),
                    "entry_date": entry.get("entry_date"),
                    "category": entry.get("category", "عام"),
                    "flow_type": flow,
                    "safe_name": "الخزينة الرئيسية",
                    "description": entry.get("description", "حركة من تطبيق الهاتف"),
                    "cash_in": cash_in,
                    "cash_out": cash_out,
                    "payment_method": "نقدي بالخزينة (Cash)" if entry.get("payment_method") == "cash" else "تحويل بنكي / إلكتروني",
                    "party_name": entry.get("party_name", ""),
                    "notes": entry.get("created_by", "تطبيق الهاتف الذكي")
                }
                new_id = ldb.add_journal_entry(payload)
                return {"success": True, "message": "تم الحفظ محلياً في قاعدة البيانات", "entry_id": new_id}
            except Exception as e:
                return {"success": False, "message": f"خطأ محلي: {str(e)}"}

        return {"success": False, "message": "تعذر الحفظ (لا يوجد اتصال ولا قاعدة بيانات محلية)"}

    # =========================================================================
    # Inventory
    # =========================================================================
    def get_inventory(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.mode == "server":
            try:
                url = f"{self.server_url}/api/inventory"
                if category:
                    url += f"?category={category}"
                r = self.session.get(url, timeout=self.timeout)
                if r.status_code == 200:
                    return self._parse_list(r.json(), "items")
            except Exception as e:
                print(f"Server get_inventory failed: {e}")

        ldb = self._get_local_db()
        if ldb:
            try:
                return ldb.get_items(category=category or "")
            except Exception as e:
                print(f"Local get_inventory failed: {e}")
        return []

    # =========================================================================
    # Customers
    # =========================================================================
    def get_customers(self) -> List[Dict[str, Any]]:
        if self.mode == "server":
            try:
                r = self.session.get(f"{self.server_url}/api/customers", timeout=self.timeout)
                if r.status_code == 200:
                    return self._parse_list(r.json(), "customers")
            except Exception as e:
                print(f"Server get_customers failed: {e}")

        ldb = self._get_local_db()
        if ldb:
            try:
                return ldb.get_all_customers_with_balances()
            except Exception as e:
                print(f"Local get_customers failed: {e}")
        return []

    # =========================================================================
    # Suppliers
    # =========================================================================
    def get_suppliers(self) -> List[Dict[str, Any]]:
        if self.mode == "server":
            try:
                r = self.session.get(f"{self.server_url}/api/suppliers", timeout=self.timeout)
                if r.status_code == 200:
                    return self._parse_list(r.json(), "suppliers")
            except Exception as e:
                print(f"Server get_suppliers failed: {e}")

        ldb = self._get_local_db()
        if ldb:
            try:
                return ldb.get_all_suppliers_with_balances()
            except Exception as e:
                print(f"Local get_suppliers failed: {e}")
        return []
