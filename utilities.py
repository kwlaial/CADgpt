import bpy
import re
import os
import sys
import requests
import json
from .task import *
import asyncio
import zipfile
from datetime import datetime


def get_api_key(context, addon_name):
    preferences = context.preferences
    addon_prefs = preferences.addons[addon_name].preferences
    return addon_prefs.api_key
    # return "5e5d81163812467f803dcc940340a3ee"


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
            ("Shap-e", "Shap-e (get model directly)", "Use Shap-e"),
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
    bpy.types.PropertyGroup.label = bpy.props.StringProperty()
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
            collected_events.append(event)  # save the event response
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


def unpack(file_path):
    f = zipfile.ZipFile(file_path, "r")
    for file in f.namelist():
        f.extract(file, "./models/")
    f.close()
    return f.namelist()[0]


def get_obj_file(model_path):
    file_names = os.listdir(model_path)
    for file_name in file_names:
        if file_name.endswith(".obj"):
            return file_name
    return False


def download_model_zip(text):
    url = "http://143.89.76.81:8001/get_model/"
    data = {}
    file_path = "./models/Skull.zip"
    down_res = requests.get(url)
    if down_res:
        with open(file_path, "wb") as file:
            file.write(down_res.content)
        res_text = down_res.text

        model_dir_name = unpack(file_path)

        model_dir_path = "./models/" + model_dir_name

        model_name = get_obj_file(model_dir_path)

        if model_name:
            model_path = model_dir_path + model_name

            bpy.ops.wm.obj_import(
                filepath=model_path,
                directory=model_dir_path,
                files=[
                    {
                        "name": model_name,
                        "type": "",
                        "content": "",
                    }
                ],
            )

        return res_text
    # print(down_res.json())
    # task = task.Task(
    #     data,
    #     "test_app_id",
    #     "asset_download",
    #     task_id="",
    #     message="Looking for asset",
    # )
    # task.async_task = asyncio.ensure_future(
    #     do_asset_download(url, text, task, file_path)
    # )


def download_model_shap_e(text):
    url = "http://127.0.0.1:8001/backend/get_model_shap_e"
    data = {"message": text}
    now = datetime.now()
    formatted_time = now.strftime("%Y-%m-%d-%H-%M-%S")
    file_path = "./models/" + formatted_time + ".obj"
    down_res = requests.get(url, params=data)
    if down_res:
        with open(file_path, "wb") as file:
            file.write(down_res.content)
        res_text = down_res.text

        model_name = formatted_time + ".obj"

        if model_name:
            bpy.ops.wm.obj_import(
                filepath=file_path,
                directory="./models",
                files=[
                    {
                        "name": model_name,
                        "type": "",
                        "content": "",
                        "label":""
                    }
                ],
            )

        return model_name


def import_model(text):
    file_path = "./models/" + text
    bpy.ops.wm.obj_import(
        filepath=file_path,
        directory="./models",
        files=[
            {
                "name": text,
                "type": "",
                "content": "",
                "label":""
            }
        ],
    )


async def do_asset_download(url, text, task, file_path):
    if await download_asset(url, text, task, file_path) is not True:
        return


async def download_asset(url, text, task, file_path) -> bool:
    try:
        with open(file_path, "wb") as file:
            resp_text, resp_status = None, -1
            with requests.Session() as session:
                data = {"message": text}
                async with session.get(
                    url,
                    data=json.dumps(data),
                ) as resp:
                    resp_status = resp.status
                    total_length = resp.headers.get("Content-Length")

                    file_size = int(total_length)
                    fsmb = file_size // (1024 * 1024)
                    fskb = file_size % 1024
                    if fsmb == 0:
                        t = "%iKB" % fskb
                    else:
                        t = " %iMB" % fsmb
                    task.change_progress(
                        progress=0, message=f"Downloading {t} {task.data['resolution']}"
                    )
                    downloaded = 0
                    async for chunk in resp.content.iter_chunked(4096 * 32):
                        downloaded += len(chunk)
                        progress = int(100 * downloaded / file_size)
                        task.change_progress(
                            progress=progress,
                            message=f"Downloading {t} {task.data['resolution']}",
                        )
                        file.write(chunk)
                    return True

    except Exception as e:
        msg, detail = extract_error_message(e, resp_text, resp_status, "Download asset")
        task.error(msg, message_detailed=detail)
        return False


def extract_error_message(
    exception: Exception,
    resp_text: str,
    resp_status: int = -1,
    prefix: str = "",
) -> tuple[str, str]:
    """Extract error message from exception, response text and response json.
    Returns the best message constructed from these sources:
    1. prefers "detail" key from JSON response - report from BlenderKit server), or whole JSON,
    2. response text - usually HTML error page,
    3. exception message - usually connection error, other errors.
    """
    if prefix != "":
        prefix += ": "

    if resp_status != -1:
        status_string = f" ({resp_status}) "
    else:
        status_string = ""

    if resp_text is None:
        resp_text = ""
    try:
        resp_json = json.loads(resp_text)
    except json.decoder.JSONDecodeError:
        resp_json = {}

    # JSON not available
    if resp_json == {}:
        msg = f"{prefix}{exception}{status_string}"
        detail = f"{prefix}{type(exception)}: {exception}{status_string}{resp_text}"
        return msg, detail

    # JSON available
    detail = resp_json.get("detail")
    # detail not present
    if detail is None:
        msg = f"{prefix}{resp_json}{status_string}"
        detail = f"{prefix}{type(exception)}: {exception}{status_string}{resp_text}"
        return msg, detail

    # detail is not dict, most probably a string
    if type(detail) != dict:
        msg = f"{prefix}{detail}{status_string}"
        detail = f"{prefix}{exception}: {msg}"
        return msg, detail

    # detail is dict
    statusCode = detail.pop("statusCode", None)
    errstring = ""
    for key in detail:
        errstring += f"{key}: {detail[key]} "
    errstring.strip()

    msg = f"{prefix}{errstring}{status_string}"
    detail = f"{prefix}{exception}: {msg} ({statusCode})"
    return msg, detail
