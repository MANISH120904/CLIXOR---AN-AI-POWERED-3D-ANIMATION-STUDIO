# Blender API Common Errors - Quick Reference

## Error 1: TypeError: 'builtin_function_or_method' object is not iterable

### Signs
- Error occurs when looping over object properties
- Stack trace shows `for x in obj.something`

### Common Causes
```python
# ❌ WRONG - These are methods, not iterable
for x in obj.indices
for x in obj.locations
for x in obj.get_modifiers()
```

### Solutions
```python
# ✅ CORRECT - Use actual collections
for obj in bpy.data.objects          # Iterate over all objects
for mat in bpy.data.materials        # Iterate over materials
loc = obj.location                   # Get location directly (Vector)
```

---

## Error 2: RuntimeError: Node type X undefined

### Signs
- Error mentions "Node type ShaderNode..." not found
- Occurs when creating shader nodes

### Common Causes (Blender 5.0)
```python
# ❌ WRONG - These don't exist in Blender 5.0
ShaderNodeTexMusgrave
ShaderNodeTexCellular
```

### Solutions
```python
# ✅ CORRECT - Use available nodes
ShaderNodeTexNoise        # For procedural noise (replaces Musgrave & Cellular)
ShaderNodeTexWave
ShaderNodeTexMagic
ShaderNodeTexVoronoi
ShaderNodeTexGradient
```

### Full Example
```python
material = bpy.data.materials.new("ProcMaterial")
material.use_nodes = True
bsdf = material.node_tree.nodes["Principled BSDF"]

# Add noise texture
noise = material.node_tree.nodes.new(type='ShaderNodeTexNoise')
material.node_tree.links.new(noise.outputs[0], bsdf.inputs['Base Color'])
```

---

## Error 3: AttributeError: X object has no attribute 'animation_data'

### Signs
- Error mentions missing `.animation_data` attribute
- Occurs with `rigidbody_world` or certain object types

### Common Causes
```python
# ❌ WRONG - RigidBodyWorld doesn't have animation_data
bpy.context.scene.rigidbody_world.animation_data
```

### Safe Access Pattern
```python
# ✅ CORRECT - Always check first
if bpy.context.scene.rigidbody_world:
    rbw = bpy.context.scene.rigidbody_world
    if hasattr(rbw, 'animation_data') and rbw.animation_data:
        # Safe to use
        pass
```

### For Physics Animation
```python
# Use keyframes on objects instead of the world
obj.rigid_body.type = 'ACTIVE'
obj.keyframe_insert(data_path='location', frame=1)
obj.location = (0, 0, 5)
obj.keyframe_insert(data_path='location', frame=10)
```

---

## Blender 5.0.1 Critical API Changes

### Principled BSDF Socket Names
| Old Name | New Name |
|----------|----------|
| "Transmission" | "Transmission Weight" |
| "Clearcoat" | "Coat Weight" |
| "Specular" | "Specular IOR Level" |
| "Emission" | "Emission Color" |

### Safe Pattern
```python
bsdf = material.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Transmission Weight"].default_value = 0.5  # ✅ CORRECT
# bsdf.inputs["Transmission"].default_value = 0.5       # ❌ WRONG
```

---

## Debugging Checklist

When code fails:

- [ ] Check if attribute name changed in Blender 5.0
- [ ] Verify you're not trying to iterate over a method
- [ ] If using shader nodes, check they exist with `ShaderNodeTexNoise` fallback
- [ ] For any object access, use `try/except` or `hasattr()` checks
- [ ] Check all collection attributes exist (use Blender's Python console to verify)

---

## Quick Validation Before Execution

Before sending code to Blender, check for:

```python
# Pattern 1: Iteration over wrong thing
import re
bad_patterns = [
    r'for\s+\w+\s+in\s+\w+\.indices',
    r'for\s+\w+\s+in\s+\w+\.locations(?!\s*=)',
]
for pattern in bad_patterns:
    if re.search(pattern, code):
        print("WARNING: Potentially invalid iteration pattern")

# Pattern 2: Deprecated shader nodes
if 'ShaderNodeTexMusgrave' in code or 'ShaderNodeTexCellular' in code:
    print("WARNING: Using deprecated shader node")

# Pattern 3: Unsafe attribute access
if 'rigidbody_world' in code and 'animation_data' in code:
    if 'hasattr' not in code:
        print("WARNING: Unsafe rigidbody_world.animation_data access")
```

---

## Resources

- Blender 5.0 Python API: https://docs.blender.org/api/current/
- Shader Nodes: https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/
- Rigidly Bodies: https://docs.blender.org/manual/en/latest/physics/rigid_body/

## Testing Code

```python
import bpy

# Test 1: Verify object properties exist
print("Testing object properties...")
for obj in bpy.data.objects[:1]:
    print(f"  - location: {obj.location}")
    print(f"  - users_collection: {list(obj.users_collection)}")
    # NOT obj.locations or obj.indices

# Test 2: Verify shader nodes exist
print("Testing shader nodes...")
mat = bpy.data.materials.get("Material")
if mat:
    mat.use_nodes = True
    # Use ShaderNodeTexNoise, NOT ShaderNodeTexMusgrave
    print(f"  - Available node types: {dir(bpy.types)}")

# Test 3: Verify rigidbody_world safety
print("Testing rigidbody_world...")
if bpy.context.scene.rigidbody_world:
    print("  - rigidbody_world exists")
    print(f"  - has animation_data: {hasattr(bpy.context.scene.rigidbody_world, 'animation_data')}")
```
