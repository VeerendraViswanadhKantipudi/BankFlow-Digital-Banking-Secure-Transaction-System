"""
Statement service — generates PDF and CSV account statements.

PDF generation uses reportlab (no system-level deps, works on Render out-of-box).
All methods are pure functions returning bytes/strings; no Flask context needed.
"""
import csv
import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.models.domain import (
    Account, Transaction, LedgerEntry, LedgerEntryType, User
)
from app.core.exceptions import ResourceNotFoundError, ForbiddenError


# ─── Query helpers ────────────────────────────────────────────────────────────

def _get_account_or_raise(db_session: Session, account_id: int, user_id: int, is_admin: bool) -> Account:
    account = db_session.get(Account, account_id)
    if not account:
        raise ResourceNotFoundError(f"Account {account_id} not found.")
    if not is_admin and account.user_id != user_id:
        raise ForbiddenError("You do not have access to this account's statements.")
    return account


def _get_transactions(
    db_session: Session,
    account_id: int,
    from_date: Optional[datetime],
    to_date: Optional[datetime]
):
    query = db_session.query(Transaction).filter(
        or_(
            Transaction.sender_account_id == account_id,
            Transaction.receiver_account_id == account_id,
        )
    )
    if from_date:
        query = query.filter(Transaction.created_at >= from_date)
    if to_date:
        query = query.filter(Transaction.created_at <= to_date)
    return query.order_by(Transaction.created_at.asc()).all()


def _tx_direction(tx: Transaction, account_id: int) -> str:
    return "DEBIT" if tx.sender_account_id == account_id else "CREDIT"


# ─── CSV Generator ────────────────────────────────────────────────────────────

def generate_csv_statement(
    db_session: Session,
    user_id: int,
    account_id: int,
    is_admin: bool,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> bytes:
    """
    Returns UTF-8 encoded CSV bytes of all transactions for the account
    within the optional date range.
    """
    account = _get_account_or_raise(db_session, account_id, user_id, is_admin)
    transactions = _get_transactions(db_session, account_id, from_date, to_date)

    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow([
        "Transaction ID", "Date (UTC)", "Type", "Counter-Party Account",
        "Amount", "Status", "Idempotency Key"
    ])

    for tx in transactions:
        direction = _tx_direction(tx, account_id)
        counter_party = tx.receiver_account_id if direction == "DEBIT" else tx.sender_account_id
        writer.writerow([
            tx.transaction_id,
            tx.created_at.strftime("%Y-%m-%d %H:%M:%S") if tx.created_at else "",
            direction,
            counter_party,
            str(tx.amount),
            tx.status.value if hasattr(tx.status, "value") else tx.status,
            tx.idempotency_key or "",
        ])

    return buf.getvalue().encode("utf-8")


# ─── PDF Generator ────────────────────────────────────────────────────────────

def generate_pdf_statement(
    db_session: Session,
    user_id: int,
    account_id: int,
    is_admin: bool,
    bank_name: str = "BankFlow",
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> bytes:
    """
    Returns PDF bytes of a formatted account statement.
    Uses reportlab — no system library dependencies.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    account = _get_account_or_raise(db_session, account_id, user_id, is_admin)
    owner = db_session.get(User, account.user_id)
    transactions = _get_transactions(db_session, account_id, from_date, to_date)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()

    BRAND_BLUE = colors.HexColor("#2563eb")
    LIGHT_GREY = colors.HexColor("#f1f5f9")
    DARK_TEXT = colors.HexColor("#1e293b")
    MUTED_TEXT = colors.HexColor("#64748b")

    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontSize=22, textColor=BRAND_BLUE, spaceAfter=4,
        fontName="Helvetica-Bold"
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=MUTED_TEXT, spaceAfter=2
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=9, textColor=DARK_TEXT
    )

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(bank_name, title_style))
    story.append(Paragraph("Account Statement", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceAfter=8))

    # ── Account meta ──────────────────────────────────────────────────────────
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    date_range = "All time"
    if from_date and to_date:
        date_range = f"{from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
    elif from_date:
        date_range = f"From {from_date.strftime('%Y-%m-%d')}"
    elif to_date:
        date_range = f"Up to {to_date.strftime('%Y-%m-%d')}"

    meta_data = [
        ["Account Holder:", owner.full_name if owner else "—"],
        ["Account Number:", account.account_number],
        ["Account ID:", str(account.account_id)],
        ["Current Balance:", f"{account.balance}"],
        ["Statement Period:", date_range],
        ["Generated:", generated_at],
    ]
    meta_table = Table(meta_data, colWidths=[45*mm, 120*mm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED_TEXT),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK_TEXT),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8*mm))

    # ── Transaction table ─────────────────────────────────────────────────────
    if not transactions:
        story.append(Paragraph("No transactions found for the selected period.", body_style))
    else:
        headers = ["#", "Date (UTC)", "Type", "Counter-Party Acct", "Amount", "Status"]
        rows = [headers]
        total_debits = Decimal("0.00")
        total_credits = Decimal("0.00")

        for tx in transactions:
            direction = _tx_direction(tx, account_id)
            counter = tx.receiver_account_id if direction == "DEBIT" else tx.sender_account_id
            amt = Decimal(str(tx.amount))
            if direction == "DEBIT":
                total_debits += amt
            else:
                total_credits += amt
            rows.append([
                str(tx.transaction_id),
                tx.created_at.strftime("%Y-%m-%d %H:%M") if tx.created_at else "",
                direction,
                str(counter),
                f"{amt:,.2f}",
                tx.status.value if hasattr(tx.status, "value") else str(tx.status),
            ])

        col_widths = [15*mm, 35*mm, 20*mm, 40*mm, 28*mm, 28*mm]
        tx_table = Table(rows, colWidths=col_widths, repeatRows=1)
        tx_table.setStyle(TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            # Data rows
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TEXTCOLOR", (0, 1), (-1, -1), DARK_TEXT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("ALIGN", (4, 1), (4, -1), "RIGHT"),  # Amount column right-aligned
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tx_table)
        story.append(Spacer(1, 6*mm))

        # ── Summary row ───────────────────────────────────────────────────────
        summary_data = [
            ["Total Credits:", f"+{total_credits:,.2f}"],
            ["Total Debits:", f"-{total_debits:,.2f}"],
            ["Net:", f"{(total_credits - total_debits):,.2f}"],
        ]
        summary_table = Table(summary_data, colWidths=[40*mm, 30*mm])
        summary_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("TEXTCOLOR", (0, 0), (-1, -1), DARK_TEXT),
        ]))
        story.append(summary_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MUTED_TEXT))
    story.append(Paragraph(
        f"This statement is computer-generated by {bank_name}. "
        "Contact your bank branch for queries.",
        ParagraphStyle("Footer", parent=styles["Normal"],
                       fontSize=7, textColor=MUTED_TEXT, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()


# ─── Single Transaction Receipt ───────────────────────────────────────────────

def generate_pdf_receipt(
    db_session: Session,
    user_id: int,
    transaction_id: int,
    is_admin: bool,
    bank_name: str = "BankFlow",
) -> bytes:
    """
    Returns a PDF receipt for a single transaction.
    Validates the requesting user owns one of the participating accounts.
    """
    from reportlab.lib.pagesizes import A5
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    tx = db_session.get(Transaction, transaction_id)
    if not tx:
        raise ResourceNotFoundError(f"Transaction {transaction_id} not found.")

    # Ownership check
    user_accounts = Account.query.filter_by(user_id=user_id).all()
    user_account_ids = {a.account_id for a in user_accounts}
    if not is_admin and not (
        tx.sender_account_id in user_account_ids or
        tx.receiver_account_id in user_account_ids
    ):
        raise ForbiddenError("You do not have access to this transaction.")

    BRAND_BLUE = colors.HexColor("#2563eb")
    MUTED_TEXT = colors.HexColor("#64748b")
    DARK_TEXT = colors.HexColor("#1e293b")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A5,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph(bank_name, ParagraphStyle(
        "T", parent=styles["Heading1"], fontSize=18, textColor=BRAND_BLUE,
        spaceAfter=2, fontName="Helvetica-Bold", alignment=TA_CENTER
    )))
    story.append(Paragraph("Transaction Receipt", ParagraphStyle(
        "Sub", parent=styles["Normal"], fontSize=10, textColor=MUTED_TEXT,
        spaceAfter=4, alignment=TA_CENTER
    )))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceAfter=6))

    rows = [
        ["Transaction ID:", str(tx.transaction_id)],
        ["Status:", tx.status.value if hasattr(tx.status, "value") else str(tx.status)],
        ["Amount:", f"{tx.amount}"],
        ["From Account:", str(tx.sender_account_id)],
        ["To Account:", str(tx.receiver_account_id)],
        ["Date (UTC):", tx.created_at.strftime("%Y-%m-%d %H:%M:%S") if tx.created_at else "—"],
    ]
    if tx.idempotency_key:
        rows.append(["Idempotency Key:", tx.idempotency_key])

    t = Table(rows, colWidths=[45*mm, 75*mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED_TEXT),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK_TEXT),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MUTED_TEXT))
    story.append(Paragraph(
        f"Generated by {bank_name} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        ParagraphStyle("F", parent=styles["Normal"], fontSize=7,
                       textColor=MUTED_TEXT, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()

