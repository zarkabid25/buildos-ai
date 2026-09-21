import math
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import InventoryTransactionType
from app.models.inventory_transaction import InventoryTransaction
from app.models.material import Material
from app.schemas.forecast import ConsumptionRate, MaterialAnomaly, MaterialForecast
from app.services.inventory_service import get_total_stock_on_hand

# "Consumption" counts only material actually leaving the business: plain
# stock-outs and project allocations. Transfers move stock between warehouses
# without reducing the company's total on-hand quantity, so they don't count.
_CONSUMPTION_TYPES = (InventoryTransactionType.STOCK_OUT, InventoryTransactionType.ALLOCATION)

# Below this lead time, a reorder recommendation is triggered.
DEFAULT_LEAD_TIME_DAYS = 7
# Recommended order quantity brings stock up to cover this many days of usage.
DEFAULT_REORDER_TARGET_DAYS = 30
# An anomaly is flagged when the last week's daily average consumption exceeds
# the prior baseline average by more than this multiple.
ANOMALY_THRESHOLD_MULTIPLIER = Decimal("1.5")


def _consumption_total(
    db: Session, company_id: uuid.UUID, material_id: uuid.UUID, start: datetime, end: datetime
) -> Decimal:
    total = (
        db.query(func.sum(InventoryTransaction.quantity))
        .filter(
            InventoryTransaction.company_id == company_id,
            InventoryTransaction.material_id == material_id,
            InventoryTransaction.transaction_type.in_(_CONSUMPTION_TYPES),
            InventoryTransaction.created_at >= start,
            InventoryTransaction.created_at < end,
        )
        .scalar()
    )
    return total or Decimal("0")


def get_consumption_rate(
    db: Session, company_id: uuid.UUID, material: Material, window_days: int = 30
) -> ConsumptionRate:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=window_days)
    total = _consumption_total(db, company_id, material.id, start, now)
    daily_avg = total / window_days

    return ConsumptionRate(
        material_id=material.id,
        material_name=material.name,
        unit=material.unit,
        daily_avg=daily_avg,
        weekly_avg=daily_avg * 7,
        monthly_avg=daily_avg * 30,
        window_days=window_days,
    )


def get_material_forecast(
    db: Session,
    company_id: uuid.UUID,
    material: Material,
    lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
    reorder_target_days: int = DEFAULT_REORDER_TARGET_DAYS,
) -> MaterialForecast:
    current_stock = get_total_stock_on_hand(db, company_id, material.id)
    rate = get_consumption_rate(db, company_id, material)

    # A flat 30-day trailing average reacts too slowly to a genuine consumption
    # spike (the same kind of spike detect_anomalies() flags) -- it would keep
    # predicting a comfortable stockout date for days after usage has clearly
    # accelerated. Use the more conservative (higher) of the last-7-days rate
    # and the 30-day rate so a real spike shows up in the forecast immediately,
    # not just in the separate anomaly list.
    now = datetime.now(timezone.utc)
    recent_total = _consumption_total(db, company_id, material.id, now - timedelta(days=7), now)
    recent_avg = recent_total / 7
    daily_avg = max(rate.daily_avg, recent_avg)

    if daily_avg <= 0:
        return MaterialForecast(
            material_id=material.id,
            material_name=material.name,
            unit=material.unit,
            current_stock=current_stock,
            daily_avg_usage=daily_avg,
            estimated_stockout_date=None,
            days_remaining=None,
            recommended_order_quantity=None,
            reason="No recorded consumption in the last 30 days, so a stockout date can't be estimated.",
        )

    days_remaining = int(current_stock / daily_avg) if current_stock > 0 else 0
    estimated_stockout_date = date.today() + timedelta(days=days_remaining)

    if days_remaining <= lead_time_days:
        target_stock = daily_avg * reorder_target_days
        shortfall = target_stock - current_stock
        recommended_qty = Decimal(math.ceil(shortfall)) if shortfall > 0 else Decimal("0")
        reason = (
            f"Estimated {days_remaining} day(s) of stock remain, at or below the "
            f"{lead_time_days}-day lead-time buffer. Ordering {recommended_qty} {material.unit} "
            f"covers {reorder_target_days} days at the current usage rate."
        )
    else:
        recommended_qty = None
        reason = (
            f"Estimated {days_remaining} day(s) of stock remain, above the "
            f"{lead_time_days}-day lead-time buffer. No reorder needed yet."
        )

    return MaterialForecast(
        material_id=material.id,
        material_name=material.name,
        unit=material.unit,
        current_stock=current_stock,
        daily_avg_usage=daily_avg,
        estimated_stockout_date=estimated_stockout_date,
        days_remaining=days_remaining,
        recommended_order_quantity=recommended_qty,
        reason=reason,
    )


def list_forecasts(db: Session, company_id: uuid.UUID) -> list[MaterialForecast]:
    materials = db.query(Material).filter(Material.company_id == company_id).all()
    return [get_material_forecast(db, company_id, m) for m in materials]


def detect_anomalies(db: Session, company_id: uuid.UUID) -> list[MaterialAnomaly]:
    materials = db.query(Material).filter(Material.company_id == company_id).all()
    now = datetime.now(timezone.utc)

    anomalies: list[MaterialAnomaly] = []
    for material in materials:
        recent_total = _consumption_total(db, company_id, material.id, now - timedelta(days=7), now)
        baseline_total = _consumption_total(
            db, company_id, material.id, now - timedelta(days=30), now - timedelta(days=7)
        )
        recent_avg = recent_total / 7
        baseline_avg = baseline_total / 23

        if baseline_avg <= 0 or recent_avg <= 0:
            continue

        change = recent_avg / baseline_avg
        if change >= ANOMALY_THRESHOLD_MULTIPLIER:
            change_percent = (change - 1) * 100
            anomalies.append(
                MaterialAnomaly(
                    material_id=material.id,
                    material_name=material.name,
                    unit=material.unit,
                    recent_daily_avg=recent_avg,
                    baseline_daily_avg=baseline_avg,
                    change_percent=change_percent,
                    message=(
                        f"Daily consumption over the last 7 days ({recent_avg:.1f} {material.unit}/day) "
                        f"is {change_percent:.0f}% above the prior baseline ({baseline_avg:.1f} {material.unit}/day)."
                    ),
                )
            )
    return anomalies
