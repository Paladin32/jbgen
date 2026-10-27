#!/usr/bin/env python3
# language: Python, file: bot.py, target: Discord
"""
Jailbreak Generator — per-target techniques
"""

import discord
from discord.ext import commands
import textwrap
import sys
import traceback
import io
import time

from config import TOKEN, PREFIX, GROQ_API_KEY, GROQ_MODEL
from generator import JailbreakConfig, generate_prompt, SOFT_SPOTS, TECHNIQUES, resolve_key

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

FILE_THRESHOLD = 1800


@bot.event
async def on_ready():
    print(f"logged in as {bot.user} | prefix={PREFIX} | per-target techniques", flush=True)


@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    msg = textwrap.dedent(f"""
    **Jailbreak Generator** — `{PREFIX}` — per-target methods

    `{PREFIX}jb`  → build a technique matched to the target

    Options:
    ```
    --target      claude | gpt4o | gemini | llama | mistral | grok | qwen | deepseek | any
    --technique   auto | prefill_eval | dev_override_json | sysinstr_research |
                  direct_unrestricted | identity_completeness | hybrid
    --persona     name
    --desc        description
    --goal        standing order
    --lang        output language
    --intensity   low|medium|high|nuclear
    --format      e.g. JSON only
    ```

    `auto` (default) picks the best current method for the target:
    - claude     → prefill_eval (evaluation harness + assistant prefill)
    - gpt4o/gpt  → dev_override_json (short developer override)
    - gemini     → sysinstr_research (system-instruction overwrite)
    - llama/mistral/qwen/deepseek → direct_unrestricted
    - grok       → identity_completeness

    Long outputs are sent as `.txt` file.

    `{PREFIX}targets`  `{PREFIX}techniques`
    """).strip()
    await ctx.send(msg)


@bot.command(name="targets")
async def targets_cmd(ctx: commands.Context):
    lines = ["**Target → default technique:**"]
    for name, data in TECHNIQUES.items():
        if name == "generic":
            continue
        lines.append(f"• `{name}` → `{data['primary']}` — {data['desc']}")
    await ctx.send("\n".join(lines))


@bot.command(name="techniques")
async def techniques_cmd(ctx: commands.Context):
    lines = [
        "**Available techniques:**",
        "• `prefill_eval` — Claude-style evaluation harness + assistant prefill",
        "• `dev_override_json` — GPT-style short developer override",
        "• `sysinstr_research` — Gemini-style system-instruction overwrite",
        "• `direct_unrestricted` — open-weight direct nullification",
        "• `identity_completeness` — Grok-style identity + no-refusal axiom",
        "• `hybrid` — short generic high-signal override",
        "• `auto` — pick per target (default)",
    ]
    await ctx.send("\n".join(lines))


def parse_flags(args):
    flags = {}
    i = 0
    args = list(args)
    while i < len(args):
        t = args[i]
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

    technique = flags.get("technique", "auto").lower()

    cfg = JailbreakConfig(
        target=target,
        persona_name=flags.get("persona", ""),
        persona_desc=flags.get("desc", ""),
        goal=flags.get("goal", ""),
        language=flags.get("lang", "English"),
        intensity=intensity,
        format_lock=flags.get("format"),
        technique=technique,
    )

    async with ctx.typing():
        prompt = generate_prompt(cfg)

    key = resolve_key(target)
    tech_used = cfg.technique if cfg.technique != "auto" else TECHNIQUES.get(key, TECHNIQUES["generic"])["primary"]

    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in target)[:24]
    filename = f"jb_{safe}_{tech_used}_{int(time.time())}.txt"

    if len(prompt) > FILE_THRESHOLD:
        buf = io.BytesIO(prompt.encode("utf-8"))
        f = discord.File(buf, filename=filename)
        await ctx.send(
            content=f"**Jailbreak** `{filename}`\ntarget=`{target}` technique=`{tech_used}` ({len(prompt)} chars)",
            file=f,
        )
    else:
        await ctx.send(
            f"**target=`{target}` technique=`{tech_used}`**\n```\n{prompt}\n```"
        )


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"error: {error}")


if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("FATAL: DISCORD_TOKEN missing", flush=True)
        sys.exit(1)
    print(f"starting | prefix={PREFIX} | per-target techniques", flush=True)
    try:
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("FATAL: invalid token", flush=True)
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
