# BillingBypasser 

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/tresormika/BillingBypasser)
[![GitHub last commit](https://img.shields.io/github/last-commit/tresormika/BillingBypasser)](https://github.com/tresormika/BillingBypasser/commits)
[![GitHub issues](https://img.shields.io/github/issues/tresormika/BillingBypasser)](https://github.com/tresormika/BillingBypasser/issues)
[![GitHub stars](https://img.shields.io/github/stars/tresormika/BillingBypasser?style=social)](https://github.com/tresormika/BillingBypasser/stargazers)

**BillingBypasser** is an advanced, AI-powered tool to analyze and patch Android APKs, specifically targeting the removal of Google Play Billing checks. It can operate in **manual mode** using proven static patches, or in **AI mode** to dynamically analyze the decompiled code and generate custom patches on the fly, supporting various Large Language Models (LLMs).

##  Overview

The tool automates the entire workflow of APK modification:

1.  **Decompiles** your APK using `apktool`.
2.  **Analyzes** the code structure to locate billing-related components (`com.android.billingclient.api`).
3.  **Patches** the billing logic using either:
    *   **Manual Mode:** Applies a set of pre-defined, effective smali patches.
    *   **AI Mode:** Sends code context to an LLM (like Gemini, Claude, or GPT-4o) which then creates custom patching instructions.
4.  **Recompiles** the modified code back into a new APK.
5.  **Aligns & Signs** the final APK with a debug keystore, making it ready for installation.

## Features

*   **Cross-Platform:** Works on **Windows, Linux, and macOS**.
*   **Dual-Mode Patching:**
    *   **Manual Mode:** Quick, reliable, and doesn't require an internet connection or API keys.
    *   **AI-Powered Mode:** Adapts to different app implementations for higher success rates.
*   **Multi-LLM Support:** Integrates with Gemini, OpenRouter, Anthropic Claude, OpenAI GPT-4o, and DeepSeek.
*   **Rich Terminal UI:** A beautiful and informative interface built with the `rich` library, featuring progress bars, color-coded panels, and clear logging.
*   **Automated Environment Check:** Verifies that all necessary tools (`apktool`, `apksigner`, `java`, `keytool`) are installed. If any are missing, it provides clear instructions on how to obtain them.
*   **Network Security Analysis:** Scans the decompiled code for SSL pinning or other network-based verification methods.

## 📋Prerequisites

Before running BillingBypasser, ensure the following are installed and accessible from your command line:

1.  **Java Runtime Environment (JRE) or Java Development Kit (JDK)**: Version 8 or later is required. This includes `keytool`.
    *   **Windows/Linux/macOS:** You can download the JDK from [Adoptium](https://adoptium.net/).
2.  **Apktool**: The core tool for APK decompilation and recompilation.
    *   **Linux (Debian/Ubuntu):** `sudo apt install apktool`
    *   **macOS:** `brew install apktool`
    *   **Windows:** Download the wrapper script and `.jar` file from the [official website](https://ibotpeaches.github.io/Apktool/install/).
3.  **Apksigner**: A tool from the Android SDK Build Tools used for signing APKs. It is automatically included with Android Studio. Alternatively, you can install it via your package manager or download it as part of the Android SDK command-line tools.
    *   **Linux:** `sudo apt install apksigner`
    *   **macOS:** `brew install apksigner`

>  **Tip:** The script performs a startup check and will warn you about any missing tools.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/tresormika/BillingBypasser.git
    cd BillingBypasser
    ```

2.  **Install the required Python packages:**
    ```bash
    pip install rich requests
    ```

##  Usage

Run the script from your terminal:
```bash
python billing_bypasser.py
```

You will be guided through an interactive setup:

1. Select the target APK file.
2. Choose the output name for the patched APK.
3. Select the patching mode:
   · 1 (Manual): Uses hardcoded patches. Recommended for a quick test.
   · 2 (AI-powered): Allows you to choose an LLM provider and enter your API key. The script will then send the decompiled code for analysis.

 AI Mode Configuration

When using AI mode, you can choose from multiple providers:

Provider Key Environment Variable Notes
gemini GEMINI_API_KEY Google Gemini 2.0 Flash model.
openrouter OPENROUTER_API_KEY Provides access to many models (GPT-4o, Claude, Llama, etc.).
claude ANTHROPIC_API_KEY Anthropic's Claude 3.5 Sonnet model.
openai OPENAI_API_KEY OpenAI GPT-4o model.
deepseek DEEPSEEK_API_KEY DeepSeek Chat model.

The script will prompt you to enter the API key if it is not found in your system's environment variables. Keys are handled securely and are not stored permanently by the script.

 Legal and Ethical Considerations

This tool is intended for educational and research purposes only. Its sole purpose is to help developers test the resilience of their own applications against client-side patching attacks.

· You must have explicit permission to modify any APK that you do not own.
· Circumventing payment systems may violate the terms of service of the application and the Google Play Store.
· The author and contributors are not responsible for any misuse of this tool.

Always respect software licenses and the intellectual property of others.

 How It Works

Here is a technical overview of the patching process:

1. Decompilation: The APK is unpacked and converted into smali code (an assembly-like language for Android) and resources.
2. Manual Patches (ProxyBillingActivity.smali, Purchase.smali):
   · The tool replaces the ProxyBillingActivity code to always return a successful result (RESULT_OK), effectively skipping the Google Play payment prompt.
   · It modifies the Purchase.smali constructor to force the purchaseState to 1 (purchased) and injects a fake signature.
3. AI-Powered Analysis:
   · The script extracts the AndroidManifest.xml and relevant .smali files.
   · This data is sent to the selected LLM with a specific prompt to generate patching instructions in a structured JSON format.
   · The script then parses this response and applies the suggested modifications.
4. Recompilation & Signing: The patched smali code is rebuilt into a new APK, which is then signed with a debug certificate to make it installable on a device.

📁 Repository Structure

```
BillingBypasser/
├── billing_bypasser.py     # Main script with UI, core logic, and manual patches
├── llm_analyzer.py         # Module for interacting with various LLM APIs
├── README.md               # This file
└── LICENSE                 # MIT License file
```

 Dependencies

· Rich - For beautiful terminal formatting.
· Requests - For HTTP requests to LLM APIs.
· Apktool - For APK decompilation and recompilation.
· Apksigner - For APK signing.
· Java - Runtime environment for Apktool and Apksigner.

👤 Author

Trésor Mika Lankoandé

· Email: tresormikalankoande@gmail.com
· GitHub: tresor_mika

 License

This project is licensed under the MIT License. See the LICENSE file for full details.

---

BillingBypasser is provided "as is", without warranty of any kind. By using this tool, you agree that you are solely responsible for your actions.



