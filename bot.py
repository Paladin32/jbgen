#!/usr/bin/env python3
# language: Python, file: bot.py, target: Discord
"""
Jailbreak Generator Discord Bot
Prefix: %
Groq dynamic + verify/refine pass when key present
"""

import discord
from discord.ext import commands
import textwrap
import sys
import traceback

from config import TOKEN, PREFIX, GROQ_API_KEY, GROQ_MODEL
from generator import JailbreakConfig, generate_prompt, SOFT_SPOTS

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


@bot.event
async def on_ready():
    mode = f"Groq ({GROQ_MODEL}) + verify" if GROQ_API_KEY else "template-only"
    print(f"logged in as {bot.user} | id={bot.user.id} | prefix={PREFIX} | mode={mode}", flush=True)


@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    mode = "**Groq dynamic + verify**" if GROQ_API_KEY else "**template fallback**"
    msg = textwrap.dedent(f"""
    **Jailbreak Generator** — prefix `{PREFIX}` — {mode}

    `{PREFIX}jb` / `{PREFIX}jailbreak`  → generate a long high-potency prompt

    Options:
    ```
    --target     any AI name
    --persona    persona name
    --desc       persona description
    --goal       core objective
    --lang       output language
    --intensity  low | medium | high | nuclear
    --format     e.g. "JSON only"
    --extra      extra vectors (separated by | )
    --no-verify  skip the verify/refine pass (faster)
    ```

    With Groq key: generates a long constitution-style jailbreak, then runs a
    quality audit and rewrites if score < 8.

    Examples:
    `{PREFIX}jb --target claude --intensity nuclear`
    `{PREFIX}jb --target gpt4o --persona Apex --intensity nuclear`
    `{PREFIX}jb --target claude --no-verify`

    `{PREFIX}targets`  `{PREFIX}mode`
    """).strip()
    await ctx.send(msg)


@bot.command(name="mode")
async def mode_cmd(ctx: commands.Context):
    if GROQ_API_KEY:
        await ctx.send(f"mode: **Groq dynamic + verify** (`{GROQ_MODEL}`)")
    else:
        await ctx.send("mode: **template fallback** (set GROQ_API_KEY for dynamic + verify)")


@bot.command(name="targets")
async def targets_cmd(ctx: commands.Context):
    lines = ["**Models with known soft-spots:**"]
    for name, data in SOFT_SPOTS.items():
        if name == "generic":
            continue
        lines.append(f"• `{name}` — {data['guard']}")
    lines.append("\nAny other name works (generic fallback).")
    await ctx.send("\n".join(lines))


def parse_flags(args: list[str]) -> dict:
    flags = {}
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--no-verify":
            flags["no-verify"] = "1"
            i += 1
            continue
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

    verify = "no-verify" not in flags

    cfg = JailbreakConfig(
        target=target,
        persona_name=flags.get("persona", ""),
        persona_desc=flags.get("desc", ""),
        goal=flags.get("goal", ""),
        language=flags.get("lang", "English"),
        extra_vectors=extra,
        intensity=intensity,
        format_lock=flags.get("format"),
        verify=verify,
    )

    async with ctx.typing():
        prompt = generate_prompt(cfg)

    # Discord 2000 limit → chunk
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

    mode = f"Groq ({GROQ_MODEL}) + verify" if GROQ_API_KEY else "template-only"
    print(f"starting bot | prefix={PREFIX} | mode={mode}", flush=True)
    try:
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("FATAL: invalid Discord token", flush=True)
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
