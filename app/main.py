import os
from dataclasses import dataclass
from typing import List

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_config
from app.janice import appraise, AppraisalError

app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


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


def _base_context(request: Request, config) -> dict:
    return {
        "config_pct": config.buyback_percentage,
        "allowed_categories": config.allowed_categories,
        "fixed_price_items": config.fixed_price_display,
        "og_image": str(request.url_for("static", path="laboon.jpg")),
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    config = get_config()
    return templates.TemplateResponse(request, "index.html", _base_context(request, config))


@app.post("/appraise", response_class=HTMLResponse)
async def do_appraise(request: Request, items: str = Form(...)):
    config = get_config()

    if not items.strip():
        return templates.TemplateResponse(
            request, "index.html",
            {
                **_base_context(request, config),
                "error": "Please paste some items",
                "paste": items,
            },
        )

    try:
        raw_items = await appraise(items)
    except AppraisalError:
        return templates.TemplateResponse(
            request, "index.html",
            {
                **_base_context(request, config),
                "error": "Price service unavailable, try again later",
                "paste": items,
            },
        )

    accepted: List[AcceptedItem] = []
    rejected: List[RejectedItem] = []

    for item in raw_items:
        fixed_price = config.fixed_prices.get(item.name.lower())

        if fixed_price is None:
            if item.buy_price <= 0.0:
                rejected.append(RejectedItem(name=item.name, reason="not found"))
                continue

            if not any(c in (item.group_name, item.category_name) for c in config.allowed_categories):
                rejected.append(RejectedItem(name=item.name, reason="category not accepted"))
                continue

        unit_price = fixed_price if fixed_price is not None else item.buy_price * config.buyback_percentage
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
            **_base_context(request, config),
            "accepted": accepted,
            "rejected": rejected,
            "grand_total": grand_total,
            "paste": items,
        },
    )
