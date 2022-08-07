import bpy, os
from subprocess import check_call

bl_info = {
    'name': 'SFM scale flexes generator',
    'blender': (3, 2, 1)
}

class CrowbarShapekeyCleanerOperator(bpy.types.Operator):    
    bl_idname = 'opr.crowbar_shapekey_cleaner'
    bl_label = 'Cleanup Crobar shape keys'
    bl_description = "Removes _L _R suffixes from shape key names. Needed for restoration with controller source file"
    
    def execute(self, context):
        obj = bpy.context.active_object
        for key in obj.data.shape_keys.key_blocks:
            if '+' in key.name:
                new_name = key.name.split('+')[0]
                new_name.replace("L_", "_")
                if (new_name[-1] == 'L'):
                    new_name = new_name[:-1]
                key.name = new_name
            
        return {'FINISHED'}
        
class ExaggerateShapeKeysOperator(bpy.types.Operator):    
    bl_idname = 'opr.exaggerate_shapekeys_operator'
    bl_label = 'Exaggerate shape keys'
    bl_description = 'Multiplies upper bounds of all shape keys on the selected mesh by a given number'
    
    def execute(self, context):
        VALUE = context.scene.exaggeration_multiplier
        selection = bpy.context.active_object
        keys = selection.data.shape_keys.key_blocks
        for key in keys[1:]:
            key.slider_max = VALUE
            key.value = VALUE
            name = key.name
            new_key = selection.shape_key_add(from_mix=True)
            selection.shape_key_remove(key)
            new_key.name = name

        return {'FINISHED'}

class RemoveBoneScaleShapeKeysOperator(bpy.types.Operator):
    bl_idname = "opr.remove_bone_scale_shapekeys_operator"
    bl_label = "Remove bone scaling shape keys"
    bl_description = "Remove bone scaling shape keys.\n\nWith mesh selected, shift-select armature and enter pose mode to pick which bones to remove shape keys for"

    def execute(self, context):
        bone_names = [bone.name.replace("_","-").replace(" ","-") for bone in bpy.context.selected_pose_bones]
        selection = bpy.context.selected_objects[0 if bpy.context.active_object == bpy.context.selected_objects[1] else 1]
        keys = selection.data.shape_keys.key_blocks
        for key in keys[1:]:
            if key.name[:-6] in bone_names and ("--pos" in key.name or "--neg" in key.name ):
                selection.shape_key_remove(key)

        return {'FINISHED'}

class RemoveObjectScaleShapeKeysOperator(bpy.types.Operator):
    bl_idname = "opr.remove_object_scale_shapekeys_operator"
    bl_label = "Remove object scaling shape keys"
    bl_description = "Remove object scaling shape keys"

    def execute(self, context):
        selection = bpy.context.active_object
        keys = selection.data.shape_keys.key_blocks
        for key in keys[1:]:
            name = selection.name.replace("_","-").replace(" ","-")
            if (name+"--pos" in key.name or name+"--neg" in key.name ):
                selection.shape_key_remove(key)

        return {'FINISHED'}
    
class GenerateBoneScaleShapeKeysOperator(bpy.types.Operator):    
    bl_idname = 'opr.generate_bone_scale_shapekeys_operator'
    bl_label = 'Generate scale shape keys'
    bl_description = 'Generates shape keys for negative and positive bone scaling on specified axis for a selected model.\n\nWith mesh selected, shift-select armature and enter pose mode to pick which bones to generate shape keys for'
    
    def execute(self, context):
        POSITIVE_SCALING = context.scene.positive_scaling
        NEGATIVE_SCALING = context.scene.negative_scaling
        ENABLE_X = context.scene.enable_x
        ENABLE_Y = context.scene.enable_y
        ENABLE_Z = context.scene.enable_z
        MERGE_KEYS = context.scene.enable_key_merge
        
        bone_names = [bone.name for bone in bpy.context.selected_pose_bones]
        active_bone_name = bpy.context.active_bone.name
        obj = bpy.context.selected_objects[0 if bpy.context.active_object == bpy.context.selected_objects[1] else 1]
        if obj.data.shape_keys == None:
            obj.shape_key_add(name="Basis")

        # Duplicate armature
        og_arm = bpy.context.active_object
        bpy.ops.object.posemode_toggle()
        obj.select_set(False)
        bpy.context.view_layer.objects.active = og_arm
        og_arm.select_set(True)
        bpy.ops.object.duplicate()
        arm = bpy.context.object
        obj.modifiers["Armature"].object = arm
    
        # Clear bones parents
        bpy.ops.object.editmode_toggle()
        for bone in arm.data.edit_bones:
            bone.parent = None
        bpy.ops.object.editmode_toggle()

        # Make shape keys
        arm.select_set(False)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        axis = []
        if ENABLE_X: axis.append(('X', 0))
        if ENABLE_Y: axis.append(('Y', 1))
        if ENABLE_Z: axis.append(('Z', 2))
        scaling = [POSITIVE_SCALING, NEGATIVE_SCALING]
        new_keys = []
        for bone in arm.pose.bones:
            if bone.name in bone_names:
                # Delete existing keys
                bone_name = bone.name.replace("_","-").replace(" ","-")
                for key in obj.data.shape_keys.key_blocks:
                    if bone_name == key.name[:-6]:
                        obj.shape_key_remove(key)
                for a in axis:
                    for j in range(len(scaling)):
                        bone.scale[a[1]] = scaling[j]
                        bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier="Armature")
                        name = bone_name + '--{}{}'.format('pos' if j == 0 else 'neg', a[0])
                        new_key = obj.data.shape_keys.key_blocks[-1]
                        new_key.name = name
                        new_keys.append(new_key)
                        bone.scale[a[1]] = 1
        if MERGE_KEYS:
            for start in range(len(axis)*2):
                key_suffix = new_keys[start].name[-6:]
                for i in range(start, len(new_keys), len(axis)*2):
                    new_keys[i].value = 1
                new_key = obj.shape_key_add(name=active_bone_name.replace("_","-").replace(" ","-") + key_suffix, from_mix=True)
                for i in range(start, len(new_keys), len(axis)*2):
                    obj.shape_key_remove(new_keys[i])
                new_key.name = new_key.name[:-4]
        
        # Remove duplicated armature, restore the original one
        bpy.data.objects.remove(arm)
        obj.modifiers["Armature"].object = og_arm
        og_arm.select_set(True)
        bpy.context.view_layer.objects.active = og_arm
        bpy.ops.object.posemode_toggle()


        return {'FINISHED'} 

class GenerateObjectScaleShapekeyOperator(bpy.types.Operator):    
    bl_idname = 'opr.generate_object_scale_shapekeys_operator'
    bl_label = 'Generate object scale shape keys'
    bl_description = 'Generates shape keys for negative and positive object scaling on specified axis for a selected model'
    
    def execute(self, context):
        POSITIVE_SCALING = context.scene.positive_scaling
        NEGATIVE_SCALING = context.scene.negative_scaling
        ENABLE_X = context.scene.enable_x
        ENABLE_Y = context.scene.enable_y
        ENABLE_Z = context.scene.enable_z

        obj = bpy.context.active_object
        if obj.data.shape_keys == None:
            obj.shape_key_add(name="Basis")
        for key in obj.data.shape_keys.key_blocks:
            if obj.name.replace("_","-").replace(" ","-") in key.name:
                obj.shape_key_remove(key)

        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.context.object.active_shape_key_index = len(obj.data.shape_keys.key_blocks) - 1

        axis = []
        if ENABLE_X: axis.append(('X', 0))
        if ENABLE_Y: axis.append(('Y', 1))
        if ENABLE_Z: axis.append(('Z', 2))
        scaling = [POSITIVE_SCALING, NEGATIVE_SCALING]
        for a in axis:
            for j in range(len(scaling)):
                key = obj.shape_key_add(from_mix=False)
                bpy.context.object.active_shape_key_index += 1
                name = '{}--{}{}'.format(obj.name.replace("_","-").replace(" ","-"),'pos' if j == 0 else 'neg', a[0])
                key.name = name

                bpy.ops.object.editmode_toggle()
                bpy.ops.mesh.select_all(action='SELECT')
                scale_value = [1, 1, 1]
                scale_value[a[1]] *= scaling[j]
                # print(scale_value)
                bpy.ops.transform.resize(value=scale_value, orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', constraint_axis=(False, True, False), mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False)
                bpy.ops.object.editmode_toggle()

        return {'FINISHED'}

class GenerateControllersOperator(bpy.types.Operator):    
    bl_idname = 'opr.generate_controllers_operator'
    bl_label = 'Create HWM controllers file using generated shape keys IDs based on a given .dmx file'     
    bl_description = 'Generates controller block containing controllers for regular shape keys, HWM (if specified) and scaling controllers '

    def parse_dmx_controllers(self, DMX_FILE_PATH):
        controls = []
        with open(DMX_FILE_PATH, 'r') as dmx:
                    line = dmx.readline()
                    while line:
                        if "DmeCombinationInputControl" in line:
                            dmx.readline()
                            line = dmx.readline()
                            morph = {}
                            while "}" not in line.strip():
                                #print(line)
                                data = line.strip().replace('"', '').split()
                                if len(data) == 3:
                                    morph[data[0]] = [data[1], data[2]]
                                else:
                                    dmx.readline()
                                    line = dmx.readline()  
                                    arr = []
                                    while "]" not in line.strip():
                                        arr.append(line.strip().replace('"', '').replace(",", ""))
                                        line = dmx.readline()  
                                    morph[data[0]] = [data[1], arr]
                                line = dmx.readline()  
                            controls.append(morph)
                        line = dmx.readline()
        return controls
    
    def execute (self, context):
        global controllers_count
        controllers_count = 0
        DMX_FILE_PATH = context.scene.dmx_file_path
        CONTROLLER_SOURCE = context.scene.controller_source
        CONTROLLER_OUTPUT = context.scene.controller_output
        if CONTROLLER_SOURCE == None:
            return {'CANCELLED'}
        if CONTROLLER_OUTPUT == None:
            CONTROLLER_OUTPUT = bpy.data.texts.new(CONTROLLER_SOURCE.name + "-new")
            context.scene.controller_output = CONTROLLER_OUTPUT
            
        # Write controller file header
        if (len(CONTROLLER_OUTPUT.lines) != 0):
            CONTROLLER_OUTPUT.clear()
            # Return if the source file isn't a dmx controller list
            if (CONTROLLER_OUTPUT.lines[0].body != '<!-- dmx encoding keyvalues2 1 format model 1 -->'):
                return {'CANCELLED'}
        for line in CONTROLLER_SOURCE.lines:
            if ("element_array" in line.body):
                CONTROLLER_OUTPUT.write(line.body + "\n\t\t[\n")
                break
            else:
                CONTROLLER_OUTPUT.write(line.body + "\n")
                
        # Get shape key ids
        controller_ids = {}
        for i in range(len(CONTROLLER_SOURCE.lines)):
            if "DmeCombinationInputControl" in CONTROLLER_SOURCE.lines[i].body:
                id = CONTROLLER_SOURCE.lines[i+2].body.strip().split()[2].replace('"', '')
                name = CONTROLLER_SOURCE.lines[i+3].body.strip().split()[2].replace('"', '')
                controller_ids[name] = id   
        controller_ids_keys = list(controller_ids.keys()) # used later to create controllers for non-hwm and non-scale shape keys
        # print(controller_ids)

        # If present, parse HWM controllers
        if DMX_FILE_PATH != '':
            controls = self.parse_dmx_controllers(DMX_FILE_PATH)
            for c in controls:
                name = c['rawControlNames'][1][0]
                if (name in controller_ids_keys):
                    # remove key names from list
                    for control in c['rawControlNames'][1]:
                        if control in controller_ids_keys:
                            controller_ids_keys.remove(control)
                    # write controller
                    CONTROLLER_OUTPUT.write('\t\t\t"DmeCombinationInputControl"\n\t\t\t{\n')
                    c['id'][1] = controller_ids[name]
                    for key in c.keys():
                        CONTROLLER_OUTPUT.write('\t\t\t\t"{}" "{}"'.format( key, c[key][0]))
                        if "array" not in c[key][0]:
                            CONTROLLER_OUTPUT.write(' "{}"\n'.format(c[key][1]))
                        else:
                            CONTROLLER_OUTPUT.write('\n\t\t\t\t[\n')
                            for i in range(len(c[key][1])):
                                CONTROLLER_OUTPUT.write('\t\t\t\t\t"{}"'.format(c[key][1][i]))
                                CONTROLLER_OUTPUT.write(',\n' if i+1 != len(c[key][1]) else '')
                            CONTROLLER_OUTPUT.write('\n\t\t\t\t]\n')
                    CONTROLLER_OUTPUT.write("\t\t\t},\n")
                    controllers_count += 1

        # Parse scale controllers      
        keys = controller_ids_keys.copy()
        # print(keys)
        for key in keys:
            if "--neg" in key:
                controller_ids_keys.remove(key)
                name = key[:-4] + key[-1]
                controller_ids_keys.remove(name[:-1] + "pos" + name[-1])
                CONTROLLER_OUTPUT.write("\t"*3 + '"DmeCombinationInputControl"\n')
                CONTROLLER_OUTPUT.write("\t"*3 + "{\n" )
                CONTROLLER_OUTPUT.write("\t"*4 + '"id" "elementid" "{}"\n'.format(controller_ids[key]))
                CONTROLLER_OUTPUT.write("\t"*4 + '"name" "string" "{}"\n'.format(name[:-1] + "scale" + name[-1]))
                CONTROLLER_OUTPUT.write("\t"*4 + '"rawControlNames" "string_array"\n')
                CONTROLLER_OUTPUT.write("\t"*4 + "[\n")
                CONTROLLER_OUTPUT.write("\t"*5 + '"{}",\n'.format(name[:-1] + "neg" + name[-1]))
                CONTROLLER_OUTPUT.write("\t"*5 + '"{}"\n'.format(name[:-1] + "pos" + name[-1]))
                CONTROLLER_OUTPUT.write("\t"*4 + "]\n")
                CONTROLLER_OUTPUT.write("\t"*4 + '"stereo" "bool" "0"\n')
                CONTROLLER_OUTPUT.write("\t"*4 + '"eyelid" "bool" "0"\n')
                CONTROLLER_OUTPUT.write("\t"*4 + '"wrinkleScales" "float_array"\n')
                CONTROLLER_OUTPUT.write("\t"*4 + '[\n')
                CONTROLLER_OUTPUT.write("\t"*5 + '"0",\n')
                CONTROLLER_OUTPUT.write("\t"*5 + '"0"\n')
                CONTROLLER_OUTPUT.write("\t"*4 + ']\n')
                CONTROLLER_OUTPUT.write("\t"*3 + '},\n')
                controllers_count += 1

        # Generate controllers for the remaining keys
        for key in controller_ids_keys:
            CONTROLLER_OUTPUT.write("\t"*3 + '"DmeCombinationInputControl"\n')
            CONTROLLER_OUTPUT.write("\t"*3 + "{\n" )
            CONTROLLER_OUTPUT.write("\t"*4 + '"id" "elementid" "{}"\n'.format(controller_ids[key]))
            CONTROLLER_OUTPUT.write("\t"*4 + '"name" "string" "{}"\n'.format(key))
            CONTROLLER_OUTPUT.write("\t"*4 + '"rawControlNames" "string_array" ["{}"]\n'.format(key))
            CONTROLLER_OUTPUT.write("\t"*4 + '"stereo" "bool" "0"\n')
            CONTROLLER_OUTPUT.write("\t"*4 + '"eyelid" "bool" "0"\n')
            CONTROLLER_OUTPUT.write("\t"*4 + '"wrinkleScales" "float_array" ["0.0"]\n')
            CONTROLLER_OUTPUT.write("\t"*3 + "},\n" )
            controllers_count += 1

        print("Generated {} controllers (128 supported)".format(controllers_count))

        # Write controller file footer
        CONTROLLER_OUTPUT.write("\t\t]\n")
        vectors = ['\t\t"controlValues" "vector3_array" [', "\t\t" + '"controlValuesLagged" "vector3_array" [']
        for v in vectors:
            CONTROLLER_OUTPUT.write(v)
            for i in range(controllers_count):
                CONTROLLER_OUTPUT.write('"0.0 0.0 0.5"')
                CONTROLLER_OUTPUT.write(', ' if i+1 < controllers_count else ']\n')
        CONTROLLER_OUTPUT.write("\t\t" + '"usesLaggedValues" "bool" "0"\n')
        CONTROLLER_OUTPUT.write("\t\t" + '"dominators" "element_array" [ ]\n')
        CONTROLLER_OUTPUT.write("\t\t" + '"targets" "element_array" [ ]\n')
        CONTROLLER_OUTPUT.write("\t}\n")
        CONTROLLER_OUTPUT.write("}\n")
        
        return {'FINISHED'}

FILTER_OUT = ["hlp_", "index", "middle", "ring", "pinky", "thumb", "weapon"]
READY_TO_GENERATE = False
controllers_count = 0

def check_controller_file(self, context):
    global READY_TO_GENERATE
    # print(context.scene.controller_source, context.scene.controller_output)
    READY_TO_GENERATE = context.scene.controller_source != None

PROPS = [
    ('exaggeration_multiplier', bpy.props.FloatProperty(name="Exaggeration multiplier", default=10)),
    ('positive_scaling', bpy.props.FloatProperty(name="Upper bound", default=5)),
    ('negative_scaling', bpy.props.FloatProperty(name="Lower bound", default=0)),
    ('dmx_file_path', bpy.props.StringProperty(name="Controller source", subtype="FILE_PATH")),
    ('controller_source', bpy.props.PointerProperty(type=bpy.types.Text, name="ID source", update=check_controller_file)),
    ('controller_output', bpy.props.PointerProperty(type=bpy.types.Text, name="Controller output")),
    ('enable_x', bpy.props.BoolProperty(name='Enable scaling for X axis', default=True)),
    ('enable_y', bpy.props.BoolProperty(name='Enable scaling for Y axis', default=True)),
    ('enable_z', bpy.props.BoolProperty(name='Enable scaling for Z axis', default=True)),
    ('enable_key_merge', bpy.props.BoolProperty(name='Merge shape keys', description="Make a single set of shape keys for selected bones", default=False)),
]     

class ScaleFlexesPanel(bpy.types.Panel):
    bl_idname = 'VIEW3D_PT_sfm_scale_flexes_panel'
    bl_label = 'SFM bone scale flexes generator'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
            
    def draw(self, context):
        selected_objects = bpy.context.selected_objects
        OBJECT_SELECTED = len(selected_objects) != 0
        BONE_SCALING_MODE = False        
        if OBJECT_SELECTED:
            active_object = bpy.context.active_object
            OBJECT_SELECTED = active_object.type == 'MESH'
            if (len(selected_objects) == 2):
                second_object = bpy.context.selected_objects[0 if bpy.context.active_object == bpy.context.selected_objects[1] else 1]
                BONE_SCALING_MODE = active_object.type == "ARMATURE" and second_object.type == 'MESH' and bpy.context.mode == 'POSE'
        # ----------
        box = self.layout.box()
        box.enabled = OBJECT_SELECTED
        box.operator('opr.crowbar_shapekey_cleaner', text='Clean up Crowbar\'s stereo shape key names')

        row = box.row()
        row.prop(context.scene, 'exaggeration_multiplier')
        row.operator('opr.exaggerate_shapekeys_operator', text='Exaggerate shape keys')
        # ----------
        box = self.layout.box()
        box.enabled = OBJECT_SELECTED or BONE_SCALING_MODE

        row = box.row()
        col = row.column()
        col.prop(context.scene, 'positive_scaling')
        col.prop(context.scene, 'negative_scaling')
        col = row.column()

        col.prop(context.scene, 'enable_x')
        col.prop(context.scene, 'enable_y')
        col.prop(context.scene, 'enable_z')

        row = box.row()
        col = row.column()
        col.enabled = BONE_SCALING_MODE
        box = col.box()
        box.label(text="Bone scaling")
        box.prop(context.scene, 'enable_key_merge')
        box.operator('opr.generate_bone_scale_shapekeys_operator', text='Generate shape keys')
        box.operator('opr.remove_bone_scale_shapekeys_operator', text='Remove shape keys')
        col = row.column()
        col.enabled = OBJECT_SELECTED and not BONE_SCALING_MODE
        box = col.box()
        box.label(text="Object scaling")
        box.operator('opr.generate_object_scale_shapekeys_operator', text='Generate shape keys')
        box.operator('opr.remove_object_scale_shapekeys_operator', text='Remove shape keys')
        # ----------
        box = self.layout.box()
        box.prop(context.scene, 'controller_source')
        box.prop(context.scene, 'controller_output')
        box.prop(context.scene, 'dmx_file_path')
        row = box.row()
        row.operator('opr.generate_controllers_operator', text='Generate controllers')
        row.enabled = READY_TO_GENERATE
        # ----------
        if controllers_count != 0:
            self.layout.label(text="{} controllers generated.".format(controllers_count))


CLASSES = [
    ScaleFlexesPanel,
    CrowbarShapekeyCleanerOperator,
    ExaggerateShapeKeysOperator,
    GenerateBoneScaleShapeKeysOperator,
    GenerateObjectScaleShapekeyOperator,
    RemoveObjectScaleShapeKeysOperator,
    RemoveBoneScaleShapeKeysOperator,
    GenerateControllersOperator
]

def register():
    for (prop_name, prop_value) in PROPS:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for c in CLASSES:
        bpy.utils.register_class(c)

def unregister():
    for (prop_name, _) in PROPS:
        delattr(bpy.types.Scene, prop_name)
        
    for c in CLASSES:
        bpy.utils.unregister_class(c)


if __name__ == '__main__':
    register()