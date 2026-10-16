# -*- coding: utf-8 -*-
"""
Services Module for Al-Bonyan Iron & Cement ERP:
1. ExcelExporter: Exports any table, report, or account statement to a styled RTL .xlsx file.
2. WhatsAppService: Formats and sends reports, invoices, and account statements via WhatsApp API links (wa.me).
3. AIInvoiceReaderWorker: Background QThread using Google GenAI SDK (`google-genai` >= 2.25.0) and `gemini-3.8-flash`
   via `client.interactions.create` to extract structured JSON from uploaded PDF/Image invoices, with a rich demo mode fallback.
"""
import os
import json
import base64
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from PyQt6.QtCore import QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from config import EXPORTS_DIR, format_egp


class ExcelExporter:
    """Professional RTL Excel (.xlsx) exporter tailored for financial & warehouse reports."""

    @staticmethod
    def export_to_excel(
        parent: QWidget,
        report_title: str,
        headers: List[str],
        rows: List[List[Any]],
        summary_pairs: Optional[List[ tuple ]] = None,
        default_filename: str = "تقرير_البنيان"
    ) -> Optional[str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{default_filename}_{timestamp}.xlsx"
        initial_path = os.path.join(EXPORTS_DIR, safe_name)

        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "تصدير التقرير إلى ملف Excel",
            initial_path,
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return None

        if not file_path.endswith(".xlsx"):
            file_path += ".xlsx"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "التقرير المالي"
        ws.views.sheetView[0].rightToLeft = True

        # Styling definitions
        title_font = Font(name="Cairo", size=15, bold=True, color="FFFFFF")
        subtitle_font = Font(name="Cairo", size=10, italic=True, color="E2E8F0")
        header_font = Font(name="Cairo", size=11, bold=True, color="FFFFFF")
        data_font = Font(name="Cairo", size=11, bold=False, color="0F172A")
        summary_font = Font(name="Cairo", size=11, bold=True, color="0F172A")

        title_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        zebra_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        summary_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

        thin_side = Side(style="thin", color="CBD5E1")
        border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        col_count = max(len(headers), 4)
        last_col_letter = get_column_letter(col_count)

        # Row 1: Title Banner
        ws.merge_cells(f"A1:{last_col_letter}1")
        ws["A1"] = f"شركة البنيان لتجارة الحديد والأسمنت — {report_title}"
        ws["A1"].font = title_font
        ws["A1"].fill = title_fill
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 34

        # Row 2: Timestamp & Currency Banner
        ws.merge_cells(f"A2:{last_col_letter}2")
        ws["A2"] = f"تاريخ الاستخراج: {datetime.now().strftime('%Y-%m-%d %H:%M')} | العملة المعتمدة: الجنيه المصري (EGP)"
        ws["A2"].font = subtitle_font
        ws["A2"].fill = title_fill
        ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[2].height = 22

        # Row 4: Table Headers
        header_row_idx = 4
        ws.row_dimensions[header_row_idx].height = 28
        for col_idx, h_text in enumerate(headers, start=1):
            cell = ws.cell(row=header_row_idx, column=col_idx, value=str(h_text))
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border

        # Data Rows
        current_row = header_row_idx + 1
        for r_idx, row_values in enumerate(rows):
            ws.row_dimensions[current_row].height = 24
            row_fill = zebra_fill if r_idx % 2 == 1 else white_fill
            for col_idx, val in enumerate(row_values, start=1):
                cell = ws.cell(row=current_row, column=col_idx)
                if isinstance(val, (int, float)):
                    cell.value = val
                    cell.number_format = "#,##0.00"
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.value = str(val) if val is not None else ""
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.font = data_font
                cell.fill = row_fill
                cell.border = border
            current_row += 1

        # Summary Section if provided
        if summary_pairs:
            current_row += 1
            for label, val in summary_pairs:
                ws.row_dimensions[current_row].height = 25
                ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=max(1, col_count - 1))
                lbl_cell = ws.cell(row=current_row, column=1, value=str(label))
                lbl_cell.font = summary_font
                lbl_cell.fill = summary_fill
                lbl_cell.alignment = Alignment(horizontal="left", vertical="center")
                lbl_cell.border = border

                val_cell = ws.cell(row=current_row, column=col_count, value=val)
                val_cell.font = summary_font
                val_cell.fill = summary_fill
                if isinstance(val, (int, float)):
                    val_cell.number_format = "#,##0.00"
                val_cell.alignment = Alignment(horizontal="center", vertical="center")
                val_cell.border = border
                current_row += 1

        # Auto-fit columns
        for col_idx in range(1, col_count + 1):
            col_letter = get_column_letter(col_idx)
            max_len = 14
            for row_idx in range(header_row_idx, current_row):
                val = ws.cell(row=row_idx, column=col_idx).value
                if val is not None:
                    max_len = max(max_len, len(str(val)) + 5)
            ws.column_dimensions[col_letter].width = min(max_len, 45)

        wb.save(file_path)

        reply = QMessageBox.question(
            parent,
            "تم التصدير إلى Excel بنجاح",
            f"تم حفظ ملف الإكسل بنجاح في المسار:\n{file_path}\n\nهل ترغب في فتح الملف الآن؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

        return file_path


class WhatsAppService:
    """Formats messages and opens WhatsApp Web / Desktop App directly via wa.me standard links."""

    @staticmethod
    def clean_egypt_phone(phone: str) -> str:
        digits = "".join(ch for ch in str(phone) if ch.isdigit())
        if not digits:
            return ""
        if digits.startswith("00"):
            digits = digits[2:]
        if digits.startswith("01") and len(digits) == 11:
            digits = "2" + digits
        elif not digits.startswith("20") and len(digits) == 10:
            digits = "20" + digits
        return digits

    @staticmethod
    def send_whatsapp_message(phone: str, message_text: str):
        cleaned_phone = WhatsAppService.clean_egypt_phone(phone)
        encoded_text = urllib.parse.quote(message_text)
        if cleaned_phone:
            url = f"https://wa.me/{cleaned_phone}?text={encoded_text}"
        else:
            url = f"https://wa.me/?text={encoded_text}"
        QDesktopServices.openUrl(QUrl(url))

    @staticmethod
    def build_customer_statement_message(cust: Dict[str, Any], txs: List[Dict[str, Any]], company_name: str) -> str:
        lines = [
            f"*{company_name}*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📄 *كشف حساب عميل*",
            f"👤 السادة / *{cust.get('name', '')}*",
            f"🏷️ فئة التسعير: {cust.get('pricing_tier', '')}",
            f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d')}",
            "━━━━━━━━━━━━━━━━━━━━",
            "📐 *معادلة الرصيد: (إجمالي المشتريات - إجمالي المدفوعات)*",
            f"➕ إجمالي المشتريات / المسحوبات: *{format_egp(cust.get('total_debit', 0))}*",
            f"➖ إجمالي المدفوعات المسددة: *{format_egp(cust.get('total_credit', 0))}*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"💰 *صافي الرصيد الحالي المستحق: {format_egp(cust.get('current_balance', 0))}*",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
        if txs:
            lines.append("📌 *آخر الحركات المسجلة:*")
            for t in txs[-5:]:
                amt = t["debit"] if t["debit"] > 0 else t["credit"]
                lines.append(f"• {t['tx_date']} | {t['tx_type']} ({t['reference_no']}): {format_egp(amt)}")
        lines.append("\nشكراً لتعاملكم معنا.")
        return "\n".join(lines)

    @staticmethod
    def build_supplier_statement_message(sup: Dict[str, Any], txs: List[Dict[str, Any]], company_name: str) -> str:
        lines = [
            f"*{company_name}*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🏭 *كشف حساب ومطابقة رصيد مورد / مصنع*",
            f"السادة / *{sup.get('name', '')}* ({sup.get('factory_type', '')})",
            f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d')}",
            "━━━━━━━━━━━━━━━━━━━━",
            "📐 *معادلة الرصيد: (إجمالي التوريدات - إجمالي المدفوعات)*",
            f"➕ إجمالي المشتريات / التوريدات: *{format_egp(sup.get('total_credit', 0))}*",
            f"➖ إجمالي المدفوعات المسددة: *{format_egp(sup.get('total_debit', 0))}*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"💳 *صافي الرصيد الحالي المستحق لكم: {format_egp(sup.get('current_balance', 0))}*",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
        if txs:
            lines.append("📌 *آخر الحركات:*")
            for t in txs[-5:]:
                amt = t["credit"] if t["credit"] > 0 else t["debit"]
                lines.append(f"• {t['tx_date']} | {t['tx_type']} ({t['reference_no']}): {format_egp(amt)}")
        lines.append("\nمع خالص التحية — الإدارة المالية.")
        return "\n".join(lines)


class AIInvoiceReaderWorker(QThread):
    """
    Background worker that uses Google GenAI SDK (`google-genai`) via `client.interactions.create`
    with `gemini-3.8-flash` / `gemini-3.5-flash-lite` (substituting legacy `gemini-2.0-flash`)
    to extract structured invoice data from images or PDFs without freezing or hanging.
    """
    finished_success = pyqtSignal(dict)
    finished_error = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(self, file_path: str, api_key: str = "", demo_mode: bool = False):
        super().__init__()
        self.file_path = file_path
        self.api_key = api_key.strip() if api_key else os.environ.get("GEMINI_API_KEY", "").strip()
        self.demo_mode = demo_mode

    def _prepare_file_payload(self):
        """Read and optimize image/PDF payload so large camera photos upload in milliseconds."""
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext == ".pdf":
            with open(self.file_path, "rb") as f:
                file_bytes = f.read()
            return "document", "application/pdf", base64.b64encode(file_bytes).decode("utf-8")

        # Optimize images using QImage if oversized (> 1600px or > 1.5MB) to prevent upload stalls
        try:
            from PyQt6.QtGui import QImage
            from PyQt6.QtCore import QByteArray, QBuffer, QIODevice, Qt
            img = QImage(self.file_path)
            if not img.isNull():
                if img.width() > 1600 or img.height() > 1600:
                    img = img.scaled(
                        1600, 1600,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                ba = QByteArray()
                buf = QBuffer(ba)
                buf.open(QIODevice.OpenModeFlag.WriteOnly)
                img.save(buf, "JPEG", 85)
                buf.close()
                raw_bytes = bytes(ba)
                if raw_bytes:
                    return "image", "image/jpeg", base64.b64encode(raw_bytes).decode("utf-8")
        except Exception:
            pass

        with open(self.file_path, "rb") as f:
            file_bytes = f.read()
        if ext == ".png":
            mime_type = "image/png"
        elif ext == ".webp":
            mime_type = "image/webp"
        else:
            mime_type = "image/jpeg"
        return "image", mime_type, base64.b64encode(file_bytes).decode("utf-8")

    def run(self):
        try:
            if self.demo_mode or not self.api_key:
                self.status_changed.emit("⏳ جاري تشغيل المحاكاة الذكية للفاتورة...")
                self.msleep(600)
                sample_result = {
                    "invoice_type": "فاتورة مشتريات (مورد)",
                    "invoice_number": f"INV-{datetime.now().strftime('%m%d')}-884",
                    "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                    "party_name": "مجموعة حديد عز (Ezz Steel)",
                    "payment_method": "آجل / على الحساب (Credit)",
                    "items": [
                        {
                            "item_code": "IRN-EZZ-16",
                            "item_name": "حديد عز تسليح 16 مم (أطوال)",
                            "category": "حديد تسليح (Rebar)",
                            "unit": "طن (Ton)",
                            "quantity": 35.0,
                            "unit_price": 39750.0,
                            "total_price": 1391250.0
                        },
                        {
                            "item_code": "CEM-SWD-OPC",
                            "item_name": "أسمنت السويدي بورتلاندي عادي (رتبة 42.5)",
                            "category": "أسمنت بورتلاندي عادي (OPC)",
                            "unit": "طن (Ton)",
                            "quantity": 50.0,
                            "unit_price": 2680.0,
                            "total_price": 134000.0
                        }
                    ],
                    "subtotal": 1525250.0,
                    "discount": 0.0,
                    "tax_amount": 0.0,
                    "grand_total": 1525250.0,
                    "notes": "تم الاستخراج الذكي لبنود الفاتورة (حديد تسليح + أسمنت بورتلاندي) ومطابقة الأصناف."
                }
                self.finished_success.emit(sample_result)
                return

            if not os.path.exists(self.file_path):
                self.finished_error.emit("الملف المحدد غير موجود.")
                return

            self.status_changed.emit("⏳ جاري تجهيز وضغط ملف الفاتورة للإرسال السريع...")
            content_type, mime_type, b64_data = self._prepare_file_payload()

            from google import genai
            client = genai.Client(api_key=self.api_key)
            # CRITICAL FIX: Disable SDK internal exponential backoff retry on 429/5XX so UI never hangs!
            try:
                client.interactions.sdk_configuration.retry_config = None
            except Exception:
                pass

            invoice_schema = {
                "type": "object",
                "properties": {
                    "invoice_type": {
                        "type": "string",
                        "description": "نوع الفاتورة: 'فاتورة مشتريات (مورد)' أو 'فاتورة مبيعات (عميل)'"
                    },
                    "invoice_number": {"type": "string"},
                    "invoice_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "party_name": {"type": "string", "description": "اسم المورد أو العميل في الفاتورة"},
                    "payment_method": {"type": "string", "description": "طريقة الدفع مثل نقدي أو آجل أو تحويل بنكي"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item_code": {"type": "string"},
                                "item_name": {"type": "string"},
                                "category": {"type": "string"},
                                "unit": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit_price": {"type": "number"},
                                "total_price": {"type": "number"}
                            },
                            "required": ["item_name", "quantity", "unit_price", "total_price"]
                        }
                    },
                    "subtotal": {"type": "number"},
                    "discount": {"type": "number"},
                    "tax_amount": {"type": "number"},
                    "grand_total": {"type": "number"},
                    "notes": {"type": "string"}
                },
                "required": ["invoice_type", "party_name", "items", "grand_total"]
            }

            prompt = (
                "أنت محاسب خبير في شركة تجارة حديد وأسمنت في مصر. "
                "قم بقراءة هذه الفاتورة واستخراج كافة البيانات بدقة باللغة العربية بصيغة JSON: "
                "نوع الفاتورة (فاتورة مشتريات (مورد) أو فاتورة مبيعات (عميل))، رقم الفاتورة، التاريخ بصيغة YYYY-MM-DD، "
                "اسم المورد أو العميل، طريقة الدفع، وقائمة الأصناف (حديد تسليح، أسمنت، إلخ) مع الكميات بالطن أو الشيكارة "
                "وأسعار الوحدة بالجنيه المصري والإجماليات."
            )

            input_payload = [
                {
                    "type": content_type,
                    "data": b64_data,
                    "mime_type": mime_type
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]

            # Fast, non-blocking model chain: gemini-3.5-flash-lite & gemini-3.8-flash
            candidate_models = [
                "gemini-3.5-flash-lite",
                "gemini-3.8-flash",
                "gemini-3.1-flash-lite-preview",
            ]

            interaction = None
            used_model = candidate_models[0]
            last_err = None

            for model_name in candidate_models:
                try:
                    self.status_changed.emit(f"⏳ جاري تحليل الفاتورة عبر النموذج السريع ({model_name})...")
                    interaction = client.interactions.create(
                        model=model_name,
                        input=input_payload,
                        response_mime_type="application/json",
                        response_format=invoice_schema,
                        timeout=18,
                    )
                    used_model = model_name
                    break
                except Exception as err:
                    last_err = err
                    continue

            if interaction is None:
                raise RuntimeError(str(last_err) if last_err else "تعذر الاتصال بنموذج Gemini.")

            raw_text = getattr(interaction, "output_text", None) or ""
            if not raw_text and hasattr(interaction, "steps") and interaction.steps:
                for step in interaction.steps:
                    if getattr(step, "type", "") == "model_output" and getattr(step, "content", None):
                        for part in step.content:
                            txt = getattr(part, "text", None)
                            if txt:
                                raw_text += txt

            raw_text = raw_text.strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            parsed = json.loads(raw_text or "{}")
            if not parsed.get("notes"):
                parsed["notes"] = f"تم استخراج بيانات الفاتورة بنجاح عبر نموذج ({used_model})."
            self.finished_success.emit(parsed)

        except Exception as e:
            self.finished_error.emit(f"خطأ أثناء تحليل الفاتورة بالذكاء الاصطناعي:\n{str(e)}")

