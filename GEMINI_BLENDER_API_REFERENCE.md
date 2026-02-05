# 📚 Gemini's Blender 5.0.1 API Reference - EXACT ATTRIBUTES

This is the complete guide Gemini uses to generate animations autonomously. Share this when asking for complex scenes.

---

## ⚡ QUICK SUMMARY

When you ask Gemini to create something like a basketball player, it now has:
- ✅ Exact metaball setup instructions
- ✅ Exact keyframe animation syntax
- ✅ Exact material socket names (Blender 5.0.1)
- ✅ Exact modifier syntax
- ✅ Exact camera/lighting setup
- ✅ Common patterns & mistakes to avoid

---

## 🎯 HOW TO REQUEST ANIMATIONS FROM GEMINI

**Example Request 1: Simple**
```
"Create a spinning golden cube that grows from small to large over 100 frames, with professional lighting"
```

**Example Request 2: Complex (What you did)**
```
"Create a realistic human stickman using metaballs with perfect proportions. 
Add a basketball and hoop. Animate the player doing a crouch-to-jump-to-shoot sequence 
with the ball releasing from the hand at frame 51 and entering the hoop at frame 71. 
Add celebration jumps with arms up afterward. Use skin-tone material with Transmission Weight 
and Specular IOR Level. Add professional lighting and camera."
```

**Example Request 3: Character**
```
"Create a dragon character using metaballs. Head with horns, long neck, 4 legs, wings, and tail. 
Make it breathe fire (emission from mouth). Animate flying motion with wing flapping. 
Use metallic scales texture. Set timeline to 200 frames total."
```

---

## 📋 METABALL EXACT ATTRIBUTES

```python
# Create metaball
bpy.ops.object.metaball_add(type='BALL', location=(x, y, z))
mball = bpy.context.active_object.data

# Configuration attributes
mball.resolution = 0.15       # Range: 0.10-0.30 (lower = smoother)
mball.threshold = 0.6         # Range: 0.4-0.8 (controls blending)
mball.elements.clear()        # Remove default element

# Add elements
elem = mball.elements.new()
elem.co = (x, y, z)           # Position as tuple
elem.radius = 0.5             # Size (0.2-1.0 typical)
elem.stiffness = 1.0          # Optional: hardness
elem.use_negative = False     # Optional: hollow blob
```

---

## 🎬 KEYFRAME ANIMATION EXACT SYNTAX

```python
# LOCATION (position)
obj.location = (x, y, z)
obj.keyframe_insert(data_path='location', frame=frame_number)

# ROTATION (Euler angles in radians)
obj.rotation_euler = (x_rad, y_rad, z_rad)
obj.keyframe_insert(data_path='rotation_euler', frame=frame_number)

# SCALE
obj.scale = (x, y, z)
obj.keyframe_insert(data_path='scale', frame=frame_number)

# TIMELINE SETUP
bpy.context.scene.frame_end = 300  # Total frames
```

**Example: Basketball player jump**
```python
# Frame 1: Standing
player.location = (0, 0, 0)
player.keyframe_insert(data_path='location', frame=1)

# Frame 20: Crouch
player.location = (0, 0, -0.5)
player.keyframe_insert(data_path='location', frame=20)

# Frame 40: Peak jump
player.location = (0, 0, 2.5)
player.keyframe_insert(data_path='location', frame=40)

# Frame 70: Landing
player.location = (0, 0, 0)
player.keyframe_insert(data_path='location', frame=70)
```

---

## 🎨 MATERIAL SOCKET NAMES (BLENDER 5.0.1 EXACT)

```python
# Create material
mat = bpy.data.materials.new(name="SkinMaterial")
mat.use_nodes = True
mat.node_tree.nodes.clear()

# Create shader
bsdf = mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

# EXACT Socket Names (These MUST be correct):
bsdf.inputs['Base Color'].default_value = (R, G, B, A)           # Color (0-1 each)
bsdf.inputs['Roughness'].default_value = 0.5                    # Smoothness (0=glossy, 1=rough)
bsdf.inputs['Metallic'].default_value = 1.0                     # Metal (0=non-metal, 1=full metal)
bsdf.inputs['Specular IOR Level'].default_value = 0.5           # ✅ NOT 'Specular'
bsdf.inputs['Transmission Weight'].default_value = 0.8          # ✅ NOT 'Transmission'
bsdf.inputs['Coat Weight'].default_value = 0.5                  # ✅ NOT 'Clearcoat'
bsdf.inputs['Emission Color'].default_value = (R, G, B, A)      # ✅ NOT 'Emission'
bsdf.inputs['Subsurface Weight'].default_value = 0.1            # Light penetration
bsdf.inputs['IOR'].default_value = 1.45                         # Index of refraction (glass=1.45)
```

**Preset Materials:**

```python
# SKIN (Human)
bsdf.inputs['Base Color'].default_value = (0.95, 0.78, 0.65, 1.0)
bsdf.inputs['Subsurface Weight'].default_value = 0.1
bsdf.inputs['Roughness'].default_value = 0.25
bsdf.inputs['Specular IOR Level'].default_value = 0.4
bsdf.inputs['Transmission Weight'].default_value = 0.05

# GLASS (Transparent)
bsdf.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)
bsdf.inputs['Transmission Weight'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.0
bsdf.inputs['IOR'].default_value = 1.45

# METAL (Shiny Steel)
bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
bsdf.inputs['Metallic'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.1

# PLASTIC (Matte)
bsdf.inputs['Base Color'].default_value = (0.2, 0.2, 0.2, 1.0)
bsdf.inputs['Roughness'].default_value = 0.6
bsdf.inputs['Specular IOR Level'].default_value = 0.2

# RUBBER (Basketball)
bsdf.inputs['Base Color'].default_value = (1.0, 0.5, 0.0, 1.0)
bsdf.inputs['Roughness'].default_value = 0.35
bsdf.inputs['Specular IOR Level'].default_value = 0.35

# GOLD
bsdf.inputs['Base Color'].default_value = (1.0, 0.8, 0.0, 1.0)
bsdf.inputs['Metallic'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.2
```

---

## 🔨 MODIFIERS EXACT SYNTAX

```python
# Add modifier
modifier = obj.modifiers.new(name="ModifierName", type='MODIFIER_TYPE')

# SUBDIVISION SURFACE (smoothing)
mod = obj.modifiers.new(name="Subsurf", type='SUBSURF')
mod.levels = 2                    # Viewport subdivisions
mod.render_levels = 4             # Render subdivisions

# BEVEL (edge chamfering)
mod = obj.modifiers.new(name="Bevel", type='BEVEL')
mod.width = 0.05                  # Bevel size
mod.angle_limit = 0.523599        # 30 degrees

# ARRAY (duplication)
mod = obj.modifiers.new(name="Array", type='ARRAY')
mod.count = 5                     # How many copies
mod.use_relative_offset = True
mod.relative_offset_displace = (2.0, 0, 0)  # Spacing

# BOOLEAN (combine/cut)
mod = obj.modifiers.new(name="Boolean", type='BOOLEAN')
mod.operation = 'UNION'           # 'UNION', 'DIFFERENCE', 'INTERSECT'
mod.object = target_object        # Object to combine with

# REMESH (retopology)
mod = obj.modifiers.new(name="Remesh", type='REMESH')
mod.mode = 'SMOOTH'               # 'BLOCKS', 'SMOOTH', 'VOXEL'
mod.voxel_size = 0.05             # Resolution

# DISPLACE (surface deformation)
mod = obj.modifiers.new(name="Displace", type='DISPLACE')
mod.strength = 0.5                # Intensity
mod.texture = texture_object      # Texture to use

# ARRAY + BOOLEAN EXAMPLE (Fence)
fence_post = create_cube(scale=0.1)
mod = fence_post.modifiers.new(name="Array", type='ARRAY')
mod.count = 10
mod.relative_offset_displace = (1.2, 0, 0)
```

---

## 📷 CAMERA & LIGHTING EXACT ATTRIBUTES

```python
# CAMERA
bpy.ops.object.camera_add(location=(x, y, z))
cam = bpy.context.active_object
cam.rotation_euler = (x_rad, y_rad, z_rad)  # Euler angles
cam.data.lens = 50                           # Focal length (mm)
cam.data.sensor_width = 36                   # Sensor size
bpy.context.scene.camera = cam               # Set active camera

# LIGHTING

# SUN LIGHT (Directional, like sunlight)
bpy.ops.object.light_add(type='SUN', location=(x, y, z))
sun = bpy.context.active_object
sun.data.energy = 2.5                        # Brightness
sun.data.angle = 0.5                         # Size (softness)

# AREA LIGHT (Soft shadows, like window)
bpy.ops.object.light_add(type='AREA', location=(x, y, z))
area = bpy.context.active_object
area.data.energy = 1.5
area.data.size = 4.0                         # Light size
area.data.shape = 'SQUARE'                   # 'SQUARE' or 'RECTANGLE'

# POINT LIGHT (Omnidirectional, like bulb)
bpy.ops.object.light_add(type='POINT', location=(x, y, z))
point = bpy.context.active_object
point.data.energy = 1.0
point.data.shadow_soft_size = 0.5            # Soft shadow radius

# THREE-POINT LIGHTING SETUP
# Key light (main)
bpy.ops.object.light_add(type='SUN', location=(5, -5, 8))
key = bpy.context.active_object
key.data.energy = 3.0

# Fill light (soften shadows)
bpy.ops.object.light_add(type='AREA', location=(-5, 5, 6))
fill = bpy.context.active_object
fill.data.energy = 1.2
fill.data.size = 5

# Back light (rim light)
bpy.ops.object.light_add(type='POINT', location=(0, -8, 4))
back = bpy.context.active_object
back.data.energy = 0.8
```

---

## 🚫 CRITICAL MISTAKES (WILL ERROR)

```python
# ❌ WRONG - These will crash in Blender 5.0.1

bsdf.inputs['Specular']                     # ❌ Use: 'Specular IOR Level'
bsdf.inputs['Transmission']                 # ❌ Use: 'Transmission Weight'
bsdf.inputs['Clearcoat']                    # ❌ Use: 'Coat Weight'
bsdf.inputs['Emission']                     # ❌ Use: 'Emission Color'

obj.data.fcurves                            # ❌ Use: obj.keyframe_insert()
action.curves                               # ❌ Use: obj.keyframe_insert()
action.fcurves                              # ❌ Use: obj.keyframe_insert()

psys.settings.scale                         # ❌ Use: psys.settings.particle_size
particle.velocity = (1, 2, 3)               # ❌ Use keyframes for initial motion
rb.use_initial_velocity = True              # ❌ Use keyframes for initial motion
rw.animation_data.action                    # ❌ Check if animation_data is not None first

obj.align = 'WORLD_ORIGIN'                  # ❌ Use: obj.align = 'WORLD'
modifier.type = 'EXTRUDE'                   # ❌ Use: type = 'SOLIDIFY'
modifier.type = 'SHRINKWRAP'                # ❌ Make sure object exists for wrap
```

---

## ✨ COMMON PATTERNS

**Loop animation (spinning)**
```python
import math
for frame in range(1, 101):
    obj.rotation_euler.z = (frame / 100.0) * math.pi * 2  # Full rotation
    obj.keyframe_insert(data_path='rotation_euler', frame=frame)
```

**Smooth shading**
```python
bpy.context.view_layer.objects.active = obj
bpy.ops.object.shade_smooth()
```

**Join objects**
```python
bpy.context.view_layer.objects.active = parent
parent.select_set(True)
child.select_set(True)
bpy.ops.object.join()
```

**Find Principled BSDF safely**
```python
bsdf = [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
```

**Animate material property**
```python
bsdf.inputs['Emission Strength'].default_value = 0.0
bsdf.inputs['Emission Strength'].keyframe_insert('default_value', frame=1)

bsdf.inputs['Emission Strength'].default_value = 2.0
bsdf.inputs['Emission Strength'].keyframe_insert('default_value', frame=50)
```

**Render animation**
```python
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 128
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.filepath = render_dir + '/animation_'
```

---

## 📊 HUMAN PROPORTIONS (Metaball)

For creating realistic humans with metaballs, use these proportions:

```
HEAD:      radius=0.5,   z=7.2
TORSO:     radius=0.9,   z=5.2  (widest part)
HIPS:      radius=0.75,  z=2.8

L_SHOULDER: radius=0.35, x=-1.2, z=5.5
L_UPPER_ARM: radius=0.32, x=-2.2, z=5.0
L_FOREARM:  radius=0.28, x=-3.0, z=5.5
L_HAND:     radius=0.25, x=-3.5, z=6.5

R_SHOULDER: radius=0.35, x=1.2, z=5.5
R_UPPER_ARM: radius=0.32, x=2.2, z=5.0
R_FOREARM:  radius=0.28, x=3.0, z=4.5
R_HAND:     radius=0.25, x=3.5, z=3.8

L_THIGH:   radius=0.42, x=-0.6, z=1.8
L_SHIN:    radius=0.38, x=-0.6, z=0.5
L_FOOT:    radius=0.32, x=-0.6, z=-0.8

R_THIGH:   radius=0.42, x=0.6, z=1.8
R_SHIN:    radius=0.38, x=0.6, z=0.5
R_FOOT:    radius=0.32, x=0.6, z=-0.8
```

---

## 🎯 TEMPLATE: Complete Scene Creation

When asking Gemini for a complex scene, it should now generate something like:

```python
import bpy
import math

# 1. CLEAR & SETUP
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.frame_end = 300

# 2. CREATE GEOMETRY
# (metaballs, meshes, modifiers, etc.)

# 3. CREATE MATERIALS
# (Principled BSDF with correct socket names)

# 4. SETUP ANIMATION
# (keyframe_insert on location, rotation, scale)

# 5. SETUP CAMERA & LIGHTS
# (professional three-point lighting)

# 6. RENDER SETTINGS
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.render.image_settings.file_format = 'PNG'

print("✅ Scene complete!")
```

---

## 🚀 EXAMPLE: Ask Gemini This

```
"Create a glowing crystal tower that grows from ground to sky over 150 frames. 
It should be made of interconnected tetrahedral shapes using metaballs. 
Add blue emission to make it glow. Animate the growth with scale keyframes starting 
at frame 1 with scale (0.1, 0.1, 0.1) and ending at frame 150 with scale (1.0, 1.0, 2.5). 
Use glass material with Transmission Weight 0.9. Add a rotating camera that orbits 
the tower. Set professional lighting with a key light from above and fill light 
from the side. Timeline: 300 frames. Render as PNG sequence."
```

Gemini should now generate complete, working code for this!

---

**This system is now live in main.py. Gemini understands all these attributes and can generate complex animations autonomously.**
