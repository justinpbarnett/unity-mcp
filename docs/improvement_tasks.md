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

## High Priority Tasks (From Original Roadmap Analysis)

### Task: Standalone Python Server Installation (CRITICAL)
**Priority**: High  
**Source**: justinpbarnett roadmap - Current Focus  
**Status**: Required for long-term compatibility  

**Description**: 
Original project is refactoring to decouple Python server from Unity package, installing as standalone application managed by `uv`.

**Benefits for AWMS**:
- Resolves installation/path conflicts permanently
- Simplifies setup and reduces configuration errors
- Aligns with original project direction for future compatibility
- Eliminates need for custom installation path workarounds

**Implementation Strategy**:
- Monitor original project progress (target was mid-April 2025, likely delayed)
- Implement similar architecture in our fork
- Ensure backward compatibility during transition
- Update installation documentation

**Priority Justification**: 
This addresses our core installation conflict issues systematically and ensures future compatibility.

### Task: Enhanced Error Handling and Connection Stability
**Priority**: High  
**Source**: justinpbarnett roadmap + AWMS requirements  
**Status**: Critical for AWMS reliability  

**Description**:
Original roadmap identifies connection issues like SocketExceptions after script compilation. AWMS specifically requires reliable error detection.

**AWMS-Specific Benefits**:
- Eliminates "silent failures" that break AWMS workflow detection
- Provides clear success/failure feedback to LLM
- Enables AWMS error prevention and self-reflection features
- Supports reliable session persistence

**Implementation Areas**:
- Improve timeout handling and retry mechanisms
- Add comprehensive error reporting to LLM
- Implement connection health monitoring
- Add fallback mechanisms for common failure scenarios

---

## Medium Priority Tasks (Strategic Fork Features)

### Task: Integration with IvanMurzak Custom Tool Framework
**Priority**: Medium  
**Source**: IvanMurzak/Unity-MCP fork analysis  
**Status**: Strategic enhancement opportunity  

**Description**:
IvanMurzak's fork provides extensible custom tool development framework using attributes like `[McpPluginToolType]` and `[McpPluginTool]`.

**AWMS Integration Benefits**:
- **Custom AWMS Tools**: Develop AWMS-specific tools (project state tracking, rule enforcement)
- **Extensible Architecture**: Add new AWMS features without modifying core Unity MCP
- **MainThread Handling**: Built-in Unity API thread management for AWMS operations
- **Dynamic Tool Loading**: Runtime tool discovery and registration

**Implementation Strategy**:
- Study IvanMurzak's attribute-based tool system
- Adapt for compatibility with justinbarnett's architecture
- Implement AWMS-specific tool categories (error detection, context management)
- Maintain compatibility with existing tool structure

**Potential AWMS Tools**:
- `[AwmsProjectStateMonitor]` - Track project state changes
- `[AwmsRuleValidator]` - Validate operations against AWMS rules
- `[AwmsContextManager]` - Manage session context and knowledge
- `[AwmsErrorDetector]` - Detect and prevent common LLM errors

### Task: Protocol Modernization (nurture-tech approach)
**Priority**: Medium  
**Source**: nurture-tech/unity-mcp-server analysis  
**Status**: Future-proofing opportunity  

**Description**:
nurture-tech fork uses latest MCP protocol version (2025-06-18) and Official MCP C# SDK.

**Benefits**:
- **Protocol Compliance**: Up-to-date with latest MCP standards
- **Professional Architecture**: Enterprise-grade implementation patterns
- **Long-term Viability**: Better maintained and supported
- **NPM Distribution**: Simplified installation and updates

**Implementation Considerations**:
- Evaluate migration effort vs benefits
- Assess compatibility with AWMS requirements
- Consider hybrid approach (adopt architecture patterns, maintain compatibility)
- Timeline coordination with AWMS development phases

### Task: WebSocket Architecture Evaluation (CoderGamester approach)
**Priority**: Medium  
**Source**: CoderGamester/mcp-unity analysis  
**Status**: Alternative architecture consideration  

**Description**:
CoderGamester fork uses WebSocket server inside Unity with Node.js server, includes Play Mode domain reload handling.

**Potential AWMS Benefits**:
- **Domain Reload Handling**: Maintains connection during Play Mode (critical for AWMS)
- **Real-time Communication**: Better suited for AWMS real-time monitoring
- **Modern Protocol**: WebSocket may be more reliable than TCP for some scenarios

**Evaluation Criteria**:
- Connection stability during Unity domain reloads
- Performance comparison with TCP approach
- Compatibility with Claude Desktop and other MCP clients
- Implementation complexity vs benefits

---

## Original Roadmap Integration Opportunities

### Short-Term Alignments (Post-Installation)

#### Azure OpenAI Integration
**Priority**: Low  
**AWMS Relevance**: Medium  
**Description**: Add UI/mechanism to configure Azure OpenAI connection.
**AWMS Benefit**: Supports enterprise AWMS deployments with Azure infrastructure.

#### Performance Optimization
**Priority**: High  
**AWMS Relevance**: High  
**Description**: Address performance bottlenecks in large scenes.
**AWMS Benefit**: Critical for AWMS operation in complex Unity projects.

#### Assembly Definition Files
**Priority**: Medium  
**AWMS Relevance**: High  
**Description**: Add `UnityMCP.Editor.asmdef` for better project structure.
**AWMS Benefit**: Improves compile times and project organization for AWMS.

### Mid-Term Strategic Features

#### Runtime MCP Operation
**Priority**: High  
**AWMS Relevance**: High  
**Description**: Explore Unity runtime (not just editor) MCP operations.
**AWMS Benefit**: Enables AWMS to work with built applications, not just editor.

#### Context Reduction
**Priority**: High  
**AWMS Relevance**: Critical  
**Description**: Reduce context sent to LLM to improve performance.
**AWMS Benefit**: Directly addresses AWMS context management and session optimization.

#### Code Revision Function
**Priority**: Medium  
**AWMS Relevance**: High  
**Description**: Implement function to revise existing code.
**AWMS Benefit**: Essential for AWMS refactoring and code improvement workflows.

#### Auto-approve Tool Calls
**Priority**: Low  
**AWMS Relevance**: Medium  
**Description**: Option to auto-approve tool calls.
**AWMS Benefit**: Reduces interruption in AWMS automated workflows.

### Long-Term Vision Alignment

#### Comprehensive Testing Suite
**Priority**: High  
**AWMS Relevance**: Critical  
**Description**: Automated testing for all Unity MCP functionality.
**AWMS Benefit**: Essential for AWMS reliability validation and regression prevention.

#### Sophisticated Scene Analysis
**Priority**: Medium  
**AWMS Relevance**: High  
**Description**: Advanced scene analysis and manipulation tools.
**AWMS Benefit**: Supports AWMS project understanding and big-picture maintenance.

---

## Fork-Specific Strategic Decisions

### Recommended Integration Priority

1. **Immediate (Phase 1)**: 
   - Enhanced error handling from roadmap
   - Performance optimizations for large projects
   - Assembly definition files

2. **Short-term (Phase 2)**:
   - Custom tool framework from IvanMurzak (for AWMS tools)
   - Context reduction capabilities
   - Runtime operation exploration

3. **Medium-term (Phase 3)**:
   - Protocol modernization evaluation
   - Standalone server installation architecture
   - WebSocket architecture assessment

4. **Long-term (Phase 4)**:
   - Comprehensive testing integration
   - Advanced scene analysis tools
   - Enterprise features (Azure integration)

### AWMS-Specific Customizations

#### Critical for AWMS Success:
- **Enhanced Error Reporting**: Silent failure elimination
- **Context Management**: LLM context optimization
- **Custom Tool Framework**: AWMS-specific operations
- **Runtime Operations**: Support for built applications
- **Domain Reload Handling**: Maintain connection during Unity state changes

#### Nice-to-Have for AWMS:
- **Protocol Modernization**: Future-proofing and compliance
- **Performance Optimizations**: Better handling of complex projects
- **Testing Infrastructure**: Validation and regression prevention

---

## Implementation Strategy

### Phase 1: Foundation (Current Testing Phase)
- Complete Unity MCP validation testing
- Implement enhanced error handling
- Add performance monitoring

### Phase 2: AWMS Integration (Next 2-3 months)
- Develop custom tool framework for AWMS operations
- Implement context reduction features
- Add domain reload handling

### Phase 3: Architecture Evolution (6 months)
- Evaluate protocol modernization
- Implement standalone server installation
- Add comprehensive testing

### Phase 4: Enterprise Features (12 months)
- Advanced scene analysis for AWMS
- Enterprise integration features
- Complete testing and validation infrastructure

**Strategic Focus**: Prioritize features that directly support AWMS reliability and functionality over general Unity MCP improvements, while maintaining compatibility with the broader Unity MCP ecosystem.
