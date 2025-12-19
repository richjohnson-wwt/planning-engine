# Multi-Day Scheduler Quick Start Guide

## 🎯 What You Have Now

✅ **Single-Day VRP Solver** - Production ready!
- File: `src/planning_engine/ortools_solver.py`
- Function: `plan_single_day_vrp()`
- What it does: Optimizes routes for ONE day
- Status: **DONE** - Don't modify this!

## 🚀 What You Need to Build

❌ **Multi-Day Scheduler** - Orchestrates single-day solver across multiple days
- File: `src/planning_engine/multi_day_scheduler.py` (stubs created)
- Function: `plan_multi_day_schedule()`
- What it will do: Call `plan_single_day_vrp()` for each work day
- Status: **TODO** - Start here tomorrow!

## 📋 Step-by-Step Implementation Plan

### Step 1: Implement `calculate_work_days()` (30 minutes)

**Goal**: Calculate available work days excluding weekends and holidays

```python
def calculate_work_days(
    start_date: date,
    end_date: date,
    holidays: List[date],
    exclude_weekends: bool = True
) -> List[date]:
    """Return list of work dates between start and end."""
    work_days = []
    current = start_date
    
    while current <= end_date:
        # Skip weekends (Saturday=5, Sunday=6)
        if exclude_weekends and current.weekday() >= 5:
            current += timedelta(days=1)
            continue
            
        # Skip holidays
        if current in holidays:
            current += timedelta(days=1)
            continue
            
        work_days.append(current)
        current += timedelta(days=1)
    
    return work_days
```

**Test it**:
```python
# Test in Python REPL
from datetime import date
from planning_engine.multi_day_scheduler import calculate_work_days

start = date(2025, 1, 1)  # Wednesday
end = date(2025, 1, 10)   # Friday
holidays = [date(2025, 1, 6)]  # Monday holiday

work_days = calculate_work_days(start, end, holidays)
print(f"Work days: {len(work_days)}")  # Should be 6 days
# Jan 1,2,3 (Wed-Fri) + Jan 7,8,9,10 (Tue-Fri) = 7 days
# Minus Jan 6 holiday = 6 days
```

### Step 2: Implement `allocate_sites_to_days()` (1 hour)

**Goal**: Divide sites evenly across work days

```python
def allocate_sites_to_days(
    sites: List[Site],
    work_days: List[date],
    crews_per_day: int,
    max_sites_per_crew_per_day: int,
    strategy: str = "balanced"
) -> dict[date, List[Site]]:
    """Allocate sites to work days."""
    
    if strategy != "balanced":
        raise NotImplementedError(f"Strategy '{strategy}' not implemented yet")
    
    # Calculate capacity per day
    sites_per_day = crews_per_day * max_sites_per_crew_per_day
    
    # Divide sites evenly across days
    allocation = {}
    site_idx = 0
    
    for work_date in work_days:
        # Allocate up to sites_per_day for this date
        day_sites = sites[site_idx:site_idx + sites_per_day]
        allocation[work_date] = day_sites
        site_idx += len(day_sites)
        
        # Stop if we've allocated all sites
        if site_idx >= len(sites):
            break
    
    return allocation
```

**Test it**:
```python
# Create 50 test sites
sites = [Site(id=str(i), name=f"Site {i}", lat=38.0, lon=-90.0) 
         for i in range(50)]

allocation = allocate_sites_to_days(
    sites=sites,
    work_days=work_days,  # From step 1
    crews_per_day=3,
    max_sites_per_crew_per_day=8
)

for work_date, day_sites in allocation.items():
    print(f"{work_date}: {len(day_sites)} sites")
# Should show ~24 sites per day (3 crews × 8 sites)
```

### Step 3: Implement `plan_multi_day_schedule()` (1 hour)

**Goal**: Call single-day VRP for each day and combine results

```python
def plan_multi_day_schedule(request: PlanRequest) -> PlanResult:
    """Plan routes across multiple days."""
    from .ortools_solver import plan_single_day_vrp
    
    # Validate required fields
    if not request.start_date or not request.end_date:
        raise ValueError("start_date and end_date required for multi-day scheduling")
    
    # Step 1: Calculate work days
    work_days = calculate_work_days(
        start_date=request.start_date,
        end_date=request.end_date,
        holidays=request.holidays
    )
    
    if not work_days:
        raise ValueError("No work days available in date range")
    
    # Step 2: Allocate sites to days
    allocation = allocate_sites_to_days(
        sites=request.sites,
        work_days=work_days,
        crews_per_day=request.get_num_crews(),
        max_sites_per_crew_per_day=request.max_sites_per_crew_per_day
    )
    
    # Step 3: Plan each day using single-day VRP
    all_team_days = []
    total_unassigned = 0
    
    for work_date, day_sites in allocation.items():
        if not day_sites:
            continue
            
        # Create single-day request
        day_request = PlanRequest(
            workspace=request.workspace,
            sites=day_sites,
            team_config=request.team_config,
            start_date=work_date,  # This specific day
            num_crews_available=request.num_crews_available,
            max_route_minutes=request.max_route_minutes,
            service_minutes_per_site=request.service_minutes_per_site,
            max_sites_per_crew_per_day=request.max_sites_per_crew_per_day,
            minimize_crews=request.minimize_crews
        )
        
        # Call single-day VRP solver
        day_result = plan_single_day_vrp(day_request)
        all_team_days.extend(day_result.team_days)
        total_unassigned += day_result.unassigned
        
        print(f"  {work_date}: {len(day_result.team_days)} team-days, "
              f"{day_result.unassigned} unassigned")
    
    return PlanResult(team_days=all_team_days, unassigned=total_unassigned)
```

### Step 4: Wire it up in `api.py` (15 minutes)

Update `_plan_with_ortools()` to detect multi-day requests:

```python
def _plan_with_ortools(request: PlanRequest) -> PlanResult:
    """Use OR-Tools solver for optimized routing."""
    
    # Check if this is a multi-day request
    if request.start_date and request.end_date:
        days_diff = (request.end_date - request.start_date).days
        
        if days_diff > 0:
            # Multi-day scheduling
            from .multi_day_scheduler import plan_multi_day_schedule
            return plan_multi_day_schedule(request)
    
    # Single-day VRP (existing code)
    from .ortools_solver import plan_single_day_vrp
    return plan_single_day_vrp(request)
```

### Step 5: Test End-to-End (30 minutes)

Create `tests/test_multi_day.py`:

```python
from datetime import date
from planning_engine import plan
from planning_engine.models import PlanRequest, TeamConfig, Workday, Site

def test_multi_day_basic():
    """Test 3-day project with 50 sites."""
    # Create 50 test sites
    sites = [
        Site(
            id=str(i),
            name=f"Site {i}",
            lat=38.6270 + (i * 0.001),
            lon=-90.1994 + (i * 0.001),
            service_minutes=60
        )
        for i in range(50)
    ]
    
    request = PlanRequest(
        workspace="test_multi_day",
        sites=sites,
        team_config=TeamConfig(
            teams=3,
            workday=Workday(start=time(9,0), end=time(17,0))
        ),
        start_date=date(2025, 1, 6),   # Monday
        end_date=date(2025, 1, 10),    # Friday
        holidays=[],
        num_crews_available=3,
        max_route_minutes=480,
        service_minutes_per_site=60,
        max_sites_per_crew_per_day=8
    )
    
    result = plan(request)
    
    # Assertions
    assert len(result.team_days) > 0
    scheduled = sum(len(td.site_ids) for td in result.team_days)
    assert scheduled <= 50
    print(f"✅ Scheduled {scheduled}/50 sites across {len(result.team_days)} team-days")
```

Run it:
```bash
uv run pytest tests/test_multi_day.py -v
```

## 📊 Expected Results

For a 50-site, 3-crew, 5-day project:
- **Capacity**: 3 crews × 8 sites/day = 24 sites/day
- **Days needed**: 50 sites ÷ 24 sites/day = ~3 days
- **Output**: ~9 team-days (3 days × 3 crews)

## 🐛 Common Issues

1. **"No work days available"** - Check date range and holidays
2. **"All sites unassigned"** - Check max_route_minutes and service_minutes
3. **"Wrong number of team-days"** - Check allocation logic

## 📚 Reference Files

- `src/planning_engine/multi_day_scheduler.py` - Stubs and architecture
- `src/planning_engine/ortools_solver.py` - Single-day VRP (don't modify!)
- `FEATURES.md` - Feature implementation status
- `README.md` - User requirements

## 🎯 Success Criteria

You'll know it's working when:
1. ✅ All 3 helper functions pass unit tests
2. ✅ End-to-end test schedules 50 sites across 3 days
3. ✅ Output JSON shows team_days with different dates
4. ✅ No sites are unassigned (unless capacity insufficient)

## 💡 Tips

- Start simple - get it working with "balanced" strategy first
- Test each function independently before integration
- Use print statements to debug allocation logic
- The single-day VRP is solid - trust it!

Good luck! You have a great foundation to build on. 🚀
