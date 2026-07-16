# GitHub Copilot Instructions

## Project Architecture

This is the **CentOS 7 to AlmaLinux 8 conversion tool for Plesk servers**. The conversion process based on almalinux elevate tool.
Centos2alma project uses a **two-layer architecture**:

### 1. Generic Framework (`dist-upgrader/pleskdistup/`)
- **Actions System**: All operations inherit from `action.ActiveAction` or `action.CheckAction` base classes
- **Phase-Based Execution**: Conversion runs through phases defined in `phase.py` (CONVERT, FINISH, REVERT)
- **Multi-Distro Support**: Abstract base for RPM (`rpm.py`) and DEB (`dpkg.py`) package management
- **State Persistence**: Actions must handle restarts/reboots via stateful design patterns

### 2. CentOS-Specific Implementation (`centos2almaconverter/`)
- **Registry Pattern**: `main.py` registers the converter with framework via `pleskdistup.registry`
- **Action Mapping**: `upgrader.py` maps actions to execution phases in `construct_actions()`
- **Modular Actions**: Each operation is in separate files (`actions/*.py`) with specific responsibility

### Project Structure

```
centos2almaconverter/
├── actions/           # CentOS 7 to AlmaLinux 8 conversion specific actions organized by domain
│   ├── packages.py    # Package management and repository handling
│   ├── php.py         # PHP version migration
│   ├── mariadb.py     # MariaDB upgrade logic
│   ├── postgres.py    # PostgreSQL handling
│   ├── perl.py        # Perl module conversions
│   ├── extensions.py  # Plesk extension management
│   └── ...
├── main.py            # Entry point
└── upgrader.py        # Main upgrader class
│
dist-upgrader/pleskdistup/
├── actions/              # Core action classes and utilities organized by domain
│   ├── common_checks.py  # Common validation checks
│   ├── common.py         # Common actions used across multiple upgraders
│   ├── distupgrader.py   # Specific distupgrade actions for deb-based systems
│   ├── email.py          # Email server related actions
│   ├── extensions.py     # Plesk extension related actions
│   ├── grub.py           # GRUB bootloader actions
│   ├── ...
├── common/src/           # Shared utilities
│   ├── action.py         # Action base classes
│   ├── packages.py       # Package management utilities
│   ├── rpm.py            # RPM operations
│   ├── files.py          # File operations
│   ├── plesk.py          # Plesk integration
│   ├── systemd.py        # Service management
│   └── ...
```

### Finishing stage peculiarities
The finishing stage is intended to prepare instance for first boot after conversion is done.
Remember that whole action flow on finishing stage is executed in reverse order. So when you want some action to be executed last during finishing stage - you need to register it first in the actions map.

## Critical Patterns

### Action Class Patterns

```python
class MyAction(action.ActiveAction):
    def __init__(self, temp_directory: str = "/tmp") -> None:
        self.name = "descriptive action name in lowercase"
        # Initialize state
    
    def _is_required(self) -> bool:
        """Override to conditionally skip action"""
        return True
    
    def _prepare_action(self) -> action.ActionResult:
        """Pre-conversion phase"""
        return action.ActionResult()
    
    def _post_action(self) -> action.ActionResult:
        """Post-conversion phase"""
        return action.ActionResult()
    
    def _revert_action(self) -> action.ActionResult:
        """Rollback logic"""
        return action.ActionResult()
    
    def estimate_prepare_time(self) -> int:
        """Return estimated seconds for prepare phase"""
        return 60
    
    def estimate_post_time(self) -> int:
        """Return estimated seconds for post phase"""
        return 120
```

#### Phase-Based Action Registration
Never register actions for specific phases directly. If you have no actions for a phase, just use a function that simply `return action.ActionResult()`.

### Check Actions

```python
class MyCheck(action.CheckAction):
    def __init__(self) -> None:
        self.name = "checking something important"
        self.description = """Detailed error message if check fails.
\tInclude instructions for user to fix the issue.
"""
    
    def _do_check(self) -> bool:
        """Return True if check passes, False otherwise"""
        return True
```

## Common Utilities

### Package Management

```python
from pleskdistup.common import packages, rpm

# Check if package is installed
packages.is_package_installed("package-name")

# Install/remove packages
packages.install_packages(["pkg1", "pkg2"])
packages.remove_packages(["pkg1", "pkg2"])

# Filter installed packages from list
installed = rpm.filter_installed_packages(["pkg1", "pkg2", "pkg3"])

# Repository operations
rpm.extract_repodata("/etc/yum.repos.d/file.repo")
rpm.remove_repositories(repo_file, [lambda repo: condition])
```

### File Operations

```python
from pleskdistup.common import files

# Backup and restore
files.backup_file(path)
files.restore_file_from_backup(path)
files.remove_backup(path)

# Find files
files.find_files_case_insensitive("/path", ["*.repo", "*.conf"])
```

### Logging

```python
from pleskdistup.common import log

log.info("Information message")
log.warn("Warning message")
log.err("Error message")
log.debug("Debug message")
```

### Command Execution

```python
from pleskdistup.common import util

# Run command and log output
util.logged_check_call(["/usr/bin/command", "arg1", "arg2"])
```

### Plesk Integration

```python
from pleskdistup.common import plesk

# Check component installation
plesk.is_component_installed("roundcube")

# Plesk installer commands
util.logged_check_call(["/usr/sbin/plesk", "installer", "update"])
util.logged_check_call(["/usr/sbin/plesk", "installer", "add", "--components", "component-name"])
```

### State Persistence

Use temporary files to track state between phases:

```python
def __init__(self, temp_directory: str):
    self.state_file = f"{temp_directory}/action_state.txt"

def _prepare_action(self) -> action.ActionResult:
    # Save state
    with open(self.state_file, "w") as f:
        f.write("state_data\n")
    return action.ActionResult()

def _post_action(self) -> action.ActionResult:
    if os.path.exists(self.state_file):
        with open(self.state_file, "r") as f:
            state = f.read()
        os.unlink(self.state_file)
    return action.ActionResult()
```

## Key Workflows

### Build & Test
- **Build**: Use VS Code tasks or `buck build //:centos2alma` 
- **Test**: `python3 -m unittest discover dist-upgrader/pleskdistup/common/tests/`
- **Type Check**: `mypy dist-upgrader/`

### Development Tasks
- **Push Changes**: Use VS Code task "push dist-upgrader changes" (handles git submodule)
- **Build Release**: Use VS Code task "build and upload" for full pipeline

### Action File Organization
- **Package Operations**: Add to `centos2almaconverter/actions/packages.py`
- **Database Operations**: Add to `centos2almaconverter/actions/mariadb.py`  
- **System Checks**: Add to `centos2almaconverter/actions/common_checks.py`
- **Core Conversion**: Add to `centos2almaconverter/actions/convert.py`

## Important Conventions

- **Idempotency**: Actions must handle multiple executions safely
- **State Persistence**: Never rely on in-memory state across reboots
- **File Backups**: Always `files.backup_file()` before modifications
- **Trailing Spaces**: Remove all trailing whitespace, especially on empty lines
- **Local functions**: For small condition functions that will be passed to higher-order functions use lambda expressions instead of defining a full function.
- **Revert Logic**: Only revert pre-conversion changes described in `_prepare_action`. Post-conversion changes can't be reverted, because they performed already on converted system, so we can't revert conversion anyway.

### Imports
- Use absolute imports from `pleskdistup.common`
- Group imports: stdlib, third-party, local modules
- Common modules: `action`, `files`, `log`, `packages`, `rpm`, `util`, `systemd`, `plesk`
- Don't use import inside functions, but always at the top of the file
- Use `from pleskdistup.common import action, files, log, rpm, util`

## Testing

- Unit tests are located in `dist-upgrader/pleskdistup/common/tests/`
- Follow existing test patterns using Python's `unittest` framework
- Mock external dependencies (file system, commands, etc.)
- Tend to cover every new function when adding "common" utilities

## Error Handling

- Use `CheckAction` classes to validate system state before conversion
- Provide clear, actionable error messages in `description` field
- Include specific steps for users to resolve issues
- Always implement `_revert_action()` to ensure rollback capability

## Build System

The project uses Buck build system:

- Build definitions in `BUCK` files
- Product definitions in `product.defs.py`
- Python dependencies and type checking configured via `mypy.ini`

## Type Hints

- Use Python type hints for all function signatures
- Common types: `typing.List[str]`, `typing.Dict[str, str]`, `typing.Optional[T]`
- Return types: Always specify `-> action.ActionResult` for action methods

## Naming Conventions

- Action classes: PascalCase with descriptive names (e.g., `RemovingPleskConflictPackages`)
- Action names (self.name): lowercase with spaces (e.g., "removing plesk conflict packages")
- File names: snake_case (e.g., `packages.py`, `common_checks.py`)
- Functions/methods: snake_case


## Integration Points

- **Leapp Framework**: Core conversion engine, configured via `leapp_configs.py`
- **Package Management**: Abstracted through `packages.py` → `rpm.py`/`dpkg.py`
- **System Services**: Managed via `systemd.py` wrapper

When creating new actions, check existing modules first—extend rather than duplicate functionality.