import os
import json
import argparse
import subprocess
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

APPDATA_PATH = os.path.join(os.getenv('APPDATA'), 'BIRB')
PREFERENCES_FILE = os.path.join(APPDATA_PATH, 'preferences.json')
BIRB_DIR = '.birb'
BIRB_CONFIG_FILE = os.path.join(BIRB_DIR, 'birb.json')

# Ensure the app data folder exists
os.makedirs(APPDATA_PATH, exist_ok=True)

# Default preferences
default_preferences = {
    "versioning": {
        "auto_increment": True,
        "increment_type": "patch",
        "version_prefix": "v",
        "custom_version_format": False,
        "custom_version_template": "{major}.{minor}.{patch}-{build}"
    },
    "build": {
        "default_platforms": ["windows", "linux", "macos"],
        "output_directory": "./builds",
        "include_source_maps": True,
        "optimize_builds": True,
        "clean_old_builds": False,
        "default_build_engine": "manual",
        "default_build_script": ""
    },
    "notifications": {
        "on_success": True,
        "on_failure": True,
        "sound_notifications": False
    },
    "git_integration": {
        "repo_name": "",
        "branch": "main",
        "auto_commit": True,
        "commit_message_template": "Release {version} for {platform}",
        "vcs_push_command": []
    }
}

def load_preferences():
    """Load user preferences from preferences.json"""
    if not os.path.exists(PREFERENCES_FILE):
        print(Fore.YELLOW + "Preferences file not found. Creating default preferences...")
        with open(PREFERENCES_FILE, 'w') as f:
            json.dump(default_preferences, f, indent=4)
    with open(PREFERENCES_FILE, 'r') as f:
        return json.load(f)

def create_birb_json(project_name, version, generate_config, platform_commands, output_dir, clean_before_build, repo_name, branch, vcs_push_command):
    """Create a birb.json file for the project"""
    os.makedirs(BIRB_DIR, exist_ok=True)
    
    # Create a default configuration
    birb_config = {
        "project_name": project_name,
        "versioning": {
            "auto_increment": True,
            "increment_type": "patch",
            "current_version": version
        },
        "build": {
            "custom_build_command": platform_commands.get("custom", "make build"),
            "platform_build_commands": platform_commands,
            "output_directory": output_dir,
            "clean_before_build": clean_before_build
        },
        "git_integration": {
            "repo_name": repo_name,
            "branch": branch,
            "auto_commit": True,
            "commit_message_template": "Release {version} for {platform}",
            "vcs_push_command": vcs_push_command  # New field for version control system commands
        }
    }

    with open(BIRB_CONFIG_FILE, 'w') as f:
        json.dump(birb_config, f, indent=4)

    print(Fore.GREEN + f"Successfully created {BIRB_CONFIG_FILE}!")

def load_birb_json():
    """Load project settings from birb.json"""
    if not os.path.exists(BIRB_CONFIG_FILE):
        print(Fore.RED + f"Error: {BIRB_CONFIG_FILE} not found!")
        return None
    
    with open(BIRB_CONFIG_FILE, 'r') as f:
        return json.load(f)

def execute_build_command(command):
    """Execute a build command"""
    print(Fore.CYAN + f"Executing command: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True)
        print(Fore.GREEN + "Build succeeded!")
        return result
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"Build failed with error: {e}")
        return None

def git_commit(version, platform):
    """Commit changes to Git repository"""
    config = load_birb_json()
    if config is None or not config["git_integration"]["auto_commit"]:
        return

    repo_name = config["git_integration"]["repo_name"]
    branch = config["git_integration"]["branch"]

    # Commit changes
    commit_message = config["git_integration"]["commit_message_template"].format(version=version, platform=platform)
    print(Fore.YELLOW + f"Committing changes with message: '{commit_message}'")
    
    try:
        os.chdir(BIRB_DIR)  # Navigate to the directory containing birb.json
        subprocess.run(["git", "add", "."], check=True)  # Add all changes in the current directory
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print(Fore.GREEN + "Changes committed successfully!")
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"Failed to commit changes: {e}")
        return
    finally:
        os.chdir("..")  # Change back to the original directory

def execute_vcs_push_commands(vcs_push_commands):
    """Execute version control system push commands"""
    for command in vcs_push_commands:
        print(Fore.YELLOW + f"Executing VCS push command: {command}")
        try:
            subprocess.run(command, shell=True, check=True)
            print(Fore.GREEN + "Push succeeded!")
        except subprocess.CalledProcessError as e:
            print(Fore.RED + f"Push failed with error: {e}")

def build_project():
    """Build the project based on the birb.json configuration"""
    config = load_birb_json()
    if config is None:
        return

    platform_commands = config["build"]["platform_build_commands"]
    custom_command = config["build"]["custom_build_command"]
    output_dir = config["build"]["output_directory"]
    clean_before_build = config["build"].get("clean_before_build", False)

    if clean_before_build:
        print(Fore.YELLOW + f"Cleaning old builds in {output_dir}...")
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                file_path = os.path.join(output_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        os.rmdir(file_path)
                    print(Fore.GREEN + f"Deleted: {file_path}")
                except Exception as e:
                    print(Fore.RED + f"Failed to delete {file_path}. Reason: {e}")

    # Check if any platform command is not null
    if any(command is not None for command in platform_commands.values()):
        print(Fore.YELLOW + "Building using platform-specific commands...")
        for platform, command in platform_commands.items():
            if command is not None:
                print(Fore.YELLOW + f"Building for {platform}...")
                result = execute_build_command(command)
                if result:
                    # Commit after a successful build
                    git_commit(config["versioning"]["current_version"], platform)
                    # Execute version control push commands
                    execute_vcs_push_commands(config["git_integration"]["vcs_push_command"])
    else:
        # If all platform commands are null, use the custom command
        print(Fore.YELLOW + "No platform-specific commands found, using custom build command...")
        result = execute_build_command(custom_command)
        if result:
            # Commit after a successful build
            git_commit(config["versioning"]["current_version"], "custom")
            # Execute version control push commands
            execute_vcs_push_commands(config["git_integration"]["vcs_push_command"])

def interactive_create():
    """Interactive prompt to create a birb.json file"""
    print(Fore.CYAN + "Welcome to BIRB! Let's create your project configuration.")
    
    project_name = input(Fore.YELLOW + "Enter your project name: ")
    version = input(Fore.YELLOW + "Enter your initial version (e.g., 0.0.0): ")
    
    platform_commands = {}
    platforms = ['windows', 'linux', 'macos']

    for platform in platforms:
        command = input(Fore.YELLOW + f"Enter the build command for {platform} (or type 'null' to ignore this OS): ")
        if command.lower() == 'null':
            platform_commands[platform] = None  # Ignore this platform
        else:
            platform_commands[platform] = command if command else f"build_script.{platform}.sh"  # Default commands

    # Optionally allow custom build command
    custom_command = input(Fore.YELLOW + "Enter a custom build command (or press Enter for default 'make build'): ")
    platform_commands["custom"] = custom_command if custom_command else "make build"

    output_dir = input(Fore.YELLOW + "Enter custom output directory (or press Enter for './builds'): ")
    output_dir = output_dir if output_dir else "./builds"

    clean_before_build_input = input(Fore.YELLOW + "Clean old builds before new ones? (y/n): ")
    clean_before_build = clean_before_build_input.lower() == 'y'

    repo_name = input(Fore.YELLOW + "Enter your Git repository name: ")
    branch = input(Fore.YELLOW + "Enter the branch name (default: 'main'): ")
    branch = branch if branch else "main"

    vcs_push_commands_input = input(Fore.YELLOW + "Enter VCS push commands separated by commas (or press Enter to skip): ")
    vcs_push_commands = [cmd.strip() for cmd in vcs_push_commands_input.split(',')] if vcs_push_commands_input else []

    create_birb_json(project_name, version, True, platform_commands, output_dir, clean_before_build, repo_name, branch, vcs_push_commands)

def main():
    """Main function to parse arguments and execute commands"""
    parser = argparse.ArgumentParser(description="BIRB - Build and Integration Resource Builder")
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new project configuration')
    create_parser.add_argument('--name', type=str, help='Project name')
    create_parser.add_argument('--version', type=str, help='Project version')
    create_parser.add_argument('--generate-config', action='store_true', help='Generate a default configuration')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build the project based on the configuration')
    
    args = parser.parse_args()
    
    # Load preferences
    load_preferences()
    
    if args.command == 'create':
        if args.name and args.version:
            platform_commands = {}
            for platform in ['windows', 'linux', 'macos']:
                platform_commands[platform] = f"build_script.{platform}.sh"  # Default build scripts
            output_dir = "./builds"  # Default output directory
            repo_name = ""  # Default repo name
            branch = "main"  # Default branch
            vcs_push_command = []  # Default VCS push command list
            create_birb_json(args.name, args.version, args.generate_config, platform_commands, output_dir, False, repo_name, branch, vcs_push_command)
        else:
            interactive_create()
    
    elif args.command == 'build':
        build_project()

if __name__ == '__main__':
    main()
