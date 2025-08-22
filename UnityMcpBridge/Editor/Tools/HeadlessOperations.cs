using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.SceneManagement;
using Newtonsoft.Json.Linq;
using UnityMcpBridge.Editor.Helpers;

namespace UnityMcpBridge.Editor.Tools
{
    /// <summary>
    /// Enhanced operations specifically designed for headless Unity operations.
    /// Includes scene management, build operations, and asset generation optimized for batch mode.
    /// </summary>
    public static class HeadlessOperations
    {
        /// <summary>
        /// Handle headless-specific operations with enhanced error handling and logging.
        /// </summary>
        public static object HandleCommand(JObject parameters)
        {
            try
            {
                string action = parameters["action"]?.ToString();
                if (string.IsNullOrEmpty(action))
                {
                    throw new ArgumentException("Action parameter is required");
                }

                return action.ToLower() switch
                {
                    "create_empty_scene" => CreateEmptyScene(parameters),
                    "load_scene" => LoadScene(parameters),
                    "save_scene" => SaveScene(parameters),
                    "build_webgl" => BuildWebGL(parameters),
                    "build_standalone" => BuildStandalone(parameters),
                    "get_scene_info" => GetSceneInfo(parameters),
                    "create_basic_objects" => CreateBasicObjects(parameters),
                    "setup_basic_lighting" => SetupBasicLighting(parameters),
                    "generate_build_report" => GenerateBuildReport(parameters),
                    _ => throw new ArgumentException($"Unknown headless action: {action}")
                };
            }
            catch (Exception ex)
            {
                Debug.LogError($"[HeadlessOperations] Error in HandleCommand: {ex.Message}\n{ex.StackTrace}");
                return new { success = false, error = ex.Message, details = ex.StackTrace };
            }
        }

        /// <summary>
        /// Create a new empty scene optimized for headless operations.
        /// </summary>
        private static object CreateEmptyScene(JObject parameters)
        {
            try
            {
                string sceneName = parameters["sceneName"]?.ToString() ?? "HeadlessScene";
                string scenePath = parameters["scenePath"]?.ToString() ?? $"Assets/Scenes/{sceneName}.unity";
                bool addDefaultObjects = parameters["addDefaultObjects"]?.ToObject<bool>() ?? true;

                // Create new scene
                var newScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                
                if (addDefaultObjects)
                {
                    // Add essential objects for headless operations
                    CreateDefaultSceneObjects();
                }

                // Ensure directory exists
                string sceneDir = Path.GetDirectoryName(scenePath);
                if (!Directory.Exists(sceneDir))
                {
                    Directory.CreateDirectory(sceneDir);
                    AssetDatabase.Refresh();
                }

                // Save the scene
                bool saved = EditorSceneManager.SaveScene(newScene, scenePath);
                
                if (!saved)
                {
                    throw new InvalidOperationException($"Failed to save scene to {scenePath}");
                }

                AssetDatabase.Refresh();

                return new
                {
                    success = true,
                    message = $"Created scene {sceneName}",
                    data = new
                    {
                        sceneName = newScene.name,
                        scenePath = scenePath,
                        sceneHandle = newScene.handle,
                        objectCount = GetSceneObjectCount(newScene)
                    }
                };
            }
            catch (Exception ex)
            {
                return new { success = false, error = $"Failed to create scene: {ex.Message}" };
            }
        }

        /// <summary>
        /// Load an existing scene by path or name.
        /// </summary>
        private static object LoadScene(JObject parameters)
        {
            try
            {
                string scenePath = parameters["scenePath"]?.ToString();
                string sceneName = parameters["sceneName"]?.ToString();

                if (string.IsNullOrEmpty(scenePath) && string.IsNullOrEmpty(sceneName))
                {
                    throw new ArgumentException("Either scenePath or sceneName must be provided");
                }

                // If only name is provided, try to find the scene
                if (string.IsNullOrEmpty(scenePath) && !string.IsNullOrEmpty(sceneName))
                {
                    scenePath = FindScenePathByName(sceneName);
                    if (string.IsNullOrEmpty(scenePath))
                    {
                        throw new FileNotFoundException($"Scene '{sceneName}' not found in project");
                    }
                }

                // Load the scene
                var scene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);

                return new
                {
                    success = true,
                    message = $"Loaded scene {scene.name}",
                    data = new
                    {
                        sceneName = scene.name,
                        scenePath = scene.path,
                        sceneHandle = scene.handle,
                        objectCount = GetSceneObjectCount(scene),
                        isLoaded = scene.isLoaded,
                        isDirty = scene.isDirty
                    }
                };
            }
            catch (Exception ex)
            {
                return new { success = false, error = $"Failed to load scene: {ex.Message}" };
            }
        }

        /// <summary>
        /// Save the current scene with optional path.
        /// </summary>
        private static object SaveScene(JObject parameters)
        {
            try
            {
                string scenePath = parameters["scenePath"]?.ToString();
                bool saveAsNew = parameters["saveAsNew"]?.ToObject<bool>() ?? false;

                Scene currentScene = SceneManager.GetActiveScene();
                
                if (string.IsNullOrEmpty(scenePath))
                {
                    if (string.IsNullOrEmpty(currentScene.path))
                    {
                        throw new InvalidOperationException("Scene path must be provided for new scenes");
                    }
                    scenePath = currentScene.path;
                }

                bool saved;
                if (saveAsNew || string.IsNullOrEmpty(currentScene.path))
                {
                    saved = EditorSceneManager.SaveScene(currentScene, scenePath);
                }
                else
                {
                    saved = EditorSceneManager.SaveScene(currentScene);
                }

                if (!saved)
                {
                    throw new InvalidOperationException("Failed to save scene");
                }

                AssetDatabase.Refresh();

                return new
                {
                    success = true,
                    message = $"Saved scene {currentScene.name}",
                    data = new
                    {
                        sceneName = currentScene.name,
                        scenePath = currentScene.path,
                        objectCount = GetSceneObjectCount(currentScene)
                    }
                };
            }
            catch (Exception ex)
            {
                return new { success = false, error = $"Failed to save scene: {ex.Message}" };
            }
        }

        /// <summary>
        /// Build WebGL with optimized settings for headless operations.
        /// </summary>
        private static object BuildWebGL(JObject parameters)
        {
            try
            {
                string buildPath = parameters["buildPath"]?.ToString() ?? "Builds/WebGL";
                string[] scenes = GetBuildScenes(parameters);
                bool developmentBuild = parameters["developmentBuild"]?.ToObject<bool>() ?? false;

                // Ensure build directory exists
                Directory.CreateDirectory(buildPath);

                // Configure build settings
                BuildPlayerOptions buildOptions = new BuildPlayerOptions
                {
                    scenes = scenes,
                    locationPathName = buildPath,
                    target = BuildTarget.WebGL,
                    options = developmentBuild ? BuildOptions.Development : BuildOptions.None
                };

                // Optional: Configure WebGL-specific settings
                PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Gzip;
                PlayerSettings.WebGL.linkerTarget = WebGLLinkerTarget.Wasm;

                var startTime = DateTime.Now;
                BuildReport report = BuildPipeline.BuildPlayer(buildOptions);
                var buildTime = DateTime.Now - startTime;

                bool success = report.summary.result == BuildResult.Succeeded;
                
                return new
                {
                    success = success,
                    message = success ? "WebGL build completed successfully" : "WebGL build failed",
                    data = new
                    {
                        buildResult = report.summary.result.ToString(),
                        buildPath = buildPath,
                        buildTime = buildTime.TotalSeconds,
                        totalSize = report.summary.totalSize,
                        totalErrors = report.summary.totalErrors,
                        totalWarnings = report.summary.totalWarnings,
                        scenes = scenes,
                        platform = "WebGL"
                    }
                };
            }
            catch (Exception ex)
            {
                return new { success = false, error = $"WebGL build failed: {ex.Message}" };
            }
        }

        /// <summary>
        /// Build standalone executable with platform detection.
        /// </summary>
        private static object BuildStandalone(JObject parameters)
        {
            try
            {
                string buildPath = parameters["buildPath"]?.ToString() ?? "Builds/Standalone";
                string[] scenes = GetBuildScenes(parameters);
                bool developmentBuild = parameters["developmentBuild"]?.ToObject<bool>() ?? false;
                string targetPlatform = parameters["targetPlatform"]?.ToString() ?? "current";

                // Determine build target
                BuildTarget buildTarget = GetBuildTarget(targetPlatform);
                
                // Adjust build path with executable extension
                if (buildTarget == BuildTarget.StandaloneWindows || buildTarget == BuildTarget.StandaloneWindows64)
                {
                    if (!buildPath.EndsWith(".exe"))
                    {
                        buildPath = Path.Combine(buildPath, $"{PlayerSettings.productName}.exe");
                    }
                }

                // Ensure build directory exists
                Directory.CreateDirectory(Path.GetDirectoryName(buildPath));

                BuildPlayerOptions buildOptions = new BuildPlayerOptions
                {
                    scenes = scenes,
                    locationPathName = buildPath,
                    target = buildTarget,
                    options = developmentBuild ? BuildOptions.Development : BuildOptions.None
                };

                var startTime = DateTime.Now;
                BuildReport report = BuildPipeline.BuildPlayer(buildOptions);
                var buildTime = DateTime.Now - startTime;

                bool success = report.summary.result == BuildResult.Succeeded;

                return new
                {
                    success = success,
                    message = success ? "Standalone build completed successfully" : "Standalone build failed",
                    data = new
                    {
                        buildResult = report.summary.result.ToString(),
                        buildPath = buildPath,
                        buildTime = buildTime.TotalSeconds,
                        totalSize = report.summary.totalSize,
                        totalErrors = report.summary.totalErrors,
                        totalWarnings = report.summary.totalWarnings,
                        scenes = scenes,
                        platform = buildTarget.ToString()
                    }
                };
            }
            catch (Exception ex)
            {
                return new { success = false, error = $"Standalone build failed: {ex.Message}" };
            }
        }

        /// <summary>
        /// Get comprehensive scene information for headless operations.
        /// </summary>
        private static object GetSceneInfo(JObject parameters)
        {
            try
            {
                Scene currentScene = SceneManager.GetActiveScene();
                
                var rootObjects = currentScene.GetRootGameObjects();
                var sceneInfo = new
                {
                    name = currentScene.name,
                    path = currentScene.path,
                    handle = currentScene.handle,
                    isLoaded = currentScene.isLoaded,
                    isDirty = currentScene.isDirty,
                    buildIndex = currentScene.buildIndex,
                    objectCount = rootObjects.Length,
                    totalGameObjects = GetSceneObjectCount(currentScene),
                    rootObjects = rootObjects.Select(obj => new
                    {
                        name = obj.name,
                        tag = obj.tag,
                        layer = obj.layer,
                        active = obj.activeInHierarchy,
                        components = obj.GetComponents<Component>().Select(c => c.GetType().Name).ToArray()
                    }).ToArray()
                };

                return new
                {
                    success = true,
                    message = $"Retrieved info for scene {currentScene.name}",
                    data = sceneInfo
                };
            }
            catch (Exception ex)
            {
                return new { success = false, error = $"Failed to get scene info: {ex.Message}" };
            }
        }

        /// <summary>
        /// Create basic objects in the scene for testing purposes.
        /// </summary>
        private static object CreateBasicObjects(JObject parameters)
        {
            try
            {
                int cubeCount = parameters["cubeCount"]?.ToObject<int>() ?? 1;
                int sphereCount = parameters["sphereCount"]?.ToObject<int>() ?? 1;
                bool addLighting = parameters["addLighting"]?.ToObject<bool>() ?? true;

                var createdObjects = new List<string>();

                // Create cubes
                for (int i = 0; i < cubeCount; i++)
                {
                    var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    cube.name = $"TestCube_{i}";
                    cube.transform.position = new Vector3(i * 2, 0, 0);
                    createdObjects.Add(cube.name);
                }

                // Create spheres
                for (int i = 0; i < sphereCount; i++)
                {
                    var sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    sphere.name = $"TestSphere_{i}";
                    sphere.transform.position = new Vector3(i * 2, 0, 2);
                    createdObjects.Add(sphere.name);
                }

                if (addLighting)
                {
                    SetupBasicLighting(parameters);
                }

                return new
                {
                    success = true,
                    message = $"Created {createdObjects.Count} basic objects",
                    data = new
                    {
                        createdObjects = createdObjects.ToArray(),
                        cubeCount = cubeCount,
                        sphereCount = sphereCount,
                        lightingAdded = addLighting
                    }
                };
            }
            catch (Exception ex)
            {
                return new { success = false, error = $"Failed to create basic objects: {ex.Message}" };
            }
        }

        /// <summary>
        /// Setup basic lighting for the scene.
        /// </summary>
        private static object SetupBasicLighting(JObject parameters)
        {
            try
            {
                bool addDirectionalLight = parameters["addDirectionalLight"]?.ToObject<bool>() ?? true;
                bool configureSkybox = parameters["configureSkybox"]?.ToObject<bool>() ?? true;

                var lightingSetup = new List<string>();

                if (addDirectionalLight)
                {
                    // Create main directional light
                    var lightObject = new GameObject("Main Light");
                    var light = lightObject.AddComponent<Light>();
                    light.type = LightType.Directional;
                    light.intensity = 1.0f;
                    light.color = Color.white;
                    lightObject.transform.rotation = Quaternion.Euler(30, 0, 0);
                    lightingSetup.Add("Directional Light");
                }

                if (configureSkybox)
                {
                    // Configure basic rendering settings
                    RenderSettings.skybox = AssetDatabase.GetBuiltinExtraResource<Material>("Default-Skybox");
                    RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Skybox;
                    lightingSetup.Add("Skybox");
                }

                return new
                {
                    success = true,
                    message = "Basic lighting setup completed",
                    data = new
                    {
                        lightingSetup = lightingSetup.ToArray(),
                        ambientMode = RenderSettings.ambientMode.ToString()
                    }
                };
            }
            catch (Exception ex)
            {
                return new { success = false, error = $"Failed to setup lighting: {ex.Message}" };
            }
        }

        /// <summary>
        /// Generate a comprehensive build report.
        /// </summary>
        private static object GenerateBuildReport(JObject parameters)
        {
            try
            {
                var buildSettings = EditorBuildSettings.scenes;
                var playerSettings = new
                {
                    productName = PlayerSettings.productName,
                    companyName = PlayerSettings.companyName,
                    version = PlayerSettings.bundleVersion,
                    buildNumber = PlayerSettings.Android.bundleVersionCode, // Cross-platform
                    targetPlatform = EditorUserBuildSettings.activeBuildTarget.ToString()
                };

                return new
                {
                    success = true,
                    message = "Build report generated",
                    data = new
                    {
                        playerSettings = playerSettings,
                        buildScenes = buildSettings.Where(s => s.enabled).Select(s => s.path).ToArray(),
                        allScenes = buildSettings.Select(s => new { path = s.path, enabled = s.enabled }).ToArray(),
                        unityVersion = Application.unityVersion,
                        platform = Application.platform.ToString(),
                        timestamp = DateTime.UtcNow.ToString("O")
                    }
                };
            }
            catch (Exception ex)
            {
                return new { success = false, error = $"Failed to generate build report: {ex.Message}" };
            }
        }

        #region Helper Methods

        private static void CreateDefaultSceneObjects()
        {
            // Create camera if none exists
            if (Camera.main == null)
            {
                var cameraObject = new GameObject("Main Camera");
                var camera = cameraObject.AddComponent<Camera>();
                cameraObject.tag = "MainCamera";
                cameraObject.transform.position = new Vector3(0, 1, -10);
            }

            // Create directional light if none exists
            if (FindObjectOfType<Light>() == null)
            {
                var lightObject = new GameObject("Directional Light");
                var light = lightObject.AddComponent<Light>();
                light.type = LightType.Directional;
                light.intensity = 1.0f;
                lightObject.transform.rotation = Quaternion.Euler(50, -30, 0);
            }
        }

        private static int GetSceneObjectCount(Scene scene)
        {
            return scene.GetRootGameObjects()
                .Sum(rootObj => rootObj.GetComponentsInChildren<Transform>(true).Length);
        }

        private static string FindScenePathByName(string sceneName)
        {
            string[] guids = AssetDatabase.FindAssets($"{sceneName} t:Scene");
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (Path.GetFileNameWithoutExtension(path).Equals(sceneName, StringComparison.OrdinalIgnoreCase))
                {
                    return path;
                }
            }
            return null;
        }

        private static string[] GetBuildScenes(JObject parameters)
        {
            var scenesParam = parameters["scenes"];
            if (scenesParam != null && scenesParam.Type == JTokenType.Array)
            {
                return scenesParam.ToObject<string[]>();
            }

            // Use scenes from build settings
            return EditorBuildSettings.scenes
                .Where(scene => scene.enabled)
                .Select(scene => scene.path)
                .ToArray();
        }

        private static BuildTarget GetBuildTarget(string targetPlatform)
        {
            return targetPlatform.ToLower() switch
            {
                "windows" or "win" or "win64" => BuildTarget.StandaloneWindows64,
                "windows32" or "win32" => BuildTarget.StandaloneWindows,
                "mac" or "macos" or "osx" => BuildTarget.StandaloneOSX,
                "linux" => BuildTarget.StandaloneLinux64,
                "webgl" => BuildTarget.WebGL,
                "android" => BuildTarget.Android,
                "ios" => BuildTarget.iOS,
                "current" => EditorUserBuildSettings.activeBuildTarget,
                _ => EditorUserBuildSettings.activeBuildTarget
            };
        }

        #endregion
    }
}