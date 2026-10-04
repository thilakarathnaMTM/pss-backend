from typing import List
from datetime import time
from app.models.machine import Machine
from app.models.tariff import Tariff
from app.services.optimizer import calculate_baseline_cost

def calculate_current_cost(
    machines: List[Machine],
    tariffs: List[Tariff],
    factory_start: time,
    factory_end: time,
) -> float:
    return calculate_baseline_cost(machines, tariffs, factory_start, factory_end)
