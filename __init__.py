import sys
import os
import bpy
import bpy.props
import re
import json

# Add the 'libs' folder to the Python path
libs_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib")
if libs_path not in sys.path:
    sys.path.append(libs_path)

import openai

from .utilities import *

bl_info = {
    "name": "GPT-4 Blender Assistant",
    "blender": (2, 82, 0),
    "category": "Object",
    "author": "hkust CADGPT",
    "version": (2, 0, 0),
    "location": "3D View > UI > GPT-4 Blender Assistant",
    "description": "Generate Blender Python code using OpenAI's GPT-4 to perform various tasks.",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
}

system_prompt = """You are an assistant made for the purposes of helping the user with Blender, the 3D software. 
- Respond with your answers in markdown (```). 
- Preferably import entire modules instead of bits. 
- Do not perform destructive operations on the meshes. 
- Do not use cap_ends. Do not do more than what is asked (setting up render settings, adding cameras, etc)
- Do not respond with anything that is not Python code.

Example:

user: create 10 cubes in random locations from -10 to 10
assistant:
```
import bpy
import random
bpy.ops.mesh.primitive_cube_add()

#how many cubes you want to add
count = 10

for c in range(0,count):
    x = random.randint(-10,10)
    y = random.randint(-10,10)
    z = random.randint(-10,10)
    bpy.ops.mesh.primitive_cube_add(location=(x,y,z))
```"""


class GPT4_OT_DeleteMessage(bpy.types.Operator):
    bl_idname = "gpt4.delete_message"
    bl_label = "Delete Message"
    bl_options = {"REGISTER", "UNDO"}

    message_index: bpy.props.IntProperty()

    def execute(self, context):
        context.scene.gpt4_chat_history.remove(self.message_index)
        return {"FINISHED"}


class GPT4_OT_ShowResponse(bpy.types.Operator):
    bl_idname = "gpt4.show_debug"
    bl_label = "Full Response"
    bl_options = {"REGISTER", "UNDO"}

    debug: bpy.props.StringProperty(
        name="Debug",
        description="The full response",
        default="",
    )

    def execute(self, context):
        text_name = "GPT4_full_response.py"
        text = bpy.data.texts.get(text_name)
        if text is None:
            text = bpy.data.texts.new(text_name)

        text.clear()
        debug = eval(self.debug)
        text.write(json.dumps(debug, indent=4))

        text_editor_area = None
        for area in context.screen.areas:
            if area.type == "TEXT_EDITOR":
                text_editor_area = area
                break

        if text_editor_area is None:
            text_editor_area = split_area_to_text_editor(context)

        text_editor_area.spaces.active.text = text

        return {"FINISHED"}


class GPT4_OT_ShowCode(bpy.types.Operator):
    bl_idname = "gpt4.show_code"
    bl_label = "Show Code"
    bl_options = {"REGISTER", "UNDO"}

    code: bpy.props.StringProperty(
        name="Code",
        description="The generated code",
        default="",
    )

    def execute(self, context):
        text_name = "GPT4_Generated_Code.py"
        text = bpy.data.texts.get(text_name)
        if text is None:
            text = bpy.data.texts.new(text_name)

        text.clear()
        text.write(self.code)

        text_editor_area = None
        for area in context.screen.areas:
            if area.type == "TEXT_EDITOR":
                text_editor_area = area
                break

        if text_editor_area is None:
            text_editor_area = split_area_to_text_editor(context)

        text_editor_area.spaces.active.text = text

        return {"FINISHED"}


class GPT4_PT_Panel(bpy.types.Panel):
    bl_label = "GPT-4 Blender Assistant"
    bl_idname = "GPT4_PT_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "GPT-4 Assistant"
    bl_ui_units_x = 500

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        column.label(text="Chat history:")
        box = column.box()
        for index, message in enumerate(context.scene.gpt4_chat_history):
            if message.type == "assistant":
                row = box.row()
                row.label(text="Assistant: ")
                delete_message_op = row.operator(
                    "gpt4.delete_message", text="", icon="TRASH", emboss=False
                )
                delete_message_op.message_index = index
                [code, debug] = message.content.split("CADGPTSPLIT2097", 1)
                show_code_op = row.operator("gpt4.show_code", text="Show Code")
                show_code_op.code = code
                show_debug_op = row.operator("gpt4.show_debug", text="Full Response")
                show_debug_op.debug = debug
            elif message.type == "user" and message.label == "shap-e":
                row = box.row()
                row.label(text=f"User: {message.content}")
                import_op = row.operator(
                    "import.obj_operator", text="Import"
                )
                [desc,name] = message.content.split(":", 1)
                import_op.message = name
            elif message.type == "user" and message.label == "gpt":
                row = box.row()
                row.label(text=f"User: {message.content}")
                delete_message_op = row.operator(
                    "gpt4.delete_message", text="", icon="TRASH", emboss=False
                )
                delete_message_op.message_index = index
                retry_question = row.operator("gpt4.retry_question", text="Retry")
                retry_question.message = message.content

        column.separator()

        column.label(text="GPT Model:")
        column.prop(context.scene, "gpt4_model", text="")

        column.label(text="Enter your message:")
        column.prop(context.scene, "gpt4_chat_input", text="")
        button_label = (
            "Please wait...(this might take some time)"
            if context.scene.gpt4_button_pressed
            else "Execute"
        )
        row = column.row(align=True)
        row.operator("gpt4.send_message", text=button_label)
        row.operator("gpt4.clear_chat", text="Clear Chat")
        row.operator("import_scene.obj_operator", text="Import History Model")

        column.separator()


class GPT4_OT_ClearChat(bpy.types.Operator):
    bl_idname = "gpt4.clear_chat"
    bl_label = "Clear Chat"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.scene.gpt4_chat_history.clear()
        return {"FINISHED"}


class GPT4_OT_Execute(bpy.types.Operator):
    bl_idname = "gpt4.send_message"
    bl_label = "Send Message"
    bl_options = {"REGISTER", "UNDO"}

    natural_language_input: bpy.props.StringProperty(
        name="Command",
        description="Enter the natural language command",
        default="",
    )

    def execute(self, context):
        if context.scene.gpt4_model == "Shap-e":
            context.scene.gpt4_button_pressed = True
            model_name = download_model_shap_e(context.scene.gpt4_chat_input)
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
            message = context.scene.gpt4_chat_history.add()
            message.type = "user"
            message.label = "shap-e"
            message.content = context.scene.gpt4_chat_input+":"+model_name

            context.scene.gpt4_chat_input = ""
            context.scene.gpt4_button_pressed = False
            return {"FINISHED"}
        else:
            api_key = get_api_key(context, __name__)
            # if null then set to env key
            if not api_key:
                self.report(
                    {"ERROR"},
                    "No API key detected. Please set the API key in the addon preferences.",
                )
                return {"CANCELLED"}

            context.scene.gpt4_button_pressed = True
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)

            if len(context.scene.gpt4_chat_input) == 0:
                self.report(
                    {"ERROR"},
                    "Please input some command",
                )
                return {"CANCELLED"}

            blender_code, full_res = generate_blender_code(
                context.scene.gpt4_chat_input,
                context.scene.gpt4_chat_history,
                system_prompt,
                api_key,
                context.scene.gpt4_model,
            )

            message = context.scene.gpt4_chat_history.add()
            message.type = "user"
            message.label = "gpt"
            message.content = context.scene.gpt4_chat_input

            # Clear the chat input field
            context.scene.gpt4_chat_input = ""

            if blender_code:
                message = context.scene.gpt4_chat_history.add()
                message.type = "assistant"
                message.label = "gpt"
                message.content = blender_code + "CADGPTSPLIT2097" + str(full_res)

                global_namespace = globals().copy()

            try:
                exec(blender_code, global_namespace)
            except Exception as e:
                self.report({"ERROR"}, f"Error executing generated code: {e}")
                context.scene.gpt4_button_pressed = False
                return {"CANCELLED"}

            context.scene.gpt4_button_pressed = False
            return {"FINISHED"}


class GPT4_OT_Retry(bpy.types.Operator):
    bl_idname = "gpt4.retry_question"
    bl_label = "Retry"
    bl_options = {"REGISTER", "UNDO"}

    message: bpy.props.StringProperty(
        name="message",
        description="Enter your message",
        default="",
    )

    def execute(self, context):
        api_key = get_api_key(context, __name__)

        context.scene.gpt4_button_pressed = True
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)

        blender_code, full_res = generate_blender_code(
            self.message,
            context.scene.gpt4_chat_history,
            system_prompt,
            api_key,
            context.scene.gpt4_model,
        )

        message = context.scene.gpt4_chat_history.add()
        message.type = "user"
        message.content = self.message

        # Clear the chat input field
        context.scene.gpt4_chat_input = ""

        if blender_code:
            message = context.scene.gpt4_chat_history.add()
            message.type = "assistant"
            message.content = blender_code + "CADGPTSPLIT2097" + str(full_res)

            global_namespace = globals().copy()

        try:
            exec(blender_code, global_namespace)
        except Exception as e:
            self.report({"ERROR"}, f"Error executing generated code: {e}")
            context.scene.gpt4_button_pressed = False
            return {"CANCELLED"}

        context.scene.gpt4_button_pressed = False
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(GPT4_OT_Execute.bl_idname)


class GPT4AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    api_key: bpy.props.StringProperty(
        name="API Key",
        description="Enter your OpenAI API Key",
        default="",
        subtype="PASSWORD",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")


class ImportOBJSelect(bpy.types.Operator):
    """import obj file"""

    bl_idname = "import_scene.obj_operator"
    bl_label = "Import OBJ Select"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        obj_files_path = os.path.join(current_file_path, "models\\")
        self.filepath = obj_files_path
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        bpy.ops.import_scene.obj(filepath=self.filepath, axis_forward="-Z", axis_up="Y")
        return {"FINISHED"}
    
class ImportOBJ(bpy.types.Operator):
    """import obj file"""

    bl_idname = "import.obj_operator"
    bl_label = "Import OBJ"
    message: bpy.props.StringProperty(
        name="message",
        description="Enter your message",
        default="",
    )

    def execute(self, context):
        import_model(self.message)
        return {"FINISHED"}


def register():
    bpy.utils.register_class(GPT4AddonPreferences)
    bpy.utils.register_class(GPT4_OT_Execute)
    bpy.utils.register_class(GPT4_OT_Retry)
    bpy.utils.register_class(GPT4_PT_Panel)
    bpy.utils.register_class(GPT4_OT_ClearChat)
    bpy.utils.register_class(GPT4_OT_ShowCode)
    bpy.utils.register_class(GPT4_OT_ShowResponse)
    bpy.utils.register_class(GPT4_OT_DeleteMessage)
    bpy.utils.register_class(ImportOBJSelect)
    bpy.utils.register_class(ImportOBJ)

    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)
    init_props()


def unregister():
    bpy.utils.unregister_class(GPT4AddonPreferences)
    bpy.utils.unregister_class(GPT4_OT_Execute)
    bpy.utils.unregister_class(GPT4_OT_Retry)
    bpy.utils.unregister_class(GPT4_PT_Panel)
    bpy.utils.unregister_class(GPT4_OT_ClearChat)
    bpy.utils.unregister_class(GPT4_OT_ShowCode)
    bpy.utils.unregister_class(GPT4_OT_ShowResponse)
    bpy.utils.unregister_class(GPT4_OT_DeleteMessage)
    bpy.utils.unregister_class(ImportOBJSelect)
    bpy.utils.unregister_class(ImportOBJ)

    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    clear_props()


if __name__ == "__main__":
    register()
