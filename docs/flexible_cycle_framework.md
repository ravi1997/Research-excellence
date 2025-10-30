# Flexible Cycle Framework

## Overview

The flexible cycle framework enhances the existing cycle management system to support independent, customizable time windows for abstract submissions, best paper nominations, and awards ceremonies. Each component can have its own timeline that can be adjusted individually while maintaining the overall cycle structure.

## Key Features

1. **Independent Time Windows**: Each component (abstracts, best papers, awards) can have completely separate submission, verification, and final phases
2. **Flexible Configuration**: Different durations and scheduling windows for each component as needed
3. **Backward Compatibility**: Existing functionality continues to work with general phases
4. **Validation**: Strong validation ensures submissions happen only during appropriate windows

## Architecture

### Enumerations

The `CyclePhase` enumeration has been enhanced with specific component phases:

- `ABSTRACT_SUBMISSION` - Time window for abstract submissions
- `BEST_PAPER_SUBMISSION` - Time window for best paper nominations
- `AWARD_SUBMISSION` - Time window for award submissions
- `ABSTRACT_VERIFICATION` - Time window for abstract verification
- `BEST_PAPER_VERIFICATION` - Time window for best paper verification
- `AWARD_VERIFICATION` - Time window for award verification
- `ABSTRACT_FINAL` - Time window for final abstract activities
- `BEST_PAPER_FINAL` - Time window for final best paper activities
- `AWARD_FINAL` - Time window for final award activities

### Models

#### Cycle Model
- Contains basic cycle information (name, start/end dates)
- Has relationships to multiple CycleWindow instances

#### CycleWindow Model
- Represents a specific time window for a cycle
- Links to a specific phase (general or component-specific)
- Defines start and end dates for the window

### Validation Logic

The validation logic has been updated to check for component-specific windows first, with fallback to general windows for backward compatibility.

## API Endpoints

### Cycle Management
- `POST /cycles` - Create a new cycle
- `GET /cycles` - Get all cycles
- `GET /cycles/<cycle_id>` - Get a specific cycle
- `PUT /cycles/<cycle_id>` - Update a cycle
- `DELETE /cycles/<cycle_id>` - Delete a cycle

### Cycle Window Management
- `POST /cycles/<cycle_id>/windows` - Create a new window for a cycle
- `GET /cycles/<cycle_id>/windows` - Get all windows for a cycle
- `GET /cycles/<cycle_id>/windows/<window_id>` - Get a specific window
- `PUT /cycles/<cycle_id>/windows/<window_id>` - Update a specific window
- `DELETE /cycles/<cycle_id>/windows/<window_id>` - Delete a specific window

### Component-Specific Endpoints
- `GET /cycles/<cycle_id>/abstract-windows` - Get all abstract-related windows
- `GET /cycles/<cycle_id>/best-paper-windows` - Get all best paper-related windows
- `GET /cycles/<cycle_id>/award-windows` - Get all award-related windows

## Usage Examples

### Creating a Cycle with Specific Windows

```python
# Create a cycle
cycle = Cycle(
    name="Research Cycle 2025",
    start_date="2025-01-01",
    end_date="2025-12-31"
)

# Create specific windows for each component
abstract_window = CycleWindow(
    cycle_id=cycle.id,
    phase="ABSTRACT_SUBMISSION",
    start_date="2025-01-01",
    end_date="2025-03-31"
)

best_paper_window = CycleWindow(
    cycle_id=cycle.id,
    phase="BEST_PAPER_SUBMISSION",
    start_date="2025-04-01",
    end_date="2025-06-30"
)

award_window = CycleWindow(
    cycle_id=cycle.id,
    phase="AWARD_SUBMISSION",
    start_date="2025-07-01",
    end_date="2025-09-30"
)
```

### Validation Behavior

When a submission is made:
1. The system checks if a specific window exists for the component type
2. If found and the submission date is within that window, the submission is allowed
3. If no specific window exists, it falls back to checking general windows
4. If neither specific nor general windows allow the submission, it's rejected

## Backward Compatibility

The framework maintains backward compatibility by:
- Preserving existing SUBMISSION, VERIFICATION, and FINAL phases
- Allowing mixed use of general and specific phases
- Providing fallback validation to general phases when specific ones aren't defined

## Benefits

1. **Flexibility**: Each component type can have completely independent time windows
2. **Scalability**: New component types can be added easily in the future
3. **Maintainability**: Clear separation between different types of windows
4. **Validation**: Strong validation ensures proper timing of submissions
5. **User Experience**: Administrators can configure complex schedules that match their organizational needs