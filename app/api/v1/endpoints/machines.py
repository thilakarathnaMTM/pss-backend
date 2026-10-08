from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.machine import Machine
from app.services.scheduler import recalculate, get_factory
from app.schemas.machine import MachineCreate, MachineUpdate, MachineOut, check_window, check_year

router = APIRouter(prefix="/machines", tags=["Machines"])

def to_out(machine: Machine) -> MachineOut:
    out = MachineOut.model_validate(machine)
    out.total_power_w = machine.quantity * machine.power_w
    return out

@router.post("", response_model=MachineOut, status_code=status.HTTP_201_CREATED)
async def create_machine(
    data: MachineCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.factory_id:
        raise HTTPException(status_code=400, detail="No factory linked")
    machine = Machine(factory_id=current_user.factory_id, **data.model_dump())
    db.add(machine)
    await db.flush()
    await recalculate(db, await get_factory(db, current_user.factory_id), trigger=f"Machine added: {machine.name}")
    await db.commit()
    await db.refresh(machine)
    return to_out(machine)

@router.get("", response_model=List[MachineOut])
async def list_machines(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.factory_id:
        return []
    result = await db.execute(select(Machine).where(Machine.factory_id == current_user.factory_id))
    machines = result.scalars().all()
    return [to_out(m) for m in machines]

@router.get("/{machine_id}", response_model=MachineOut)
async def get_machine(
    machine_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Machine).where(Machine.id == machine_id, Machine.factory_id == current_user.factory_id)
    )
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return to_out(machine)

@router.put("/{machine_id}", response_model=MachineOut)
async def update_machine(
    machine_id: int,
    data: MachineUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Machine).where(Machine.id == machine_id, Machine.factory_id == current_user.factory_id)
    )
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    changes = data.model_dump(exclude_unset=True)
    try:
        check_window(
            changes.get("available_start", machine.available_start),
            changes.get("available_end", machine.available_end),
            changes.get("required_hours", machine.required_hours),
            changes.get("usual_start", machine.usual_start),
        )
        check_year(changes.get("manufactured_year"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    for field, value in changes.items():
        setattr(machine, field, value)
    await db.flush()
    await recalculate(db, await get_factory(db, current_user.factory_id), trigger=f"Machine updated: {machine.name}")
    await db.commit()
    await db.refresh(machine)
    return to_out(machine)

@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_machine(
    machine_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Machine).where(Machine.id == machine_id, Machine.factory_id == current_user.factory_id)
    )
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    name = machine.name
    await db.delete(machine)
    await db.flush()
    await recalculate(db, await get_factory(db, current_user.factory_id), trigger=f"Machine deleted: {name}")
    await db.commit()
    return None
