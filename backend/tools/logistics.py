"""
Logistics Optimization Tool — route optimization using OR-Tools.
"""
import math
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import TransportRoute, Warehouse, Shipment
import logging

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in km."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def calculate_transportation_cost(
    distance_km: float,
    quantity: int,
    base_cost_per_unit: float,
    weight_kg: float = 1.0,
) -> dict:
    """
    Calculate transportation cost components.
    Cost = base_cost * quantity + distance_factor
    """
    base_cost = base_cost_per_unit * quantity
    distance_factor = distance_km * 0.05 * weight_kg
    fuel_surcharge = base_cost * 0.08
    handling_fee = max(50, quantity * 0.5)
    total_cost = base_cost + distance_factor + fuel_surcharge + handling_fee

    return {
        "base_cost": round(base_cost, 2),
        "distance_surcharge": round(distance_factor, 2),
        "fuel_surcharge": round(fuel_surcharge, 2),
        "handling_fee": round(handling_fee, 2),
        "total_cost": round(total_cost, 2),
        "cost_per_unit": round(total_cost / max(1, quantity), 2),
    }


async def optimize_routes(
    session: AsyncSession,
    destination: Optional[str] = None,
) -> dict:
    """
    Find optimal routes from warehouses to destinations.
    Uses OR-Tools for multi-warehouse allocation when applicable.
    """
    # Fetch all routes
    query = select(TransportRoute, Warehouse).join(
        Warehouse, TransportRoute.origin_warehouse_id == Warehouse.warehouse_id
    )
    if destination:
        query = query.where(TransportRoute.destination.ilike(f"%{destination}%"))

    result = await session.execute(query)
    rows = result.fetchall()

    if not rows:
        return {"error": "No transport routes found"}

    routes_data = []
    for route, warehouse in rows:
        cost = calculate_transportation_cost(
            route.distance_km, 100, route.base_cost_per_unit
        )
        routes_data.append({
            "route_id": route.route_id,
            "origin_warehouse": warehouse.warehouse_name,
            "origin_warehouse_id": route.origin_warehouse_id,
            "destination": route.destination,
            "distance_km": route.distance_km,
            "transit_time_days": route.transit_time_days,
            "transport_mode": route.transport_mode,
            "carrier": route.carrier,
            "base_cost_per_unit": route.base_cost_per_unit,
            "estimated_cost_100_units": cost["total_cost"],
        })

    # Sort by total cost
    routes_data.sort(key=lambda x: x["estimated_cost_100_units"])

    # OR-Tools optimization: minimize total cost across warehouses
    try:
        from ortools.linear_solver import pywraplp
        solver = pywraplp.Solver.CreateSolver("GLOP")
        if solver and len(routes_data) > 1:
            # Simple allocation: minimize weighted cost
            n = len(routes_data)
            vars_ = [
                solver.NumVar(0, 1, f"x_{i}")
                for i in range(n)
            ]
            # Constraint: select routes that minimize cost
            objective = solver.Objective()
            for i, r in enumerate(routes_data):
                objective.SetCoefficient(vars_[i], r["estimated_cost_100_units"])
            objective.SetMinimization()
            solver.Solve()

            optimized_routes = []
            for i, r in enumerate(routes_data):
                if vars_[i].solution_value() > 0.5 or i == 0:
                    optimized_routes.append(r)
        else:
            optimized_routes = routes_data[:3]

    except Exception as e:
        logger.warning(f"OR-Tools optimization failed: {e}, using heuristic sort")
        optimized_routes = routes_data

    return {
        "destination": destination or "All",
        "total_routes": len(routes_data),
        "all_routes": routes_data,
        "recommended_routes": optimized_routes[:5],
        "optimal_route": routes_data[0] if routes_data else None,
    }


async def optimize_warehouse_allocation(
    session: AsyncSession,
    product_id: str,
    destination: str,
    quantity: int,
) -> dict:
    """
    Determine optimal warehouse-to-customer allocation using OR-Tools.
    Minimizes total transportation cost subject to stock constraints.
    """
    from database.models import Inventory
    from ortools.linear_solver import pywraplp

    # Get inventory levels per warehouse
    inv_result = await session.execute(
        select(Inventory, Warehouse).join(
            Warehouse, Inventory.warehouse_id == Warehouse.warehouse_id
        ).where(Inventory.product_id == product_id)
    )
    inv_rows = inv_result.fetchall()

    if not inv_rows:
        return {"error": f"No inventory found for product {product_id}"}

    # Get routes to destination
    route_result = await session.execute(
        select(TransportRoute).where(
            TransportRoute.destination.ilike(f"%{destination}%")
        )
    )
    routes = {r.origin_warehouse_id: r for r in route_result.scalars().all()}

    warehouses_data = []
    for inv, wh in inv_rows:
        route = routes.get(inv.warehouse_id)
        if route:
            cost = calculate_transportation_cost(
                route.distance_km, quantity, route.base_cost_per_unit
            )
            warehouses_data.append({
                "warehouse_id": inv.warehouse_id,
                "warehouse_name": wh.warehouse_name,
                "available_stock": inv.current_stock,
                "distance_km": route.distance_km,
                "transit_time_days": route.transit_time_days,
                "cost_per_unit": cost["cost_per_unit"],
                "total_cost": cost["total_cost"],
            })

    if not warehouses_data:
        # Fallback: return warehouses without route costs
        for inv, wh in inv_rows:
            warehouses_data.append({
                "warehouse_id": inv.warehouse_id,
                "warehouse_name": wh.warehouse_name,
                "available_stock": inv.current_stock,
                "distance_km": None,
                "transit_time_days": None,
                "cost_per_unit": None,
                "total_cost": None,
            })

    # OR-Tools: minimize cost, subject to stock availability
    try:
        solver = pywraplp.Solver.CreateSolver("GLOP")
        n = len(warehouses_data)
        alloc_vars = [
            solver.NumVar(0, float(warehouses_data[i]["available_stock"]), f"alloc_{i}")
            for i in range(n)
        ]

        # Constraint: total allocation == quantity requested
        ct = solver.Constraint(quantity, quantity, "demand")
        for v in alloc_vars:
            ct.SetCoefficient(v, 1)

        objective = solver.Objective()
        for i, w in enumerate(warehouses_data):
            cost = w["cost_per_unit"] or 10.0
            objective.SetCoefficient(alloc_vars[i], cost)
        objective.SetMinimization()

        status = solver.Solve()
        allocations = []
        total_allocated = 0

        if status == pywraplp.Solver.OPTIMAL:
            for i, w in enumerate(warehouses_data):
                alloc_qty = int(round(alloc_vars[i].solution_value()))
                if alloc_qty > 0:
                    allocations.append({
                        **w,
                        "allocated_quantity": alloc_qty,
                    })
                    total_allocated += alloc_qty
        else:
            # Greedy fallback
            remaining = quantity
            for w in sorted(warehouses_data, key=lambda x: x["cost_per_unit"] or 999):
                if remaining <= 0:
                    break
                alloc = min(remaining, w["available_stock"])
                if alloc > 0:
                    allocations.append({**w, "allocated_quantity": alloc})
                    remaining -= alloc
                    total_allocated += alloc

    except Exception as e:
        logger.error(f"OR-Tools allocation error: {e}")
        allocations = []
        for w in warehouses_data:
            allocations.append({**w, "allocated_quantity": min(quantity, w["available_stock"])})

    total_cost = sum(
        a["cost_per_unit"] * a["allocated_quantity"]
        for a in allocations
        if a["cost_per_unit"]
    )

    return {
        "product_id": product_id,
        "destination": destination,
        "quantity_requested": quantity,
        "total_allocated": total_allocated if 'total_allocated' in dir() else 0,
        "allocations": allocations,
        "total_transportation_cost": round(total_cost, 2),
        "warehouses_evaluated": warehouses_data,
    }
