# Usage Tracking Refactoring Guide

## Current Problem
Usage tracking is tightly coupled with business logic, making the code harder to maintain and test.

## Recommended Architecture

### Option 1: Service Layer Pattern (Recommended)
Separate usage tracking into a dedicated service layer that can be injected where needed.

```python
# api/routes.py
from core.middleware.usage_tracking import get_usage_service

@router.post("/api/chat")
async def chat(request, current_user = Depends(get_optional_user)):
    usage_service = get_usage_service()
    start_time = time.time()
    
    try:
        # Business logic
        result = await chat_interface.send_message(...)
        
        # Track success
        await usage_service.track_chat_usage(
            user_id=current_user.get("user_id"),
            user_email=current_user.get("email"),
            session_id=session_id,
            message=message,
            response=result["response"],
            duration=time.time() - start_time,
            tokens_used=result.get("tokens", 0)
        )
        
        return result
        
    except Exception as e:
        # Track failure
        await usage_service.track_chat_usage(
            user_id=current_user.get("user_id"),
            user_email=current_user.get("email"),
            session_id=session_id,
            message=message,
            response="",
            duration=time.time() - start_time,
            error=str(e)
        )
        raise
```

### Option 2: Decorator Pattern
Use decorators for cleaner code:

```python
from core.middleware.usage_tracking import track_api_usage

@router.post("/api/chat")
@track_api_usage(operation="chat")
async def chat(request, current_user = Depends(get_optional_user)):
    # Just business logic, tracking happens automatically
    result = await chat_interface.send_message(...)
    return result
```

### Option 3: Event-Driven Pattern
Emit events and let listeners handle tracking:

```python
# core/events.py
from typing import Dict, Any
import asyncio

class EventBus:
    def __init__(self):
        self.listeners = {}
    
    def on(self, event: str):
        def decorator(func):
            if event not in self.listeners:
                self.listeners[event] = []
            self.listeners[event].append(func)
            return func
        return decorator
    
    async def emit(self, event: str, data: Dict[str, Any]):
        if event in self.listeners:
            tasks = [listener(data) for listener in self.listeners[event]]
            await asyncio.gather(*tasks, return_exceptions=True)

# Usage
event_bus = EventBus()

@event_bus.on("chat.completed")
async def track_chat(data):
    await usage_service.track_chat_usage(**data)

# In your endpoint
await event_bus.emit("chat.completed", {
    "user_id": user_id,
    "session_id": session_id,
    ...
})
```

## Benefits of Separation

1. **Single Responsibility**: Each component has one job
2. **Testability**: Can test business logic without tracking
3. **Reusability**: Same tracking logic for multiple endpoints
4. **Flexibility**: Easy to change tracking implementation
5. **Performance**: Can make tracking async/non-blocking

## Implementation Steps

### Phase 1: Create Service Layer
✅ Created `core/middleware/usage_tracking.py` with:
- `UsageTrackingService` class
- Dedicated methods for different operations
- Clean separation of concerns

### Phase 2: Refactor Endpoints
Move tracking logic from:
- `core/assistant/chat.py` → Remove embedded tracking
- `api/routes.py` → Add service layer calls

### Phase 3: Add Middleware (Optional)
For automatic request/response tracking:
```python
# main.py
from core.middleware.usage_tracking import UsageTrackingMiddleware
app.add_middleware(UsageTrackingMiddleware)
```

### Phase 4: Async Processing (Future)
Consider using background tasks for non-blocking tracking:
```python
from fastapi import BackgroundTasks

@router.post("/api/chat")
async def chat(
    request: dict,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_optional_user)
):
    result = await chat_interface.send_message(...)
    
    # Track in background, don't block response
    background_tasks.add_task(
        usage_service.track_chat_usage,
        user_id=current_user.get("user_id"),
        ...
    )
    
    return result
```

## Testing Strategy

With separated tracking:

```python
# tests/test_chat.py
async def test_chat_without_tracking():
    # Test business logic in isolation
    mock_tracker = Mock()
    result = await chat_interface.send_message(...)
    assert result["success"] == True

# tests/test_tracking.py
async def test_usage_tracking():
    # Test tracking logic separately
    service = UsageTrackingService()
    await service.track_chat_usage(...)
    # Assert tracking was recorded
```

## Monitoring & Observability

With centralized tracking:
- Add metrics collection (Prometheus/OpenTelemetry)
- Add structured logging
- Add performance monitoring
- Add cost alerts

## Summary

The norm in production systems is to:
1. **Separate concerns** - Business logic vs tracking
2. **Use service layers** - Dedicated tracking service
3. **Make it async** - Don't block main operations
4. **Centralize configuration** - One place for tracking rules
5. **Make it testable** - Mock tracking in tests

This structure scales better and is easier to maintain as the application grows.