# reports/__init__.py
from reports.ticket import generate_ticket
from reports.invoice import generate_invoice
from reports.stock_report import generate_stock_report

__all__ = ["generate_ticket", "generate_invoice", "generate_stock_report"]
