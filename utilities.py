import bpy
import re
import os
import sys
import requests
import json


def get_api_key(context, addon_name):
    preferences = context.preferences
    addon_prefs = preferences.addons[addon_name].preferences
    print(addon_name)
    print(addon_prefs)
    return addon_prefs.api_key


def init_props():
    bpy.types.Scene.gpt4_chat_history = bpy.props.CollectionProperty(
        type=bpy.types.PropertyGroup
    )
    bpy.types.Scene.gpt4_model = bpy.props.EnumProperty(
        name="GPT Model",
        description="Select the GPT model to use",
        items=[
            (
                "gpt-3.5-turbo",
                "GPT-3.5 Turbo (less powerful, cheaper)",
                "Use GPT-3.5 Turbo",
            ),
            ("gpt-4", "GPT-4 (powerful, expensive)", "Use GPT-4"),
        ],
        default="gpt-3.5-turbo",
    )
    bpy.types.Scene.gpt4_chat_input = bpy.props.StringProperty(
        name="Message",
        description="Enter your message",
        default="",
    )
    bpy.types.Scene.gpt4_button_pressed = bpy.props.BoolProperty(default=False)
    bpy.types.PropertyGroup.type = bpy.props.StringProperty()
    bpy.types.PropertyGroup.content = bpy.props.StringProperty()


def clear_props():
    del bpy.types.Scene.gpt4_chat_history
    del bpy.types.Scene.gpt4_chat_input
    del bpy.types.Scene.gpt4_button_pressed


def generate_blender_code(prompt, chat_history, system_prompt, api_key, model):
    modelTag = "gpt-35-turbo"
    if model == "gpt-4":
        modelTag = model
    url = (
        "https://hkust.azure-api.net/openai/deployments/"
        + modelTag
        + "/chat/completions?api-version=2023-07-01-preview"
    )

    headers = {"api-key": api_key}
    messages = [{"role": "system", "content": system_prompt}]
    for message in chat_history[-10:]:
        if message.type == "assistant":
            messages.append(
                {"role": "assistant", "content": "```\n" + message.content + "\n```"}
            )
        else:
            messages.append({"role": message.type.lower(), "content": message.content})

    # Add the current user message
    messages.append(
        {
            "role": "user",
            "content": "Can you please write Blender code for me that accomplishes the following task: "
            + prompt
            + "? \n. Do not respond with anything that is not Python code. Do not provide explanations, make sure it is compilable",
        }
    )
    data = {"messages": messages}

    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(response.json())
    res_json_data = response.json()

    try:
        collected_events = []
        completion_text = ""
        # iterate through the stream of events
        for event in res_json_data:
            #     print(event)
            #     if "role" in event["choices"][0]["delta"]:
            #         # skip
            #         continue
            #     if len(event["choices"][0]["delta"]) == 0:
            #         # skip
            #         continue
            collected_events.append(event)  # save the event response
        #     event_text = event["choices"][0]["delta"]["content"]
        #     completion_text += event_text  # append the text
        #     print(completion_text, flush=True, end="\r")
        choices = res_json_data["choices"]
        for item in choices:
            content = item["message"]["content"]
            completion_text += content
        completion_text = re.findall(r"```(.*?)```", completion_text, re.DOTALL)[0]
        completion_text = re.sub(r"^python", "", completion_text, flags=re.MULTILINE)

        return completion_text, res_json_data
    except IndexError:
        return None


def split_area_to_text_editor(context):
    area = context.area
    for region in area.regions:
        if region.type == "WINDOW":
            override = {"area": area, "region": region}
            bpy.ops.screen.area_split(override, direction="VERTICAL", factor=0.5)
            break

    new_area = context.screen.areas[-1]
    new_area.type = "TEXT_EDITOR"
    return new_area
