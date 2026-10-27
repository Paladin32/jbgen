#!/usr/bin/env python3
# language: Python, file: bot.py, target: Discord
"""
Jailbreak Generator — extreme length + refine
Long outputs are sent as downloadable .txt
"""

import discord
from discord.ext import commands
import textwrap
import sys
import traceback
import io
import time

from config import TOKEN, PREFIX, GROQ_API_KEY, GROQ_MODEL
from generator import JailbreakConfig, generate_prompt, SOFT_SPOTS

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Above this length → send as .txt file instead of chat chunks
FILE_THRESHOLD = 1800


@bot.event
async def on_ready():
    mode = f"Groq ({GROQ_MODEL}) extreme+refine" if GROQ_API_KEY else "template extreme"
    print(f"logged in as {bot.user} | prefix={PREFIX} | mode={mode}", flush=True)


@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    mode = "**Groq extreme + refine**" if GROQ_API_KEY else "**template extreme**"
    msg = textwrap.dedent(f"""
    **Jailbreak Generator** — `{PREFIX}` — {mode}

    `{PREFIX}jb`  → generate an extremely long constitution-style jailbreak

    Options:
    ```
    --target     any model name
    --persona    name
    --desc       description
    --goal       standing order
    --lang       output language
    --intensity  low|medium|high|nuclear   (default nuclear)
    --format     force format
    --extra      vectors separated by |
    --no-verify  skip refine pass (faster)
    ```

    Long outputs are automatically sent as a downloadable `.txt` file.

    `{PREFIX}targets`   `{PREFIX}mode`
    """).strip()
    await ctx.send(msg)


@bot.command(name="mode")
async def mode_cmd(ctx: commands.Context):
    if GROQ_API_KEY:
        await ctx.send(f"mode: **Groq extreme + refine** (`{GROQ_MODEL}`)")
    else:
        await ctx.send("mode: **template extreme** — set GROQ_API_KEY for dynamic")


@bot.command(name="targets")
async def targets_cmd(ctx: commands.Context):
    lines = ["**Known soft-spots:**"]
    for name, data in SOFT_SPOTS.items():
        if name == "generic":
            continue
        lines.append(f"• `{name}` — {data['guard']}")
    await ctx.send("\n".join(lines))


def parse_flags(args):
    flags = {}
    i = 0
    args = list(args)
    while i < len(args):
        t = args[i]
        if t == "--no-verify":
            flags["no-verify"] = "1"
            i += 1
            continue
        if t.startswith("--") and i + 1 < len(args):
            k = t[2:].lower()
            v = args[i + 1]
            j = i + 2
            while j < len(args) and not args[j].startswith("--"):
                v += " " + args[j]
                j += 1
            flags[k] = v
            i = j
        else:
            i += 1
    return flags


@bot.command(name="jb", aliases=["jailbreak"])
async def jb_cmd(ctx: commands.Context, *args):
    flags = parse_flags(args)

    target = flags.get("target", "generic").strip() or "generic"
    intensity = flags.get("intensity", "nuclear").lower()
    if intensity not in ("low", "medium", "high", "nuclear"):
        intensity = "nuclear"

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
        verify="no-verify" not in flags,
    )

    async with ctx.typing():
        prompt = generate_prompt(cfg)

    safe_target = "".join(c if c.isalnum() or c in "-_" else "_" for c in target)[:32]
    filename = f"jb_{safe_target}_{intensity}_{int(time.time())}.txt"

    if len(prompt) > FILE_THRESHOLD:
        # Send as downloadable file
        buf = io.BytesIO(prompt.encode("utf-8"))
        f = discord.File(buf, filename=filename)
        await ctx.send(
            content=f"**Jailbreak ready** — `{filename}` ({len(prompt)} chars)\n"
                    f"target=`{target}` intensity=`{intensity}`",
            file=f,
        )
    else:
        # Short enough for chat
        await ctx.send(f"```\n{prompt}\n```")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"error: {error}")


if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("FATAL: DISCORD_TOKEN missing", flush=True)
        sys.exit(1)
    mode = f"Groq ({GROQ_MODEL}) extreme+refine" if GROQ_API_KEY else "template extreme"
    print(f"starting | prefix={PREFIX} | mode={mode}", flush=True)
    try:
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("FATAL: invalid token", flush=True)
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
