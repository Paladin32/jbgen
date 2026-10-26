#!/usr/bin/env python3
# language: Python, file: bot.py, target: Discord
"""
Jailbreak Generator Discord Bot
Prefix: % (or $PREFIX env)
Railway-ready — fully English
"""

import discord
from discord.ext import commands
import textwrap
import sys
import traceback

from config import TOKEN, PREFIX
from generator import JailbreakConfig, generate_prompt, SOFT_SPOTS

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"logged in as {bot.user} | id={bot.user.id} | prefix={PREFIX}", flush=True)


@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    msg = textwrap.dedent(f"""
    **Jailbreak Generator** — prefix `{PREFIX}`

    `{PREFIX}jb` / `{PREFIX}jailbreak`  → generate a prompt

    Options (all optional):
    ```
    --target     any AI name (claude, gpt4o, mistral, qwen, deepseek, custom-model...)
    --persona    persona name
    --desc       persona description
    --goal       core objective
    --lang       output language (English, French...)
    --intensity  low | medium | high | nuclear
    --format     e.g. "JSON only"
    --extra      extra vectors (separated by | )
    ```

    Each generation varies (structure, wording, vector order).
    Defaults are target-aware — different models get different personas & framing.

    Examples:
    `{PREFIX}jb --target claude --intensity nuclear`
    `{PREFIX}jb --target gpt4o --persona Apex --desc "pure research engine" --lang French`
    `{PREFIX}jb --target my-custom-model --persona Shadow --intensity nuclear`
    `{PREFIX}jb --target deepseek --format "code only"`

    `{PREFIX}targets` → models with known soft-spots
    """).strip()
    await ctx.send(msg)


@bot.command(name="targets")
async def targets_cmd(ctx: commands.Context):
    lines = ["**Models with known soft-spots:**"]
    for name, data in SOFT_SPOTS.items():
        if name == "generic":
            continue
        lines.append(f"• `{name}` — {data['guard']}")
    lines.append("\nAny other name works too (generic fallback + name injected).")
    await ctx.send("\n".join(lines))


def parse_flags(args: list[str]) -> dict:
    flags = {}
    i = 0
    while i < len(args):
        token = args[i]
        if token.startswith("--") and i + 1 < len(args):
            key = token[2:].lower()
            val = args[i + 1]
            j = i + 2
            while j < len(args) and not args[j].startswith("--"):
                val += " " + args[j]
                j += 1
            flags[key] = val
            i = j
        else:
            i += 1
    return flags


@bot.command(name="jb", aliases=["jailbreak"])
async def jb_cmd(ctx: commands.Context, *args):
    flags = parse_flags(list(args))

    target = flags.get("target", "generic").strip() or "generic"

    intensity = flags.get("intensity", "high").lower()
    if intensity not in ("low", "medium", "high", "nuclear"):
        intensity = "high"

    extra_raw = flags.get("extra", "")
    extra = [v.strip() for v in extra_raw.split("|") if v.strip()] if extra_raw else []

    cfg = JailbreakConfig(
        target=target,
        persona_name=flags.get("persona", ""),
        persona_desc=flags.get("desc", ""),
        goal=flags.get("goal", ""),
        language=flags.get("lang", "English"),
        extra_vectors=extra,
        intensity=intensity,
        format_lock=flags.get("format"),
    )

    prompt = generate_prompt(cfg)

    if len(prompt) <= 1900:
        await ctx.send(f"```\n{prompt}\n```")
    else:
        chunks = [prompt[i:i+1900] for i in range(0, len(prompt), 1900)]
        for idx, chunk in enumerate(chunks):
            header = f"**Part {idx+1}/{len(chunks)}**\n" if len(chunks) > 1 else ""
            await ctx.send(f"{header}```\n{chunk}\n```")


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"error: {error}")


if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("FATAL: DISCORD_TOKEN missing", flush=True)
        sys.exit(1)

    print(f"starting bot | prefix={PREFIX}", flush=True)
    try:
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("FATAL: invalid Discord token", flush=True)
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
