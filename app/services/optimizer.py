from datetime import time
from typing import List, Dict
import pulp
from app.models.machine import Machine
from app.models.tariff import Tariff

def time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute

def minutes_to_time(m: int) -> time:
    h = m // 60
    mi = m % 60
    if h >= 24:
        h = h % 24
    return time(h, mi)

def get_rate_at(minute: int, tariffs: List[Tariff]) -> float:
    for tariff in tariffs:
        start = time_to_minutes(tariff.start_time)
        end = time_to_minutes(tariff.end_time)
        if start < end:
            if start <= minute < end:
                return tariff.rate_per_kwh
        else:
            if minute >= start or minute < end:
                return tariff.rate_per_kwh
    return 47.0

def machine_power_kw(machine: Machine) -> float:
    return (machine.quantity * machine.power_w) / 1000.0

def cost_for_window(
    power_kw: float,
    start_m: int,
    required_slots: int,
    slot_minutes: int,
    tariffs: List[Tariff],
) -> float:
    cost = 0.0
    for i in range(required_slots):
        minute = start_m + i * slot_minutes
        rate = get_rate_at(minute, tariffs)
        cost += power_kw * (slot_minutes / 60.0) * rate
    return cost

def calculate_baseline_cost(
    machines: List[Machine],
    tariffs: List[Tariff],
    factory_start: time,
    factory_end: time,
    slot_minutes: int = 30,
) -> float:
    total = 0.0
    factory_start_m = time_to_minutes(factory_start)
    factory_end_m = time_to_minutes(factory_end)
    for machine in machines:
        power_kw = machine_power_kw(machine)
        required_slots = int(round(machine.required_hours * 60 / slot_minutes))
        if required_slots <= 0:
            continue
        start_m = max(time_to_minutes(machine.available_start), factory_start_m)
        end_limit = min(time_to_minutes(machine.available_end), factory_end_m)
        if start_m + required_slots * slot_minutes > end_limit:
            start_m = max(factory_start_m, end_limit - required_slots * slot_minutes)
        total += cost_for_window(power_kw, start_m, required_slots, slot_minutes, tariffs)
    return round(total, 2)

def optimize_schedule(
    machines: List[Machine],
    tariffs: List[Tariff],
    factory_start: time,
    factory_end: time,
    slot_minutes: int = 30
) -> List[Dict]:
    results = []
    factory_start_m = time_to_minutes(factory_start)
    factory_end_m = time_to_minutes(factory_end)

    for machine in machines:
        power_kw = machine_power_kw(machine)
        required_slots = int(round(machine.required_hours * 60 / slot_minutes))
        if required_slots <= 0:
            continue

        avail_start = max(time_to_minutes(machine.available_start), factory_start_m)
        avail_end = min(time_to_minutes(machine.available_end), factory_end_m)

        possible_starts = list(range(avail_start, avail_end - required_slots * slot_minutes + 1, slot_minutes))
        if not possible_starts:
            continue

        prob = pulp.LpProblem(f"opt_machine_{machine.id}", pulp.LpMinimize)
        start_vars = pulp.LpVariable.dicts("start", possible_starts, cat="Binary")
        prob += pulp.lpSum([start_vars[s] for s in possible_starts]) == 1

        cost_terms = []
        for s in possible_starts:
            cost = cost_for_window(power_kw, s, required_slots, slot_minutes, tariffs)
            cost_terms.append(cost * start_vars[s])
        prob += pulp.lpSum(cost_terms)

        status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=10))
        if pulp.LpStatus[status] != "Optimal":
            continue

        chosen = None
        for s in possible_starts:
            if pulp.value(start_vars[s]) is not None and pulp.value(start_vars[s]) > 0.5:
                chosen = s
                break
        if chosen is None:
            continue

        start_t = minutes_to_time(chosen)
        end_t = minutes_to_time(chosen + required_slots * slot_minutes)
        energy = round(power_kw * machine.required_hours, 2)
        cost = cost_for_window(power_kw, chosen, required_slots, slot_minutes, tariffs)
        baseline = cost_for_window(
            power_kw,
            max(time_to_minutes(machine.available_start), factory_start_m),
            required_slots,
            slot_minutes,
            tariffs,
        )

        results.append({
            "machine_id": machine.id,
            "machine_name": machine.name,
            "scheduled_start": start_t,
            "scheduled_end": end_t,
            "energy_kwh": energy,
            "cost": round(cost, 2),
            "total_power_kw": round(power_kw, 3),
            "required_hours": machine.required_hours,
            "saving": round(max(baseline - cost, 0), 2),
        })
    return results
