from app.crud.filters import get_active_filters
from app.models.filters import Filter
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenders import Tender
from app.core.logging_config import logger
from app.schemas.filters import FilterCreate
from typing import Any


async def apply_filters(tender_data: Tender, tender_id: str, db: AsyncSession) -> bool:
    active_filters = await get_active_filters(db, filter_type=tender_data.type)
    logger.info(f"Found {len(active_filters)} active filters for tender {tender_id}")
    if not active_filters:
        logger.info(f"No active filters found for tender {tender_id}, passing to next stage")
        return True

    tender_dict = {
        "external_id": tender_data.external_id,
        "title": tender_data.title,
        "notification_number": tender_data.notification_number,
        "notification_type": tender_data.notification_type,
        "organizer": tender_data.organizer,
        "initial_price": tender_data.initial_price,
        "currency": tender_data.currency,
        "application_deadline": tender_data.application_deadline,
        "etp_code": tender_data.etp_code,
        "etp_name": tender_data.etp_name,
        "etp_url": tender_data.etp_url,
        "kontur_link": tender_data.kontur_link,
        "publication_date": tender_data.publication_date,
        "last_modified": tender_data.last_modified,
        "selection_method": tender_data.selection_method,
        "smp": tender_data.smp,
        "state": tender_data.state,
    }

    logger.info(f"Applying filters to tender {tender_id}")
    for filter_obj in active_filters:
        logger.debug(f"Checking filter {filter_obj.id}: condition={filter_obj.condition}")
        if check_filter(filter_obj, tender_dict):
            logger.info(f"Tender {tender_id} passed filter {filter_obj.id}")
            return True
        else:
            logger.info(f"Tender {tender_id} failed filter {filter_obj.id}")
    logger.info(f"Tender {tender_id} did not pass any filters")
    return False


def get_nested_value(data: dict, field: str) -> Any:

    keys = field.split(".")
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def evaluate_condition(condition: dict, tender_data: dict) -> bool:
    # Рекурсивно оценивает условие с учётом AND, OR и операторов
    if "AND" in condition:
        return all(evaluate_condition(sub_cond, tender_data) for sub_cond in condition["AND"])
    if "OR" in condition:
        return any(evaluate_condition(sub_cond, tender_data) for sub_cond in condition["OR"])

    # Простое условие
    field = condition.get("field")
    op = condition.get("op")
    value = condition.get("value")

    if not all([field, op, value is not None]):
        logger.debug(f"Invalid condition format: {condition}")
        return False

    tender_value = get_nested_value(tender_data, field)
    if tender_value is None:
        logger.debug(f"Field {field} not found in tender data")
        return False

    try:
        # Обработка операторов
        if op == "=":
            return tender_value == value
        elif op == "!=":
            return tender_value != value
        elif op == ">":
            return tender_value > value
        elif op == "<":
            return tender_value < value
        elif op == ">=":
            return tender_value >= value
        elif op == "<=":
            return tender_value <= value
        elif op == "contains":
            if isinstance(tender_value, str) and isinstance(value, str):
                return value.lower() in tender_value.lower()
            return False
        else:
            logger.debug(f"Unknown operator {op} in condition")
            return False
    except TypeError as e:
        logger.debug(f"Type error in condition {condition}: {str(e)}")
        return False


def check_filter(filter_obj: Filter, tender_data: dict) -> bool:

    if not filter_obj.condition:
        logger.debug(f"Filter {filter_obj.id} has no condition, passing")
        return True

    try:
        condition = json.loads(filter_obj.condition)
        logger.debug(f"Filter {filter_obj.id} condition: {condition}")
        return evaluate_condition(condition, tender_data)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid filter condition JSON for filter {filter_obj.id}: {str(e)}")
        return False


async def create_new_filter(filter_data: FilterCreate, db: AsyncSession) -> Filter:
    db_filter = Filter(**filter_data.dict())
    db.add(db_filter)
    await db.commit()
    await db.refresh(db_filter)
    logger.info(f"Created new filter with ID {db_filter.id}")
    return db_filter