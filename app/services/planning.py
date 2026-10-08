import calendar
from datetime import time, date
from typing import List, Dict
from app.models.factory import Factory
from app.models.machine import Machine
from app.models.tariff import Tariff
from app.models.planning import MonthlyProfile
from app.services.optimizer import optimize_schedule, calculate_baseline_cost, time_to_minutes, minutes_to_time

# Approximate Sri Lankan public / Poya holidays that fall on working days, per month.
HOLIDAYS_PER_MONTH = {1: 2, 2: 2, 3: 1, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1, 10: 2, 11: 1, 12: 2}
# Garment export season: orders peak before the Western holiday season, slow after New Year and in April.
SEASON_BY_MONTH = {1: "Low", 4: "Low", 8: "Peak", 9: "Peak", 10: "Peak", 11: "Peak"}
LOW_SEASON_HOURS_CUT = 120  # minutes shorter per day in low season


def productive_hours(start: time, end: time) -> float:
    """Productive hours per day = the factory's operating hours (start to end)."""
    return max(time_to_minutes(end) - time_to_minutes(start), 0) / 60.0


def working_days_in(year: int, month: int) -> int:
    """Monday-Saturday days in the month minus the usual holidays."""
    days = calendar.monthrange(year, month)[1]
    mon_sat = sum(1 for d in range(1, days + 1) if calendar.weekday(year, month, d) != calendar.SUNDAY)
    return mon_sat - HOLIDAYS_PER_MONTH[month]


def default_profiles(factory: Factory, year: int) -> List[MonthlyProfile]:
    start = time_to_minutes(factory.start_time)
    end = time_to_minutes(factory.end_time)
    profiles = []
    for month in range(1, 13):
        season = SEASON_BY_MONTH.get(month, "Normal")
        month_end = max(end - LOW_SEASON_HOURS_CUT, start + 8 * 60) if season == "Low" else end
        profiles.append(MonthlyProfile(
            factory_id=factory.id, year=year, month=month, season=season,
            working_days=working_days_in(year, month),
            start_time=factory.start_time, end_time=minutes_to_time(min(month_end, end)),
            inactive_machine_ids="",
            optimized=year >= date.today().year,  # past years: before the app was in use
        ))
    return profiles


def inactive_ids(profile: MonthlyProfile) -> set:
    return {int(x) for x in profile.inactive_machine_ids.split(",") if x.strip().isdigit()}


def compute_profile(profile: MonthlyProfile, machines: List[Machine], tariffs: List[Tariff]) -> Dict:
    """Optimize one typical day of the month with its hours and active machines, then scale by working days."""
    off = inactive_ids(profile)
    active = [m for m in machines if m.id not in off]
    hours = productive_hours(profile.start_time, profile.end_time)

    schedule = optimize_schedule(active, tariffs, profile.start_time, profile.end_time, use_milp=False)
    scheduled = {s["machine_id"] for s in schedule}
    daily_cost = round(sum(s["cost"] for s in schedule), 2)
    daily_kwh = round(sum(s["energy_kwh"] for s in schedule), 2)
    daily_base = calculate_baseline_cost(active, tariffs, profile.start_time, profile.end_time)
    days = profile.working_days
    used = bool(profile.optimized)
    day_saving = max(daily_base - daily_cost, 0)
    day_bill = daily_cost if used else daily_base  # without the app the factory pays for its usual schedule

    return {
        "id": profile.id,
        "year": profile.year,
        "month": profile.month,
        "season": profile.season,
        "optimized": used,
        "working_days": days,
        "start_time": profile.start_time,
        "end_time": profile.end_time,
        "inactive_machine_ids": sorted(off & {m.id for m in machines}),
        "hours_per_day": round(hours, 2),
        "active_machines": len(active),
        "skipped_machines": [m.name for m in active if m.id not in scheduled],
        "daily_kwh": daily_kwh,
        "daily_cost": round(day_bill, 2),
        "monthly_kwh": round(daily_kwh * days, 2),
        "monthly_bill": round(day_bill * days, 2),
        "monthly_baseline": round(daily_base * days, 2),
        "monthly_saving": round(day_saving * days, 2) if used else 0.0,
        "potential_saving": round(day_saving * days, 2),
        "kwh_per_hour": round(daily_kwh / hours, 2) if hours > 0 else 0.0,
        "cost_per_hour": round(day_bill / hours, 2) if hours > 0 else 0.0,
    }
