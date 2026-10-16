# -*- coding: utf-8 -*-
"""
Configuration and Constants for Al-Bonyan ERP (نظام البنيان للمحاسبة وتجارة الحديد والأسمنت)
Simplified & Intuitive Cash-In / Cash-Out & Balance Tracking Edition
"""
import os

APP_NAME = "نظام البنيان المحاسبي - لتجارة الحديد والأسمنت"
APP_VERSION = "3.0.0"
CURRENCY = "ج.م"
CURRENCY_NAME = "جنيه مصري (EGP)"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "iron_cement_erp.db")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)

# Iron & Cement Categories
ITEM_CATEGORIES = [
    "حديد تسليح (Rebar)",
    "حديد تجاري وقطاعات (Commercial Iron)",
    "أسمنت بورتلاندي عادي (OPC)",
    "أسمنت مقاوم للملوحة (SRC)",
    "أسمنت أبيض وتشطيبات (White Cement)",
    "جبس ومواد بناء إضافية"
]

# Units supported
ITEM_UNITS = [
    "طن (Ton)",
    "كيلوجرام (Kg)",
    "شيكارة 50 كجم (Bag)",
    "ربطة / طرد (Bundle)",
    "عدد / قطعة (Piece)"
]

# Pricing Tiers for Customers
PRICING_TIERS = [
    "تجزئة / مستهلك (Retail)",
    "نصف جملة / مقاول (Contractor)",
    "جملة / تاجر معتمد (Wholesale)",
    "مشاريع خاصة (VIP Projects)"
]

# Simplified Daily Transaction Flow Types (No complex Debit/Credit jargon)
FLOW_TYPES = [
    "وارد / قبض (إيراد أو تحصيل نقدية)",
    "صادر / صرف (مصروف أو سداد دفعة)",
    "معاملة آجلة (بيع أو شراء على الحساب)"
]

# Simplified Daily Journal / Transaction Categories
JOURNAL_CATEGORIES = [
    "مبيعات حديد وأسمنت",
    "تحصيل دفعة من عميل",
    "مشتريات وتوريدات مصانع",
    "سداد دفعة لمورد / مصنع",
    "مصروفات تشغيل ونولون شحن",
    "رواتب وأجور وسلف موظفين",
    "إيرادات أخرى متنوعة"
]

# Payment Methods / Safes in Egypt
PAYMENT_METHODS = [
    "نقدي بالخزينة (Cash)",
    "تحويل بنكي (Bank Transfer)",
    "إنستاباي (InstaPay)",
    "شيك بنكي (Cheque)",
    "آجل / على الحساب (Credit)",
    "محفظة إلكترونية (Vodafone Cash)"
]

def format_egp(amount: float, include_symbol: bool = True) -> str:
    """Format number as Egyptian Pound currency."""
    try:
        val = float(amount or 0.0)
    except (ValueError, TypeError):
        val = 0.0
    formatted = f"{val:,.2f}"
    return f"{formatted} {CURRENCY}" if include_symbol else formatted
