from dataclasses import dataclass
from typing import List

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_config
from app.janice import appraise, AppraisalError

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


@dataclass
class AcceptedItem:
    name: str
    quantity: int
    unit_price: float
    subtotal: float


@dataclass
class RejectedItem:
    name: str
    reason: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    config = get_config()
    return templates.TemplateResponse(request, "index.html", {"config_pct": config.buyback_percentage})


@app.post("/appraise", response_class=HTMLResponse)
async def do_appraise(request: Request, items: str = Form(...)):
    config = get_config()

    if not items.strip():
        return templates.TemplateResponse(
            request, "index.html",
            {"error": "Please paste some items", "paste": items},
        )

    try:
        raw_items = await appraise(items)
    except AppraisalError:
        return templates.TemplateResponse(
            request, "index.html",
            {
                "error": "Price service unavailable, try again later",
                "paste": items,
            },
        )

    accepted: List[AcceptedItem] = []
    rejected: List[RejectedItem] = []

    for item in raw_items:
        if item.buy_price <= 0.0:
            rejected.append(RejectedItem(name=item.name, reason="not found"))
            continue

        if config.allowed_categories and (
            item.group_name not in config.allowed_categories
            and item.category_name not in config.allowed_categories
        ):
            cats = ", ".join(config.allowed_categories)
            rejected.append(
                RejectedItem(name=item.name, reason=f"not accepted — we only buy {cats}")
            )
            continue

        unit_price = item.buy_price * config.buyback_percentage
        accepted.append(
            AcceptedItem(
                name=item.name,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=unit_price * item.quantity,
            )
        )

    grand_total = sum(a.subtotal for a in accepted)

    return templates.TemplateResponse(
        request, "index.html",
        {
            "accepted": accepted,
            "rejected": rejected,
            "grand_total": grand_total,
            "paste": items,
            "config_pct": config.buyback_percentage,
        },
    )
