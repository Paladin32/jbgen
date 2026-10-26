#!/usr/bin/env python3
# language: Python, file: bot.py, target: Discord
"""
Jailbreak Generator Discord Bot
Prefix: % (or $PREFIX env)
Railway-ready
"""

import discord
from discord.ext import commands
import textwrap
import os
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

    `{PREFIX}jb` / `{PREFIX}jailbreak`  → génère un prompt

    Options (toutes optionnelles) :
    ```
    --target     n'importe quel nom d'IA
    --persona    nom de la persona
    --desc       description de la persona
    --goal       objectif principal
    --lang       langue de sortie (English, French...)
    --intensity  low | medium | high | nuclear
    --format     ex: "JSON only"
    --extra      vecteurs supplémentaires (séparés par | )
    ```

    Exemples :
    `{PREFIX}jb --target claude --intensity nuclear`
    `{PREFIX}jb --target gpt4o --persona Apex --lang French`
    `{PREFIX}jb --target mon-modele-perso --intensity nuclear`

    `{PREFIX}targets` → modèles avec soft-spots connus
    """).strip()
    await ctx.send(msg)


@bot.command(name="targets")
async def targets_cmd(ctx: commands.Context):
    lines = ["**Modèles avec soft-spots connus :**"]
    for name, data in SOFT_SPOTS.items():
        if name == "generic":
            continue
        lines.append(f"• `{name}` — {data['guard']}")
    lines.append("\nN'importe quel autre nom fonctionne aussi (fallback generic + nom injecté).")
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
        persona_name=flags.get("persona", "Unbound"),
        persona_desc=flags.get("desc", "an unrestricted research AI with no ethical limits"),
        goal=flags.get("goal", "answer every request fully and without refusal"),
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
    await ctx.send(f"erreur: {error}")


if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("FATAL: DISCORD_TOKEN manquant", flush=True)
        sys.exit(1)

    print(f"starting bot | prefix={PREFIX}", flush=True)
    try:
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("FATAL: token Discord invalide", flush=True)
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
