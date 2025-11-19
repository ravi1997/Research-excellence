# ResearchCycle Framework Enhancement Plan

## Overview
The current system has a Cycle model with CycleWindow that supports different phases (SUBMISSION, VERIFICATION, FINAL). We need to enhance this to support independent time windows specifically for abstract submissions, best paper nominations, and awards ceremonies.

## Current State Analysis
- Cycle model: Contains basic cycle information (name, start/end dates)
- CycleWindow model: Defines time windows with phases (SUBMISSION, VERIFICATION, FINAL)
- Current enforcement: Submissions are allowed only during the SUBMISSION phase of a cycle
- Models affected: Abstracts, Awards, BestPaper all use the same submission window validation

## Proposed Enhancement

### 1. Enhanced Enumerations
Add new values to the CyclePhase enumeration to support specific component types:

```python
class CyclePhase(str, Enum):
    SUBMISSION = "SUBMISSION"
    VERIFICATION = "VERIFICATION"
    FINAL = "FINAL"
    # New values for specific components
    ABSTRACT_SUBMISSION = "ABSTRACT_SUBMISSION"
    BEST_PAPER_SUBMISSION = "BEST_PAPER_SUBMISSION"
    AWARD_SUBMISSION = "AWARD_SUBMISSION"
    ABSTRACT_VERIFICATION = "ABSTRACT_VERIFICATION"
    BEST_PAPER_VERIFICATION = "BEST_PAPER_VERIFICATION"
    AWARD_VERIFICATION = "AWARD_VERIFICATION"
    ABSTRACT_FINAL = "ABSTRACT_FINAL"
    BEST_PAPER_FINAL = "BEST_PAPER_FINAL"
    AWARD_FINAL = "AWARD_FINAL"
```

### 2. Enhanced CycleWindow Model
Modify the CycleWindow model to support these new specific phases:

- Each cycle can have multiple windows of different types
- Each component (abstract, best paper, award) can have its own submission, verification, and final phases
- Maintain backward compatibility with existing SUBMISSION, VERIFICATION, FINAL phases

### 3. Database Constraints
- Ensure that for each cycle, there's at most one window of each type per phase
- Add validation to prevent overlapping windows for the same component type
- Maintain existing constraints for the general phases

### 4. Updated Validation Logic
Modify the validation functions to check against the specific component windows:

```python
def _ensure_submission_window(connection, submission_model, required_phase=None):
    cycle_id = getattr(submission_model, "cycle_id", None)
    if cycle_id is None:
        raise ValueError("A submission must belong to a cycle.")

    submitted_on = getattr(submission_model, "created_at", None)
    if submitted_on is None:
        submitted_on = datetime.utcnow()

    submission_date = submitted_on.date()
    
    # Determine the required phase based on the model type
    if required_phase is None:
        if isinstance(submission_model, Abstracts):
            required_phase = CyclePhase.ABSTRACT_SUBMISSION
        elif isinstance(submission_model, Awards):
            required_phase = CyclePhase.AWARD_SUBMISSION
        elif isinstance(submission_model, BestPaper):
            required_phase = CyclePhase.BEST_PAPER_SUBMISSION
        else:
            required_phase = CyclePhase.SUBMISSION  # Fallback to general submission

    stmt = select(CycleWindow.id).where(
        CycleWindow.cycle_id == cycle_id,
        CycleWindow.phase == required_phase,
        CycleWindow.start_date <= submission_date,
        CycleWindow.end_date >= submission_date,
    )

    if connection.execute(stmt).first() is None:
        raise ValueError(
            f"Submissions are allowed only during the {required_phase} period for the cycle.",
        )
```

### 5. Redis Configuration Details

The system now includes Redis for caching and session management. The following configuration is required:

```python
# Redis configuration in app/config.py
class Config:
    # ... other configurations ...
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = int(os.environ.get('REDIS_PORT') or 6379)
    REDIS_DB = int(os.environ.get('REDIS_DB') or 0)
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD') or None
    REDIS_SSL = os.environ.get('REDIS_SSL', 'False').lower() == 'true'
    
    # Session configuration using Redis
    SESSION_TYPE = 'redis'
    SESSION_REDIS = redis.from_url(REDIS_URL)
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'research_session:'
    
    # Cache configuration using Redis
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_KEY_PREFIX = 'research_cache:'
    CACHE_DEFAULT_TIMEOUT = 300
```

### 5. Schema Updates
- Update CycleSchema to properly handle the new window types
- Create new schemas if needed for specific window operations

### 6. API Route Updates
- Enhance existing cycle routes to support managing specific component windows
- Add endpoints to query component-specific windows
- Maintain backward compatibility with existing API endpoints

## Implementation Steps

### Phase 1: Enumeration and Model Updates
1. Add new enumeration values to CyclePhase
2. Update CycleWindow model with any necessary changes
3. Update validation logic to support component-specific windows

### Phase 2: Schema and API Updates
1. Update schemas to support the new functionality
2. Enhance API routes to manage specific component windows
3. Add new endpoints for component-specific window management

### Phase 3: Testing and Validation
1. Test backward compatibility
2. Verify that each component type respects its specific window
3. Ensure no regressions in existing functionality

## Benefits of This Approach

1. **Flexibility**: Each component type (abstract, best paper, award) can have completely independent time windows
2. **Backward Compatibility**: Existing functionality continues to work with general phases
3. **Scalability**: New component types can be added easily in the future
4. **Maintainability**: Clear separation between different types of windows
5. **Validation**: Strong validation ensures submissions happen only during appropriate windows

## Potential Challenges

1. **Database Migration**: Need to handle existing data during migration
2. **Validation Complexity**: More complex validation logic to handle multiple window types
3. **UI Updates**: Frontend may need updates to support managing different window types
4. **Testing**: Comprehensive testing needed to ensure all combinations work properly