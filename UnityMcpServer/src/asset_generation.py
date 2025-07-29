"""
Enhanced asset generation system with improved server request handling and pipeline optimization.
Provides advanced asset creation, processing, and management capabilities.
"""

import os
import json
import time
import asyncio
import hashlib
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import concurrent.futures
from pathlib import Path

from enhanced_logging import enhanced_logger, LogContext
from exceptions import UnityOperationError, ResourceError, ValidationError
from advanced_logging import advanced_log_manager, LogLevel, LogCategory
from error_recovery import error_recovery_manager


class AssetType(Enum):
    """Supported asset types for generation."""
    TEXTURE = "texture"
    MATERIAL = "material"
    MESH = "mesh"
    PREFAB = "prefab"
    SCRIPT = "script"
    SHADER = "shader"
    AUDIO = "audio"
    ANIMATION = "animation"
    SCENE = "scene"


class GenerationMethod(Enum):
    """Asset generation methods."""
    PROCEDURAL = "procedural"
    TEMPLATE_BASED = "template_based"
    AI_ASSISTED = "ai_assisted"
    IMPORT_EXTERNAL = "import_external"
    DUPLICATE_EXISTING = "duplicate_existing"


class ProcessingStage(Enum):
    """Asset processing pipeline stages."""
    VALIDATION = "validation"
    GENERATION = "generation"
    OPTIMIZATION = "optimization"
    IMPORT = "import"
    POST_PROCESSING = "post_processing"
    FINALIZATION = "finalization"


@dataclass
class AssetGenerationRequest:
    """Request for asset generation."""
    asset_type: AssetType
    name: str
    generation_method: GenerationMethod
    parameters: Dict[str, Any] = field(default_factory=dict)
    output_path: str = "Assets/Generated"
    priority: int = 5  # 1-10, higher is more priority
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    request_id: str = None
    user_id: str = None
    session_id: str = None
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = self._generate_request_id()
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        timestamp = str(time.time())
        content = f"{self.asset_type.value}_{self.name}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class AssetGenerationResult:
    """Result of asset generation."""
    request_id: str
    success: bool
    asset_path: str = None
    asset_guid: str = None
    generation_time: float = 0
    file_size: int = 0
    processing_stages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AssetGenerationPipeline:
    """Enhanced asset generation pipeline with optimization and error handling."""
    
    def __init__(self, max_concurrent_jobs: int = 4):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_requests: Dict[str, AssetGenerationRequest] = {}
        self.completed_requests: Dict[str, AssetGenerationResult] = {}
        self.request_queue: List[AssetGenerationRequest] = []
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_jobs)
        
        # Pipeline statistics
        self.stats = {
            "total_requests": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "average_generation_time": 0,
            "total_assets_generated": 0
        }
        
        # Asset templates and configurations
        self.asset_templates = self._load_asset_templates()
        self.generation_configs = self._load_generation_configs()
    
    def _load_asset_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load asset templates for template-based generation."""
        
        templates = {
            AssetType.MATERIAL.value: {
                "standard": {
                    "shader": "Standard",
                    "properties": {
                        "_Color": [1, 1, 1, 1],
                        "_Metallic": 0,
                        "_Glossiness": 0.5
                    }
                },
                "unlit": {
                    "shader": "Unlit/Color",
                    "properties": {
                        "_Color": [1, 1, 1, 1]
                    }
                }
            },
            AssetType.TEXTURE.value: {
                "solid_color": {
                    "width": 256,
                    "height": 256,
                    "format": "RGBA32",
                    "color": [1, 1, 1, 1]
                },
                "noise": {
                    "width": 512,
                    "height": 512,
                    "format": "RGBA32",
                    "noise_type": "perlin",
                    "scale": 10.0
                }
            },
            AssetType.SCRIPT.value: {
                "monobehaviour": {
                    "template": "MonoBehaviour",
                    "namespace": "Generated",
                    "base_methods": ["Start", "Update"]
                },
                "scriptable_object": {
                    "template": "ScriptableObject",
                    "namespace": "Generated",
                    "create_asset_menu": True
                }
            }
        }
        
        return templates
    
    def _load_generation_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load generation configurations for different asset types."""
        
        configs = {
            AssetType.TEXTURE.value: {
                "max_size": 4096,
                "compression": "automatic",
                "mipmap": True,
                "filter_mode": "bilinear"
            },
            AssetType.MESH.value: {
                "max_vertices": 65000,
                "optimize_mesh": True,
                "generate_normals": True,
                "generate_tangents": True
            },
            AssetType.AUDIO.value: {
                "max_duration": 300,  # 5 minutes
                "compression": "vorbis",
                "quality": 0.7
            }
        }
        
        return configs
    
    async def submit_generation_request(self, request: AssetGenerationRequest) -> str:
        """Submit an asset generation request."""
        
        # Log the request
        advanced_log_manager.log_advanced(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            f"Asset generation request submitted: {request.asset_type.value} '{request.name}'",
            operation="asset_generation_request",
            request_id=request.request_id,
            user_id=request.user_id,
            session_id=request.session_id,
            asset_type=request.asset_type.value,
            generation_method=request.generation_method.value
        )
        
        # Validate request
        try:
            self._validate_generation_request(request)
        except ValidationError as e:
            advanced_log_manager.log_advanced(
                LogLevel.ERROR,
                LogCategory.SYSTEM,
                f"Asset generation request validation failed: {e.message}",
                request_id=request.request_id,
                error_type="ValidationError"
            )
            raise
        
        # Add to queue and active requests
        self.active_requests[request.request_id] = request
        self.request_queue.append(request)
        self.stats["total_requests"] += 1
        
        # Sort queue by priority
        self.request_queue.sort(key=lambda r: r.priority, reverse=True)
        
        # Start processing if not at capacity
        if len([r for r in self.active_requests.values() if r.request_id not in self.completed_requests]) < self.max_concurrent_jobs:
            asyncio.create_task(self._process_next_request())
        
        return request.request_id
    
    def _validate_generation_request(self, request: AssetGenerationRequest):
        """Validate asset generation request."""
        
        # Check asset type support
        if request.asset_type not in AssetType:
            raise ValidationError(f"Unsupported asset type: {request.asset_type}")
        
        # Check generation method support
        if request.generation_method not in GenerationMethod:
            raise ValidationError(f"Unsupported generation method: {request.generation_method}")
        
        # Validate name
        if not request.name or not request.name.strip():
            raise ValidationError("Asset name cannot be empty")
        
        # Check for invalid characters in name
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in request.name for char in invalid_chars):
            raise ValidationError(f"Asset name contains invalid characters: {invalid_chars}")
        
        # Validate output path
        if not request.output_path.startswith("Assets/"):
            raise ValidationError("Output path must be within Assets folder")
        
        # Asset-specific validation
        if request.asset_type == AssetType.TEXTURE:
            self._validate_texture_request(request)
        elif request.asset_type == AssetType.MESH:
            self._validate_mesh_request(request)
        elif request.asset_type == AssetType.SCRIPT:
            self._validate_script_request(request)
    
    def _validate_texture_request(self, request: AssetGenerationRequest):
        """Validate texture generation request."""
        
        params = request.parameters
        config = self.generation_configs.get(AssetType.TEXTURE.value, {})
        
        # Check dimensions
        width = params.get("width", 256)
        height = params.get("height", 256)
        max_size = config.get("max_size", 4096)
        
        if width > max_size or height > max_size:
            raise ValidationError(f"Texture dimensions exceed maximum size: {max_size}x{max_size}")
        
        if width <= 0 or height <= 0:
            raise ValidationError("Texture dimensions must be positive")
    
    def _validate_mesh_request(self, request: AssetGenerationRequest):
        """Validate mesh generation request."""
        
        params = request.parameters
        config = self.generation_configs.get(AssetType.MESH.value, {})
        
        # Check vertex count
        vertex_count = params.get("vertex_count", 0)
        max_vertices = config.get("max_vertices", 65000)
        
        if vertex_count > max_vertices:
            raise ValidationError(f"Mesh vertex count exceeds maximum: {max_vertices}")
    
    def _validate_script_request(self, request: AssetGenerationRequest):
        """Validate script generation request."""
        
        params = request.parameters
        
        # Check class name
        class_name = params.get("class_name", request.name)
        if not class_name.isidentifier():
            raise ValidationError("Class name must be a valid identifier")
    
    async def _process_next_request(self):
        """Process the next request in the queue."""
        
        if not self.request_queue:
            return
        
        request = self.request_queue.pop(0)
        
        try:
            result = await self._generate_asset(request)
            self.completed_requests[request.request_id] = result
            
            if result.success:
                self.stats["successful_generations"] += 1
                self.stats["total_assets_generated"] += 1
            else:
                self.stats["failed_generations"] += 1
            
            # Update average generation time
            total_time = self.stats["average_generation_time"] * (self.stats["successful_generations"] + self.stats["failed_generations"] - 1)
            self.stats["average_generation_time"] = (total_time + result.generation_time) / (self.stats["successful_generations"] + self.stats["failed_generations"])
            
        except Exception as e:
            # Handle unexpected errors
            result = AssetGenerationResult(
                request_id=request.request_id,
                success=False,
                errors=[str(e)]
            )
            self.completed_requests[request.request_id] = result
            self.stats["failed_generations"] += 1
            
            advanced_log_manager.log_advanced(
                LogLevel.ERROR,
                LogCategory.SYSTEM,
                f"Unexpected error in asset generation: {str(e)}",
                request_id=request.request_id,
                error_type=type(e).__name__
            )
        
        finally:
            # Remove from active requests
            self.active_requests.pop(request.request_id, None)
            
            # Process next request if queue not empty
            if self.request_queue:
                asyncio.create_task(self._process_next_request())
    
    async def _generate_asset(self, request: AssetGenerationRequest) -> AssetGenerationResult:
        """Generate an asset based on the request."""
        
        start_time = time.time()
        result = AssetGenerationResult(request_id=request.request_id, success=False)
        
        try:
            advanced_log_manager.log_advanced(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                f"Starting asset generation: {request.asset_type.value} '{request.name}'",
                request_id=request.request_id,
                operation="asset_generation_start"
            )
            
            # Stage 1: Validation
            result.processing_stages.append(ProcessingStage.VALIDATION.value)
            await self._process_validation_stage(request, result)
            
            # Stage 2: Generation
            result.processing_stages.append(ProcessingStage.GENERATION.value)
            await self._process_generation_stage(request, result)
            
            # Stage 3: Optimization
            result.processing_stages.append(ProcessingStage.OPTIMIZATION.value)
            await self._process_optimization_stage(request, result)
            
            # Stage 4: Import
            result.processing_stages.append(ProcessingStage.IMPORT.value)
            await self._process_import_stage(request, result)
            
            # Stage 5: Post-processing
            result.processing_stages.append(ProcessingStage.POST_PROCESSING.value)
            await self._process_post_processing_stage(request, result)
            
            # Stage 6: Finalization
            result.processing_stages.append(ProcessingStage.FINALIZATION.value)
            await self._process_finalization_stage(request, result)
            
            result.success = True
            result.generation_time = time.time() - start_time
            
            advanced_log_manager.log_advanced(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                f"Asset generation completed: {request.asset_type.value} '{request.name}'",
                request_id=request.request_id,
                duration=result.generation_time,
                success=True,
                asset_path=result.asset_path
            )
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            result.generation_time = time.time() - start_time
            
            # Attempt error recovery
            log_context = LogContext(
                operation="asset_generation",
                request_id=request.request_id,
                user_id=request.user_id,
                session_id=request.session_id
            )
            
            recovery_result = await error_recovery_manager.handle_error(
                e, log_context, {"request": request.__dict__}
            )
            
            if recovery_result["success"]:
                result.success = True
                result.warnings.append(f"Generation recovered: {recovery_result['message']}")
            
            advanced_log_manager.log_advanced(
                LogLevel.ERROR,
                LogCategory.SYSTEM,
                f"Asset generation failed: {request.asset_type.value} '{request.name}': {str(e)}",
                request_id=request.request_id,
                duration=result.generation_time,
                success=False,
                error_type=type(e).__name__,
                recovery_applied=recovery_result["success"]
            )
        
        return result
    
    async def _process_validation_stage(self, request: AssetGenerationRequest, result: AssetGenerationResult):
        """Process validation stage."""
        # Additional validation beyond initial request validation
        pass
    
    async def _process_generation_stage(self, request: AssetGenerationRequest, result: AssetGenerationResult):
        """Process generation stage."""
        
        if request.generation_method == GenerationMethod.TEMPLATE_BASED:
            await self._generate_from_template(request, result)
        elif request.generation_method == GenerationMethod.PROCEDURAL:
            await self._generate_procedural(request, result)
        elif request.generation_method == GenerationMethod.DUPLICATE_EXISTING:
            await self._duplicate_existing_asset(request, result)
        else:
            raise UnityOperationError(f"Generation method not implemented: {request.generation_method}")
    
    async def _generate_from_template(self, request: AssetGenerationRequest, result: AssetGenerationResult):
        """Generate asset from template."""
        
        template_name = request.parameters.get("template", "default")
        templates = self.asset_templates.get(request.asset_type.value, {})
        
        if template_name not in templates:
            raise ValidationError(f"Template '{template_name}' not found for {request.asset_type.value}")
        
        template = templates[template_name]
        
        # Create asset path
        asset_filename = f"{request.name}.{self._get_asset_extension(request.asset_type)}"
        result.asset_path = os.path.join(request.output_path, asset_filename).replace("\\", "/")
        
        # Generate based on asset type
        if request.asset_type == AssetType.MATERIAL:
            await self._generate_material_from_template(request, result, template)
        elif request.asset_type == AssetType.SCRIPT:
            await self._generate_script_from_template(request, result, template)
        elif request.asset_type == AssetType.TEXTURE:
            await self._generate_texture_from_template(request, result, template)
    
    async def _generate_procedural(self, request: AssetGenerationRequest, result: AssetGenerationResult):
        """Generate asset procedurally."""
        # Implement procedural generation based on asset type
        pass
    
    async def _duplicate_existing_asset(self, request: AssetGenerationRequest, result: AssetGenerationResult):
        """Duplicate an existing asset."""
        source_path = request.parameters.get("source_path")
        if not source_path:
            raise ValidationError("Source path required for duplication")
        
        # Implementation would duplicate the asset
        pass
    
    async def _generate_material_from_template(self, request: AssetGenerationRequest, 
                                             result: AssetGenerationResult, template: Dict[str, Any]):
        """Generate material from template."""
        # Implementation would create Unity material
        pass
    
    async def _generate_script_from_template(self, request: AssetGenerationRequest, 
                                           result: AssetGenerationResult, template: Dict[str, Any]):
        """Generate script from template."""
        # Implementation would create Unity script
        pass
    
    async def _generate_texture_from_template(self, request: AssetGenerationRequest, 
                                            result: AssetGenerationResult, template: Dict[str, Any]):
        """Generate texture from template."""
        # Implementation would create Unity texture
        pass
    
    async def _process_optimization_stage(self, request: AssetGenerationRequest, result: AssetGenerationResult):
        """Process optimization stage."""
        # Apply optimizations based on asset type and configuration
        pass
    
    async def _process_import_stage(self, request: AssetGenerationRequest, result: AssetGenerationResult):
        """Process import stage."""
        # Import asset into Unity
        pass
    
    async def _process_post_processing_stage(self, request: AssetGenerationRequest, result: AssetGenerationResult):
        """Process post-processing stage."""
        # Apply post-processing effects or modifications
        pass
    
    async def _process_finalization_stage(self, request: AssetGenerationRequest, result: AssetGenerationResult):
        """Process finalization stage."""
        # Final cleanup and metadata assignment
        if result.asset_path and os.path.exists(result.asset_path):
            result.file_size = os.path.getsize(result.asset_path)
    
    def _get_asset_extension(self, asset_type: AssetType) -> str:
        """Get file extension for asset type."""
        
        extensions = {
            AssetType.MATERIAL: "mat",
            AssetType.TEXTURE: "png",
            AssetType.SCRIPT: "cs",
            AssetType.SHADER: "shader",
            AssetType.PREFAB: "prefab",
            AssetType.SCENE: "unity",
            AssetType.AUDIO: "wav",
            AssetType.MESH: "asset"
        }
        
        return extensions.get(asset_type, "asset")
    
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Get status of a generation request."""
        
        if request_id in self.completed_requests:
            result = self.completed_requests[request_id]
            return {
                "status": "completed",
                "success": result.success,
                "asset_path": result.asset_path,
                "generation_time": result.generation_time,
                "processing_stages": result.processing_stages,
                "warnings": result.warnings,
                "errors": result.errors
            }
        elif request_id in self.active_requests:
            return {
                "status": "processing",
                "request": self.active_requests[request_id].__dict__
            }
        else:
            return {
                "status": "not_found",
                "error": f"Request {request_id} not found"
            }
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        
        return {
            "statistics": self.stats,
            "active_requests": len(self.active_requests),
            "queue_length": len(self.request_queue),
            "completed_requests": len(self.completed_requests),
            "max_concurrent_jobs": self.max_concurrent_jobs
        }


# Global asset generation pipeline instance
asset_generation_pipeline = AssetGenerationPipeline()
