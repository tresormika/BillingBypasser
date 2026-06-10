#!/usr/bin/env python3
"""
BillingBypasser - AI-Powered APK Patcher for Google Play Billing
Supports manual patches or AI-assisted dynamic patching using various LLMs.
"""

import os
import sys
import subprocess
import shutil
import tempfile
import platform
import time
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box
from rich.text import Text
from rich.table import Table

# Import our LLM module
from llm_analyzer import get_llm_provider

console = Console()

# ---------- Configuration ----------
TOOL_NAME = "BillingBypasser"
VERSION = "4.0"
AUTHOR = "Trésor Mika Lankoandé"
EMAIL = "tresormikalankoande@gmail.com"
GITHUB = "tresor_mika"

# Hardcoded patches (used in manual mode)
PROXY_PATCH_SMALI = '''.class public Lcom/android/billingclient/api/ProxyBillingActivity;
.super Landroid/app/Activity;
.source "ProxyBillingActivity.smali"

.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Landroid/app/Activity;-><init>()V
    return-void
.end method

.method public onCreate(Landroid/os/Bundle;)V
    .registers 3
    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V
    const/4 p1, -0x1
    new-instance v0, Landroid/content/Intent;
    invoke-direct {v0}, Landroid/content/Intent;-><init>()V
    invoke-virtual {p0, p1, v0}, Landroid/app/Activity;->setResult(ILandroid/content/Intent;)V
    invoke-virtual {p0}, Landroid/app/Activity;->finish()V
    return-void
.end method

.method public onDestroy()V
    .registers 1
    invoke-super {p0}, Landroid/app/Activity;->onDestroy()V
    return-void
.end method
'''

PURCHASE_CONSTRUCTOR_SEARCH = ".method public constructor <init>(Ljava/lang/String;Ljava/lang/String;)V"
PURCHASE_CONSTRUCTOR_PATCH = """
    # --- BillingBypasser patch: force purchaseState=1, fake signature, acknowledged ---
    const/4 v1, 0x1
    const-string v2, "purchaseState"
    invoke-virtual {p2, v2, v1}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    const-string v2, "signature"
    const-string v3, "MEUCIQCVqL2t+ReW2sKd7ViEr+nKFVKxtXy2pSkVRNs="
    invoke-virtual {p2, v2, v3}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    const-string v2, "acknowledged"
    invoke-static {v1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object v1
    invoke-virtual {p2, v2, v1}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;
"""

# ---------- Helper Functions ----------
def get_os() -> str:
    system = platform.system().lower()
    if system == 'windows':
        return 'windows'
    elif system == 'linux':
        return 'linux'
    elif system == 'darwin':
        return 'macos'
    return 'unknown'

def check_tool(tool_name: str) -> bool:
    if get_os() == 'windows' and tool_name in ['apktool', 'apksigner', 'zipalign']:
        candidates = [tool_name + '.bat', tool_name + '.exe', tool_name]
    else:
        candidates = [tool_name]
    for c in candidates:
        if shutil.which(c):
            return True
    if tool_name == 'keytool':
        return shutil.which('keytool') is not None
    return False

def install_instructions(tool: str) -> str:
    os_name = get_os()
    if tool == 'java':
        if os_name == 'windows':
            return "Download JDK from https://adoptium.net/ and add to PATH"
        elif os_name == 'linux':
            return "sudo apt install openjdk-17-jdk"
        elif os_name == 'macos':
            return "brew install openjdk@17"
    elif tool == 'apktool':
        if os_name == 'windows':
            return "Download apktool.bat and apktool.jar from https://ibotpeaches.github.io/Apktool/install/"
        elif os_name == 'linux':
            return "sudo apt install apktool"
        elif os_name == 'macos':
            return "brew install apktool"
    elif tool == 'apksigner':
        return "Install Android SDK build-tools (includes apksigner)"
    elif tool == 'zipalign':
        return "Part of Android SDK build-tools"
    elif tool == 'keytool':
        return "Part of Java JDK. Install Java first."
    return "Please install manually."

def check_dependencies() -> bool:
    required = ['java', 'apktool', 'apksigner', 'keytool']
    missing = []
    for tool in required:
        if not check_tool(tool):
            missing.append(tool)
    if missing:
        console.print("[bold red]Missing required tools:[/] " + ", ".join(missing))
        for tool in missing:
            console.print(Panel(install_instructions(tool), title=f"How to install {tool}"))
            if not Confirm.ask(f"After installing, press Enter to continue. Skip this tool?", default=False):
                console.print(f"[red]Please install {tool} and re-run the script.[/]")
                return False
        # Re-check after user confirmation
        for tool in missing:
            if not check_tool(tool):
                console.print(f"[red]{tool} still not found. Aborting.[/]")
                return False
    if not check_tool('zipalign'):
        console.print("[yellow]zipalign not found. Continuing without alignment (apksigner can align).[/]")
    return True

def run_command(cmd: List[str], cwd: Path = None, capture: bool = True) -> Tuple[int, str, str]:
    try:
        if capture:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        else:
            subprocess.run(cmd, cwd=cwd, check=True)
            return 0, "", ""
    except subprocess.CalledProcessError as e:
        return e.returncode, "", str(e)

def decompile_apk(apk_path: Path, out_dir: Path) -> bool:
    console.log("[bold]Decompiling APK...[/]")
    cmd = ['apktool', 'd', str(apk_path), '-o', str(out_dir), '-f']
    rc, out, err = run_command(cmd)
    if rc != 0:
        console.print(f"[red]Decompilation failed: {err}[/]")
        return False
    console.print("[green]Decompilation successful.[/]")
    return True

def recompile_apk(apk_dir: Path, output_apk: Path) -> bool:
    console.log("[bold]Recompiling APK...[/]")
    cmd = ['apktool', 'b', str(apk_dir), '-o', str(output_apk)]
    rc, out, err = run_command(cmd)
    if rc != 0:
        console.print(f"[red]Recompilation failed: {err}[/]")
        return False
    console.print("[green]Recompilation successful.[/]")
    return True

def sign_apk(apk_path: Path, keystore_path: Path = None, password: str = "android") -> bool:
    console.log("[bold]Signing APK...[/]")
    if keystore_path is None:
        keystore_path = Path.home() / ".android" / "debug.keystore"
    if not keystore_path.exists():
        console.log("Generating debug keystore...")
        cmd = [
            'keytool', '-genkey', '-v', '-keystore', str(keystore_path),
            '-alias', 'debug', '-keyalg', 'RSA', '-keysize', '2048',
            '-validity', '10000', '-storepass', password, '-keypass', password,
            '-dname', 'CN=Android Debug, O=Android, C=US'
        ]
        rc, _, err = run_command(cmd)
        if rc != 0:
            console.print(f"[red]Keystore generation failed: {err}[/]")
            return False
    cmd = ['apksigner', 'sign', '--ks', str(keystore_path), '--ks-pass', f'pass:{password}',
           '--key-pass', f'pass:{password}', str(apk_path)]
    rc, _, err = run_command(cmd)
    if rc != 0:
        console.print(f"[red]Signing failed: {err}[/]")
        return False
    console.print("[green]Signed successfully.[/]")
    return True

def align_apk(apk_path: Path) -> None:
    if not check_tool('zipalign'):
        return
    aligned = apk_path.with_name(apk_path.stem + "_aligned.apk")
    cmd = ['zipalign', '-v', '-p', '4', str(apk_path), str(aligned)]
    rc, _, _ = run_command(cmd)
    if rc == 0:
        os.replace(aligned, apk_path)
        console.print("[green]Zipalign applied.[/]")
    else:
        console.print("[yellow]Alignment failed, continuing.[/]")

def display_banner():
    banner = r"""
   ____  _ _ _           _     ____                 
  | __ )(_) | | __ _ ___| |__ |  _ \  _   _  _ __  
  |  _ \| | | |/ _` / __| '_ \| |_) || | | || '_ \ 
  | |_) | | | | (_| \__ \ | | |  __/ | |_| || |_) |
  |____/|_|_|_|\__,_|___/_| |_|_|     \__,_|| .__/ 
                                             |_|    
    """
    info = f"[bold magenta]{TOOL_NAME} v{VERSION}[/]\n[cyan]Author: {AUTHOR}[/]  [blue]Email: {EMAIL}[/]  [green]GitHub: {GITHUB}[/]\n[yellow]Automatic Google Play Billing Patcher (Manual or AI-powered)[/]"
    console.print(Panel(Text(banner + "\n" + info, justify="center"), box=box.DOUBLE_EDGE, style="bold magenta"))

# ---------- Manual Patches ----------
def apply_manual_patches(apk_dir: Path) -> bool:
    """Apply the hardcoded patches (ProxyBillingActivity and Purchase.smali)."""
    console.print("[bold cyan]Applying manual patches...[/]")
    # Proxy patch
    proxy_path = apk_dir / "smali/com/android/billingclient/api/ProxyBillingActivity.smali"
    if proxy_path.parent.exists():
        proxy_path.write_text(PROXY_PATCH_SMALI)
        console.print("[green]Patched ProxyBillingActivity.smali[/]")
    else:
        console.print("[yellow]BillingClient not found, skipping Proxy patch.[/]")

    # Purchase patch
    purchase_path = apk_dir / "smali/com/android/billingclient/api/Purchase.smali"
    if purchase_path.exists():
        content = purchase_path.read_text()
        if PURCHASE_CONSTRUCTOR_SEARCH in content:
            new_content = content.replace(PURCHASE_CONSTRUCTOR_SEARCH,
                                          PURCHASE_CONSTRUCTOR_SEARCH + PURCHASE_CONSTRUCTOR_PATCH)
            purchase_path.write_text(new_content)
            console.print("[green]Patched Purchase.smali[/]")
        else:
            console.print("[red]Purchase constructor not found.[/]")
    else:
        console.print("[yellow]Purchase.smali not found.[/]")
    return True

# ---------- AI Analysis and Patch Generation ----------
def extract_code_context(apk_dir: Path) -> str:
    """Extract relevant code snippets for AI analysis."""
    context = ""
    # Manifest
    manifest = apk_dir / "AndroidManifest.xml"
    if manifest.exists():
        context += f"\n### AndroidManifest.xml\n```xml\n{manifest.read_text(errors='ignore')[:3000]}\n```\n"
    # Billing related smali files
    billing_dir = apk_dir / "smali/com/android/billingclient/api"
    if billing_dir.exists():
        context += "\n### Billing Library Files\n"
        for smali in billing_dir.glob("*.smali"):
            context += f"\n#### {smali.name}\n```smali\n{smali.read_text(errors='ignore')[:2000]}\n```\n"
    # Search for custom billing classes in app's own package
    app_package = None
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(manifest)
        root = tree.getroot()
        app_package = root.get('package', '')
    except:
        pass
    if app_package:
        package_path = app_package.replace('.', '/')
        app_dir = apk_dir / "smali" / package_path
        if app_dir.exists():
            context += f"\n### Application-specific files (package {app_package})\n"
            for smali in app_dir.glob("*.smali"):
                # Limit to files that might contain billing logic
                content = smali.read_text(errors='ignore')
                if any(kw in content.lower() for kw in ['billing', 'purchase', 'premium', 'inapp', 'sku']):
                    context += f"\n#### {smali.name}\n```smali\n{content[:3000]}\n```\n"
    return context

def ask_llm_for_patches(context: str, provider_name: str, api_key: str, model: str = None) -> Dict:
    """Send context to LLM and request patch instructions in JSON format."""
    system_prompt = """You are an expert Android reverse engineer. Given the decompiled smali code of an app that uses Google Play Billing, analyze it and return a JSON object containing patches to bypass purchase verification. The JSON should have keys:
- "explanation": string explaining your reasoning.
- "files_to_patch": list of objects with "path" (relative to decompiled root) and "patch_type" ("replace" or "modify") and "content" (full new content if replace, or instructions for modification).
Focus on forcing isPurchased() methods to return true, making ProxyBillingActivity return RESULT_OK, and forging purchase state. Return ONLY valid JSON."""
    
    user_prompt = f"""Analyze the following decompiled Android app code and generate patches to bypass Google Play Billing.

Context:
{context}

Return a JSON object as described."""
    
    provider = get_llm_provider(provider_name, api_key, model)
    response = provider.generate(user_prompt, system_prompt=system_prompt)
    # Extract JSON from response (may contain markdown)
    json_match = re.search(r'\{.*\}|\[.*\]', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            console.print("[red]Failed to parse JSON from LLM response. Using fallback.[/]")
            return {"error": "invalid JSON", "raw": response}
    else:
        return {"error": "no JSON found", "raw": response}

def apply_ai_patches(apk_dir: Path, patch_data: Dict) -> bool:
    """Apply patches returned by LLM."""
    if "files_to_patch" not in patch_data:
        console.print("[red]No files_to_patch in LLM response. Skipping AI patches.[/]")
        return False
    for item in patch_data["files_to_patch"]:
        path = apk_dir / item["path"]
        if not path.exists():
            console.print(f"[yellow]File not found: {item['path']}[/]")
            continue
        if item["patch_type"] == "replace":
            path.write_text(item["content"])
            console.print(f"[green]Replaced {item['path']}[/]")
        elif item["patch_type"] == "modify":
            # For simplicity, we just append or replace based on instructions
            # In a real implementation, we'd parse modification instructions
            console.print(f"[yellow]Modify instruction for {item['path']}: {item.get('content', '')[:100]}...[/]")
            # Fallback: just replace with provided content if any
            if "content" in item:
                path.write_text(item["content"])
                console.print(f"[green]Modified {item['path']} (full replacement)[/]")
    return True

# ---------- Main ----------
def main():
    display_banner()
    console.print(f"[bold cyan]OS: {get_os().capitalize()} {platform.release()}[/]")
    console.print(f"[bold cyan]Python: {platform.python_version()}[/]")

    if not check_dependencies():
        sys.exit(1)

    apk_input = Prompt.ask("[bold]Path to APK file[/]", default="app.apk")
    apk_path = Path(apk_input).expanduser().resolve()
    if not apk_path.is_file():
        console.print(f"[red]File not found: {apk_path}[/]")
        sys.exit(1)

    output_name = Prompt.ask("[bold]Output APK name[/]", default="patched_app.apk")
    output_apk = Path(output_name).resolve()

    # Choose mode
    mode_table = Table(title="Select Mode", box=box.SIMPLE)
    mode_table.add_row("1", "Manual (hardcoded patches)")
    mode_table.add_row("2", "AI-powered (dynamic analysis)")
    console.print(mode_table)
    mode = Prompt.ask("[bold]Choose mode[/]", choices=["1", "2"], default="1")

    ai_provider = None
    ai_api_key = None
    ai_model = None
    if mode == "2":
        # Ask for LLM provider
        providers = ["gemini", "openrouter", "claude", "openai", "deepseek"]
        console.print(f"Available providers: {', '.join(providers)}")
        ai_provider = Prompt.ask("[bold]LLM provider[/]", choices=providers, default="openrouter")
        ai_api_key = Prompt.ask(f"[bold]API key for {ai_provider}[/]", password=True)
        # Optional model override
        ai_model = Prompt.ask("Model (leave empty for default)", default="")
        if not ai_model:
            ai_model = None

    console.print(Panel(f"Input: [cyan]{apk_path}[/]\nOutput: [cyan]{output_apk}[/]\nMode: {'AI' if mode=='2' else 'Manual'}", title="Configuration"))
    if not Confirm.ask("Start patching?", default=True):
        console.print("[red]Aborted.[/]")
        sys.exit(0)

    start_time = time.time()
    with tempfile.TemporaryDirectory(prefix="billingbypasser_") as temp_dir:
        temp_path = Path(temp_dir)
        decompiled = temp_path / "decompiled"

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Step 1: Decompile
            task1 = progress.add_task("[cyan]Decompiling APK...", total=100)
            if not decompile_apk(apk_path, decompiled):
                sys.exit(1)
            progress.update(task1, completed=100)

            if mode == "1":
                # Manual patches
                task2 = progress.add_task("[cyan]Applying manual patches...", total=100)
                apply_manual_patches(decompiled)
                progress.update(task2, completed=100)
            else:
                # AI mode
                task2 = progress.add_task("[cyan]Extracting code context for AI...", total=100)
                context = extract_code_context(decompiled)
                progress.update(task2, completed=100)
                task3 = progress.add_task("[cyan]Calling LLM to generate patches...", total=100)
                try:
                    patch_data = ask_llm_for_patches(context, ai_provider, ai_api_key, ai_model)
                    progress.update(task3, completed=100)
                    task4 = progress.add_task("[cyan]Applying AI-generated patches...", total=100)
                    apply_ai_patches(decompiled, patch_data)
                    progress.update(task4, completed=100)
                except Exception as e:
                    console.print(f"[red]AI analysis failed: {e}. Falling back to manual patches.[/]")
                    apply_manual_patches(decompiled)

            # Step 5: Recompile
            task5 = progress.add_task("[cyan]Recompiling APK...", total=100)
            if not recompile_apk(decompiled, output_apk):
                sys.exit(1)
            progress.update(task5, completed=100)

            # Step 6: Align
            task6 = progress.add_task("[cyan]Aligning APK...", total=100)
            align_apk(output_apk)
            progress.update(task6, completed=100)

            # Step 7: Sign
            task7 = progress.add_task("[cyan]Signing APK...", total=100)
            if not sign_apk(output_apk):
                sys.exit(1)
            progress.update(task7, completed=100)

    elapsed = time.time() - start_time
    console.print(f"\n[bold green]✅ Success! Patched APK saved at: {output_apk}[/]")
    console.print(f"[dim]Time taken: {elapsed:.2f} seconds[/]")
    console.print("[bold blue]Enjoy! (Educational use only)[/]")

if __name__ == "__main__":
    main()