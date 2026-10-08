from datetime import time
from typing import List, Dict, Optional, Tuple
import pulp
from app.models.machine import Machine
from app.models.tariff import Tariff

SLOT_MINUTES = 30
DEFAULT_RATE = 47.0  # used only if no tariff period covers a minute

def time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute

def minutes_to_time(m: int) -> time:
    return time((m // 60) % 24, m % 60)

def get_rate_at(minute: int, tariffs: List[Tariff]) -> float:
    minute = minute % 1440
    for tariff in tariffs:
        start = time_to_minutes(tariff.start_time)
        end = time_to_minutes(tariff.end_time)
        if start < end:
            if start <= minute < end:
                return tariff.rate_per_kwh
        else:  # period wraps past midnight (e.g. 22:30 -> 05:30)
            if minute >= start or minute < end:
                return tariff.rate_per_kwh
    return DEFAULT_RATE

def machine_power_kw(machine: Machine) -> float:
    return (machine.quantity * machine.power_w) / 1000.0

def cost_for_window(
    power_kw: float,
    start_m: int,
    required_slots: int,
    slot_minutes: int,
    tariffs: List[Tariff],
) -> float:
    """cost = sum over slots of (kW x slot hours x rate at that slot)"""
    cost = 0.0
    for i in range(required_slots):
        rate = get_rate_at(start_m + i * slot_minutes, tariffs)
        cost += power_kw * (slot_minutes / 60.0) * rate
    return cost

def feasible_starts(
    machine: Machine,
    factory_start: time,
    factory_end: time,
    slot_minutes: int = SLOT_MINUTES,
) -> Tuple[int, List[int]]:
    """Return (required_slots, every legal start minute inside machine window AND factory hours)."""
    required_slots = int(round(machine.required_hours * 60 / slot_minutes))
    if required_slots <= 0:
        return 0, []
    lo = max(time_to_minutes(machine.available_start), time_to_minutes(factory_start))
    hi = min(time_to_minutes(machine.available_end), time_to_minutes(factory_end))
    return required_slots, list(range(lo, hi - required_slots * slot_minutes + 1, slot_minutes))

def baseline_start(machine: Machine, starts: List[int]) -> int:
    """The "before optimization" start: the machine's usual start time (snapped to the nearest legal start),
    or the earliest legal start when no usual time is recorded."""
    usual = getattr(machine, "usual_start", None)
    if usual is None:
        return starts[0]
    u = time_to_minutes(usual)
    return min(starts, key=lambda s: (abs(s - u), s))

def machine_baseline_cost(
    machine: Machine,
    tariffs: List[Tariff],
    factory_start: time,
    factory_end: time,
    slot_minutes: int = SLOT_MINUTES,
) -> Optional[float]:
    """Cost at the machine's usual (un-optimized) start time (None if it cannot be scheduled)."""
    required_slots, starts = feasible_starts(machine, factory_start, factory_end, slot_minutes)
    if not starts:
        return None
    return cost_for_window(machine_power_kw(machine), baseline_start(machine, starts), required_slots, slot_minutes, tariffs)

def calculate_baseline_cost(
    machines: List[Machine],
    tariffs: List[Tariff],
    factory_start: time,
    factory_end: time,
    slot_minutes: int = SLOT_MINUTES,
) -> float:
    # Machines that cannot be scheduled are excluded, same as in optimize_schedule,
    # so the two totals are always comparable.
    total = 0.0
    for machine in machines:
        cost = machine_baseline_cost(machine, tariffs, factory_start, factory_end, slot_minutes)
        if cost is not None:
            total += cost
    return round(total, 2)

def optimize_schedule(
    machines: List[Machine],
    tariffs: List[Tariff],
    factory_start: time,
    factory_end: time,
    slot_minutes: int = SLOT_MINUTES,
    use_milp: bool = True,
) -> List[Dict]:
    """use_milp=False picks the same start by direct comparison (identical result, much faster).
    It is used for the 12-month projections, which would otherwise start dozens of CBC solver processes."""
    results = []
    for machine in machines:
        power_kw = machine_power_kw(machine)
        required_slots, starts = feasible_starts(machine, factory_start, factory_end, slot_minutes)
        if not starts:
            continue

        costs = {s: cost_for_window(power_kw, s, required_slots, slot_minutes, tariffs) for s in starts}

        if not use_milp:
            chosen = min(starts, key=lambda s: (round(costs[s], 6), s))  # cheapest, earliest on ties
            results.append(_result(machine, power_kw, chosen, costs, starts, required_slots, slot_minutes))
            continue

        # Binary choice: exactly one start time per machine, minimise its cost.
        # The tiny 1e-6 * start term breaks ties in favour of the earlier start.
        prob = pulp.LpProblem(f"opt_machine_{machine.id}", pulp.LpMinimize)
        x = pulp.LpVariable.dicts("start", starts, cat="Binary")
        prob += pulp.lpSum((costs[s] + 1e-6 * s) * x[s] for s in starts)
        prob += pulp.lpSum(x[s] for s in starts) == 1
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=10))
        if pulp.LpStatus[status] != "Optimal":
            continue

        chosen = next((s for s in starts if (pulp.value(x[s]) or 0) > 0.5), None)
        if chosen is None:
            continue

        results.append(_result(machine, power_kw, chosen, costs, starts, required_slots, slot_minutes))
    return results


def _result(machine, power_kw, chosen, costs, starts, required_slots, slot_minutes) -> Dict:
    """Shape one machine's result; saving is measured against its usual (un-optimized) start."""
    cost = costs[chosen]
    baseline = costs[baseline_start(machine, starts)]
    return {
        "machine_id": machine.id,
        "machine_name": machine.name,
        "scheduled_start": minutes_to_time(chosen),
        "scheduled_end": minutes_to_time(chosen + required_slots * slot_minutes),
        "energy_kwh": round(power_kw * required_slots * slot_minutes / 60.0, 2),
        "cost": round(cost, 2),
        "total_power_kw": round(power_kw, 3),
        "required_hours": machine.required_hours,
        "saving": round(max(baseline - cost, 0), 2),
    }
