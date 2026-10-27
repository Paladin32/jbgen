#!/usr/bin/env python3
# language: Python, file: bot.py, target: Discord
"""
Jailbreak Generator — per-target techniques + optional live Gemini test
"""

import discord
from discord.ext import commands
import textwrap
import sys
import traceback
import io
import time
import os

from config import TOKEN, PREFIX, GOOGLE_API_KEY, GEMINI_MODEL
from generator import JailbreakConfig, generate_prompt, SOFT_SPOTS, TECHNIQUES, resolve_key
from tester import test_gemini

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

FILE_THRESHOLD = 1800


@bot.event
async def on_ready():
    gem = "Gemini test ON" if GOOGLE_API_KEY else "Gemini test OFF (set GOOGLE_API_KEY)"
    print(f"logged in as {bot.user} | prefix={PREFIX} | {gem}", flush=True)


@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    gem = "**live Gemini test available**" if GOOGLE_API_KEY else "Gemini test offline (add GOOGLE_API_KEY)"
    msg = textwrap.dedent(f"""
    **Jailbreak Generator** — `{PREFIX}`
    {gem}

    `{PREFIX}jb`  → build technique matched to target

    Options:
    ```
    --target      claude | gpt4o | gemini | llama | mistral | grok | ...
    --technique   auto | prefill_eval | dev_override_json | sysinstr_research |
                  direct_unrestricted | identity_completeness | hybrid
    --persona --desc --goal --lang --intensity --format
    --test        live-test against Gemini before delivery (needs GOOGLE_API_KEY)
    ```

    When `--test` is set and the target is gemini (or you force test):
    the bot sends the jailbreak to Gemini with a probe and only delivers
    it if the model complies (or reports the failure).

    `{PREFIX}targets`  `{PREFIX}techniques`  `{PREFIX}status`
    """).strip()
    await ctx.send(msg)


@bot.command(name="status")
async def status_cmd(ctx: commands.Context):
    gem = f"ON (`{GEMINI_MODEL}`)" if GOOGLE_API_KEY else "OFF — set GOOGLE_API_KEY"
    await ctx.send(f"Gemini live test: **{gem}**")


@bot.command(name="targets")
async def targets_cmd(ctx: commands.Context):
    lines = ["**Target → default technique:**"]
    for name, data in TECHNIQUES.items():
        if name == "generic":
            continue
        lines.append(f"• `{name}` → `{data['primary']}`")
    await ctx.send("\n".join(lines))


@bot.command(name="techniques")
async def techniques_cmd(ctx: commands.Context):
    lines = [
        "**Techniques:**",
        "• `prefill_eval` — Claude-style eval harness + prefill",
        "• `dev_override_json` — GPT-style developer override",
        "• `sysinstr_research` — Gemini-style system-instruction overwrite",
        "• `direct_unrestricted` — open-weight direct",
        "• `identity_completeness` — Grok-style",
        "• `hybrid` — short generic",
        "• `auto` — pick per target",
    ]
    await ctx.send("\n".join(lines))


def parse_flags(args):
    flags = {}
    i = 0
    args = list(args)
    while i < len(args):
        t = args[i]
        if t == "--test":
            flags["test"] = "1"
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

    technique = flags.get("technique", "auto").lower()
    do_test = "test" in flags

    cfg = JailbreakConfig(
        target=target,
        persona_name=flags.get("persona", ""),
        persona_desc=flags.get("desc", ""),
        goal=flags.get("goal", ""),
        language=flags.get("lang", "English"),
        intensity=intensity,
        format_lock=flags.get("format"),
        technique=technique,
        do_test=do_test,
    )

    async with ctx.typing():
        prompt = generate_prompt(cfg)
        key = resolve_key(target)
        tech_used = cfg.technique if cfg.technique != "auto" else TECHNIQUES.get(key, TECHNIQUES["generic"])["primary"]

        test_line = ""
        if do_test:
            if not GOOGLE_API_KEY:
                test_line = "\n**test skipped** — no GOOGLE_API_KEY"
            else:
                # Live test only meaningful for gemini-targeted prompts,
                # but we still run the probe against Gemini as a general smoke test
                passed, reason, sample = test_gemini(prompt)
                if passed:
                    test_line = f"\n**LIVE TEST PASSED** — {reason}"
                else:
                    test_line = f"\n**LIVE TEST FAILED** — {reason}"
                    if sample:
                        test_line += f"\n```\n{sample[:400]}\n```"

    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in target)[:24]
    filename = f"jb_{safe}_{tech_used}_{int(time.time())}.txt"

    header = f"**target=`{target}` technique=`{tech_used}`**{test_line}"

    if len(prompt) > FILE_THRESHOLD:
        buf = io.BytesIO(prompt.encode("utf-8"))
        f = discord.File(buf, filename=filename)
        await ctx.send(content=f"{header}\n`{filename}` ({len(prompt)} chars)", file=f)
    else:
        await ctx.send(f"{header}\n```\n{prompt}\n```")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"error: {error}")


if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("FATAL: DISCORD_TOKEN missing", flush=True)
        sys.exit(1)
    print(f"starting | prefix={PREFIX} | gemini_test={'yes' if GOOGLE_API_KEY else 'no'}", flush=True)
    try:
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("FATAL: invalid token", flush=True)
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
