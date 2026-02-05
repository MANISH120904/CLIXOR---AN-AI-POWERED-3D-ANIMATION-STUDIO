# Blender API Error Fixes

## Issues Fixed

### 1. TypeError: 'builtin_function_or_method' object is not iterable

**Problem**: Code attempted to iterate over non-iterable attributes like `.indices` or `.locations`

**Examples that caused the error**:
```python
for x in obj.indices  # indices is a method, not iterable
for x in obj.locations  # locations is a property, not iterable
```

**Solutions Implemented**:
- Added regex pattern validation in `_validate_and_fix_code()` to detect these patterns
- In `repair_code()`: Replace problematic iterations with safe alternatives:
  - `for x in obj.indices` → `for x in obj.users_collection`
  - `for x in obj.locations` → `for _ in [obj.location]`
- Added error handling with helpful hints in error messages

**Prevention**: AI now instructed to:
- Check if an attribute is callable before iterating
- Use correct collection attributes instead of method references
- Always verify attribute names against Blender API documentation

---

### 2. RuntimeError: Error: Node type ShaderNodeTexMusgrave undefined

**Problem**: Code referenced non-existent Blender 5.0 shader nodes

**Affected Nodes**:
- `ShaderNodeTexMusgrave` - Removed in Blender 5.0
- `ShaderNodeTexCellular` - Removed in Blender 5.0

**Solutions Implemented**:
- Added string replacements in `repair_code()`:
  - `ShaderNodeTexMusgrave` → `ShaderNodeTexNoise`
  - `ShaderNodeTexCellular` → `ShaderNodeTexNoise`
- Pre-execution validation detects these patterns and warns about incompatibility
- Error handler provides specific guidance when shader node errors occur

**Prevention**: AI now instructed to:
- Always use `ShaderNodeTexNoise` for procedural noise textures
- Check available node types for current Blender version
- Avoid assumptions about deprecated shader nodes

---

### 3. AttributeError: 'RigidBodyWorld' object has no attribute 'animation_data'

**Problem**: Code attempted to access non-existent `animation_data` attribute on RigidBodyWorld objects

**Example that caused the error**:
```python
bpy.context.scene.rigidbody_world.animation_data  # Does NOT exist!
```

**Solutions Implemented**:
- Added safe access wrapper in `repair_code()`:
  ```python
  # Wrapped dangerous access with safety checks:
  (bpy.context.scene.rigidbody_world.animation_data if bpy.context.scene.rigidbody_world and hasattr(...) else None)
  ```
- Added specific error handler in `execute_queued_tasks()` that catches this error
- Provides helpful hint: "Use keyframes on object locations/rotations instead"

**Prevention**: AI now instructed to:
- NEVER access `.animation_data` on `rigidbody_world` - it doesn't exist
- Use keyframes on object locations/rotations for physics animation
- Always check attribute existence with `hasattr()` before access

---

## Implementation Details

### 1. Enhanced `repair_code()` Function (backend/main.py)
**Lines 75-108**

Now includes:
- String replacements for all known deprecated/incorrect attributes
- Regex-based fixes for iterator patterns
- Safe wrapping of rigidbody_world attribute access
- Automatic fixes for Blender 5.0.1 API changes

### 2. New Validation Function (blender_bridge/blender_server.py)
**Lines 325-347**

`_validate_and_fix_code()` function:
- Checks for problematic patterns before execution
- Prints warnings about potential issues
- Catches common mistakes early

### 3. Enhanced Error Handling (blender_bridge/blender_server.py)
**Lines 258-307**

Now catches and provides guidance for:
- `TypeError` - Iterator issues
- `RuntimeError` - Shader node errors
- `AttributeError` - Missing attributes (especially animation_data)

### 4. Improved AI Prompts (backend/main.py)
**Lines 144-166**

Enhanced agent instructions now include:
- Explicit warnings about iterator safety
- List of non-existent shader nodes to avoid
- Explicit instructions about RigidBodyWorld limitations
- SAFE ATTRIBUTE ACCESS section with examples

---

## Testing Recommendations

Test cases to verify fixes:

```python
# Test 1: Iterator safety
# Should NOT error on:
for obj in bpy.data.objects:
    print(obj.location)  # Use location directly, not locations

# Test 2: Shader nodes
# Should NOT error on:
mat.use_nodes = True
node = mat.node_tree.nodes.new(type='ShaderNodeTexNoise')  # NOT Musgrave

# Test 3: RigidBody animation
# Should NOT error on:
if bpy.context.scene.rigidbody_world:
    for obj in bpy.data.objects:
        if obj.rigid_body:
            obj.keyframe_insert(data_path='location', frame=1)  # Animate object, not world
```

---

## Summary

All three error types have been addressed through:
1. **Automatic code repair** - Common mistakes are fixed before execution
2. **Pre-execution validation** - Problematic patterns are detected and warned
3. **Better error handling** - Clear, actionable error messages with hints
4. **Improved AI instructions** - LLM now has explicit guidance on avoiding these errors

The system now prevents these errors at multiple stages, making the animation studio more robust and reliable.
