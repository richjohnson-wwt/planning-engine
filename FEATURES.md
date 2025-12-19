# Feature Implementation Status

This document tracks the implementation status of user-requested features.

## ✅ Implemented Features (Single-Day VRP)

### Team Assignments
- ✅ **Allocate routes based on number of teams**
  - Implementation: `num_crews_available` parameter
  - File: `models.py`, `ortools_solver.py`
  
- ✅ **Auto-calculate number of teams needed**
  - Implementation: `minimize_crews=True` mode
  - File: `ortools_solver.py`
  - The solver automatically determines minimum crews needed to complete all sites

- ✅ **Divide based on regions**
  - Implementation: State-based filtering + cluster-based planning
  - File: `api.py` - `use_clusters=True`, `state_abbr` parameter
  - Sites are grouped by geographic clusters and planned separately

### Time Estimation
- ✅ **Estimate time per site**
  - Implementation: `service_minutes_per_site` parameter
  - File: `models.py`
  - Default: 60 minutes per site

- ✅ **Define working hours per day**
  - Implementation: `Workday(start, end)` in `TeamConfig`
  - File: `models.py`
  - Example: `Workday(start=time(9,0), end=time(17,0))` = 8-hour workday

- ✅ **Set number of sites per day per team**
  - Implementation: `max_sites_per_crew_per_day` parameter
  - File: `models.py`
  - Default: 8 sites per crew per day

### Routing
- ✅ **Team radius based on region**
  - Implementation: Cluster-based planning keeps routes within geographic boundaries
  - File: `api.py` - `_plan_with_clusters()`
  - Each cluster is planned separately to avoid long-distance travel

- ✅ **Optimize travel time**
  - Implementation: OR-Tools VRP solver with haversine distance calculation
  - File: `ortools_solver.py` - `plan_single_day_vrp()`
  - Minimizes total route time including travel and service

## ⚠️ Partially Implemented

### Project Start/End Dates
- ⚠️ **Fields exist but limited functionality**
  - Implementation: `start_date` and `end_date` fields in `PlanRequest`
  - Current use: 
    - `start_date` used for timestamp reporting
    - Fields trigger OR-Tools solver vs simple fallback
  - **NOT YET**: Multi-day scheduling across date range
  - File: `models.py`, `api.py`

### Holidays and Blackout Dates
- ⚠️ **Field exists but not used**
  - Implementation: `holidays` field in `PlanRequest`
  - Current use: None (reserved for future multi-day scheduler)
  - **NOT YET**: Exclude holidays from work schedule
  - File: `models.py`

## ❌ Not Yet Implemented

### Multi-Day Scheduling
- ❌ **Estimate total project duration**
  - Need: Calculate days needed to complete all sites
  - Depends on: Multi-day scheduler
  - Placeholder: `multi_day_scheduler.py` - `estimate_project_duration()`

- ❌ **Schedule across multiple days**
  - Need: Allocate sites to specific dates between start_date and end_date
  - Depends on: Multi-day scheduler
  - Placeholder: `multi_day_scheduler.py` - `plan_multi_day_schedule()`

- ❌ **Can a region be completed before a break**
  - Need: Analyze if work can finish before holiday/blackout date
  - Depends on: Multi-day scheduler
  - Placeholder: `multi_day_scheduler.py` - `check_region_completion_before_break()`

### Variable Service Times
- ❌ **Set hours to complete each site by T-shirt size**
  - Need: Add `t_shirt_size` field to Site model (S, M, L, XL)
  - Need: Map sizes to service_minutes (S=30, M=60, L=90, XL=120)
  - Current: All sites use same `service_minutes_per_site`
  - File to modify: `models.py` - Site model

### Ramp Phase Approach
- ❌ **Crawl, Walk, Run - Ramp Phase approach**
  - Need: Progressive capacity model
  - Example: Week 1 = 50% capacity, Week 2 = 75%, Week 3+ = 100%
  - Depends on: Multi-day scheduler with "ramp" allocation strategy
  - Placeholder: `multi_day_scheduler.py` - `allocate_sites_to_days(strategy="ramp")`

### Advanced Routing
- ❌ **Set the run rate across regions per bridge/cut**
  - Need: Define capacity constraints per geographic region
  - Need: Track completion rate per region
  - Depends on: Multi-day scheduler + region-specific constraints

## 🏗️ Architecture Overview

```
Current (Single-Day VRP):
    User Request
        ↓
    API (api.py)
        ↓
    plan_single_day_vrp() [IMPLEMENTED ✅]
        ↓
    Optimized routes for ONE day

Future (Multi-Day Scheduling):
    User Request (with start_date, end_date)
        ↓
    API (api.py)
        ↓
    plan_multi_day_schedule() [TODO ❌]
        ↓
    Calculate work days (exclude weekends, holidays)
        ↓
    Allocate sites to days
        ↓
    For EACH day:
        plan_single_day_vrp() [IMPLEMENTED ✅]
        ↓
    Combined multi-day schedule
```

## 📋 Implementation Priority

### Phase 1: Multi-Day Basics (High Priority)
1. Implement `calculate_work_days()` - exclude weekends and holidays
2. Implement `allocate_sites_to_days()` with balanced strategy
3. Implement `plan_multi_day_schedule()` to orchestrate single-day calls
4. Test with 3-day, 50-site scenario

### Phase 2: Duration Estimation (Medium Priority)
1. Implement `estimate_project_duration()`
2. Add capacity calculation
3. Show estimated completion date in UI

### Phase 3: Variable Service Times (Medium Priority)
1. Add `t_shirt_size` field to Site model
2. Update Excel parsing to read t-shirt sizes
3. Map sizes to service_minutes

### Phase 4: Advanced Features (Lower Priority)
1. Implement ramp-up allocation strategy
2. Implement break analysis
3. Add region-specific run rates
4. Support priority-based scheduling

## 📝 Notes for Future Development

- **Single-day VRP is production-ready** - Don't modify it, just call it from multi-day scheduler
- **Multi-day scheduler stubs are in** `multi_day_scheduler.py`
- **All helper functions have detailed docstrings** explaining what they should do
- **Test files exist** in `tests/` directory - add multi-day tests there
- **Current system handles 80% of requirements** with single-day optimization

## 🔗 Key Files

- `src/planning_engine/ortools_solver.py` - Single-day VRP solver (DONE ✅)
- `src/planning_engine/multi_day_scheduler.py` - Multi-day scheduler (STUBS ONLY)
- `src/planning_engine/models.py` - Data models
- `src/planning_engine/api.py` - Public API
- `README.md` - User feature requests
- `FEATURES.md` - This file

## 🚀 Getting Started with Multi-Day Implementation

1. Read `multi_day_scheduler.py` - contains architecture and roadmap
2. Start with `calculate_work_days()` - simplest function
3. Write tests first (TDD approach)
4. Implement `allocate_sites_to_days()` with "balanced" strategy
5. Implement `plan_multi_day_schedule()` to tie it together
6. Test with real data from `data/workspace/` directories

Good luck! The foundation is solid - you're just adding the orchestration layer on top.
