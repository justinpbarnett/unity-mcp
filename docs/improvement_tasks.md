# Unity MCP Improvement Tasks

## Low Priority Tasks

### Task: Configurable Server Installation Path
**Priority**: Low  
**Created**: July 2, 2025  
**Status**: Open  

**Description**: 
Currently, `ServerInstaller.cs` hardcodes the server installation location. This causes conflicts when users want to use custom repository locations instead of the default AppData path.

**Current Behavior**:
- Server automatically installs to `%USERPROFILE%\AppData\Local\Programs\UnityMCP\`
- No option to specify custom installation directory
- Creates conflicts with repository-based development setups

**Proposed Enhancement**:
Add configuration option to allow users to choose between:
1. **Default Location**: Current AppData behavior (good for end users)
2. **Custom Location**: User-specified path (good for developers)
3. **Repository Mode**: Detect and use existing repository installations

**Implementation Ideas**:
- Add Unity Editor preference setting for installation mode
- Modify `GetSaveLocation()` to check user preference first
- Add validation to ensure custom paths are valid
- Provide UI in MCP Editor window to configure installation path

**Benefits**:
- Eliminates double installation issues
- Better support for development workflows
- Maintains backward compatibility
- Reduces confusion about which installation is active

**Current Workaround**:
Modified `GetSaveLocation()` to check for repository path first, fallback to AppData.

**Files Involved**:
- `UnityMcpBridge/Editor/Helpers/ServerInstaller.cs`
- `UnityMcpBridge/Editor/Windows/UnityMcpEditorWindow.cs`

---

## Future Enhancement Ideas

### Task: Installation Path Validation
**Priority**: Medium  
**Status**: Idea  

Add validation to ensure installation paths are:
- Writable by current user
- Not in system directories
- Have sufficient disk space
- Compatible with Python virtual environments

### Task: Installation Progress Feedback
**Priority**: Low  
**Status**: Idea  

Provide better user feedback during server installation:
- Progress bars for git operations
- Clear error messages for common failures
- Retry mechanisms for network issues
