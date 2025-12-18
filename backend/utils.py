import psycopg2
import httpx
import os


# PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="ticketing_db",
        user="ticketing_user",
        password="mysecretpassword",
        port=5432,
    )


# SLA hours dictionary
SLA_HOURS_DICT = {
    "low": 72,
    "medium": 48,
    "high": 24,
    "critical": 1 / 60,  # 1 minute for testing
}

# TAV triggers
TAV_BASE_URL = os.getenv("TAV_BASE_URL", "http://localhost:5001")


async def trigger_tav_workflow(ticket_payload: dict) -> None:
    workflow_id = "31220e0d-1a92-40ae-8cbc-400f3ec1b469"
    url = f"{TAV_BASE_URL}/api/v1/workflows/{workflow_id}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


async def trigger_tav_workflow_updated(ticket_payload: dict) -> None:
    updated_workflow_id = "69e99f3d-d527-49ff-9210-e1759696cda2"
    url = f"{TAV_BASE_URL}/api/v1/workflows/{updated_workflow_id}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


async def trigger_tav_workflow_sla_breached(ticket_payload: dict) -> None:
    sla_breached_workflow_id = "004d3aaf-0914-4535-bc56-bd5fabc31dd5"
    url = f"{TAV_BASE_URL}/api/v1/workflows/{sla_breached_workflow_id}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


async def trigger_tav_workflow_pre_breach(ticket_payload: dict) -> None:
    pre_breach_workflow_id = "1d25d573-3569-496f-91c5-0ad1d756026e"
    url = f"{TAV_BASE_URL}/api/v1/workflows/{pre_breach_workflow_id}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()
