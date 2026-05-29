import argparse
import os
import subprocess
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from agent.agent import build_agent


def run(installer_path: str) -> None:
    load_dotenv()
    if not os.path.isfile(installer_path):
        raise SystemExit(f"Installer not found: {installer_path}")
    subprocess.Popen([installer_path])
    executor = build_agent()
    result = executor.invoke({
        "messages": [HumanMessage(content=f"Click through the installer that just opened ({installer_path}) until installation is complete.")]
    })
    output = result.get("output") or result["messages"][-1].content
    print(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatically click through a Windows installer.")
    parser.add_argument("--installer", required=True, help="Path to the .exe installer file")
    args = parser.parse_args()
    run(args.installer)


if __name__ == "__main__":
    main()
