"""Terminal interaction only; no research state or execution."""

import re
from pathlib import Path

import questionary
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.markdown import Markdown

from .locale import tr


def clean(text):
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", str(text))


class Terminal:
    def __init__(self):
        self.console = Console()

    def show(self, text="", markdown=False):
        text = clean(text)
        self.console.print(Markdown(text) if markdown else text, markup=False)

    def page(self, text):
        with self.console.pager(styles=False):
            self.show(text, markdown=True)

    async def ask(self, question):
        bindings = question.application.key_bindings
        if isinstance(bindings, KeyBindings):

            @bindings.add("escape")
            def back(event):
                event.app.exit(result=None)

        return await question.ask_async()

    async def choose(self, title, choices, back="返回"):
        items = [
            questionary.Choice(clean(label), value=value) for value, label in choices
        ]
        back_value = object()
        items.append(questionary.Choice(tr(back), value=back_value))
        answer = await self.ask(
            questionary.select(
                title,
                choices=items,
                instruction=tr("↑↓ 选择 · Enter 确认 · Esc 返回"),
                erase_when_done=True,
            )
        )
        return None if answer is back_value else answer

    async def text(self, title, default="", secret=False):
        factory = questionary.password if secret else questionary.text
        answer = await self.ask(factory(title, default=default, erase_when_done=True))
        return answer.strip() if answer is not None else None

    async def confirm(self, title):
        return (
            await self.choose(title, [(False, tr("暂不继续")), (True, tr("确认"))])
            is True
        )

    async def path(self, directory=False, save=False):
        mode = await self.choose(
            tr("选择位置"),
            [("native", tr("打开系统选择窗口")), ("text", tr("输入或粘贴路径"))],
        )
        if mode is None:
            return None
        if mode == "native":
            try:
                return native_path(directory, save)
            except (ImportError, RuntimeError, OSError):
                self.show(tr("系统选择窗口不可用，请输入路径。"))
        value = await self.ask(
            questionary.path(tr("路径（可粘贴，Tab 补全）"), only_directories=directory)
        )
        return Path(value.strip().strip('"')).expanduser().resolve() if value else None


def native_path(directory=False, save=False):
    import tkinter
    from tkinter import filedialog

    root = None
    try:
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if directory:
            value = filedialog.askdirectory(
                parent=root, title=tr("选择授权资料文件夹"), mustexist=True
            )
        elif save:
            value = filedialog.asksaveasfilename(parent=root, title=tr("保存成果"))
        else:
            value = filedialog.askopenfilename(parent=root, title=tr("选择资料文件"))
        return Path(value).resolve() if value else None
    except tkinter.TclError as exc:
        raise RuntimeError("file dialog unavailable") from exc
    finally:
        if root is not None:
            root.destroy()
