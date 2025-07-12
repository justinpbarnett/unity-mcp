using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityMcpBridge.Editor.Models;
using UnityMcpBridge.Editor.Helpers;

namespace Examples.CustomMcpTools
{
    /// <summary>
    /// Custom MCP Tool Example: Project Information Tool
    /// 
    /// Users only need to create a class like this, and Unity MCP Bridge will automatically discover and register it
    /// </summary>
    public class ProjectInfoTool : IUnityMcpTool
    {
        public string CommandType => "project_info";
        
        public string Description => "Get detailed Unity project information including version, settings, asset statistics etc.";
        
        public object HandleCommand(JObject parameters)
        {
            try
            {
                string action = parameters["action"]?.ToString()?.ToLower() ?? "summary";

                return action switch
                {
                    "summary" => GetProjectSummary(),
                    "assets" => GetAssetStatistics(),
                    "settings" => GetProjectSettings(),
                    "scenes" => GetSceneInfo(),
                    "packages" => GetPackageInfo(),
                    _ => Response.Error($"Unknown action: {action}. Supported actions: summary, assets, settings, scenes, packages")
                };
            }
            catch (Exception ex)
            {
                return Response.Error($"Error executing project information query: {ex.Message}");
            }
        }

        private object GetProjectSummary()
        {
            return Response.Success(new
            {
                projectName = Application.productName,
                unityVersion = Application.unityVersion,
                projectPath = Application.dataPath.Replace("/Assets", ""),
                companyName = Application.companyName,
                version = Application.version,
                targetPlatform = EditorUserBuildSettings.activeBuildTarget.ToString(),
                developmentBuild = EditorUserBuildSettings.development,
                scriptDefines = PlayerSettings.GetScriptingDefineSymbolsForGroup(EditorUserBuildSettings.selectedBuildTargetGroup)
            });
        }

        private object GetAssetStatistics()
        {
            var assetGuids = AssetDatabase.FindAssets("");
            var assetsByType = assetGuids
                .Select(AssetDatabase.GUIDToAssetPath)
                .Where(path => !string.IsNullOrEmpty(path))
                .GroupBy(path => Path.GetExtension(path).ToLower())
                .ToDictionary(g => g.Key, g => g.Count());

            var totalSize = assetGuids
                .Select(AssetDatabase.GUIDToAssetPath)
                .Where(path => !string.IsNullOrEmpty(path) && File.Exists(path))
                .Sum(path => new FileInfo(path).Length);

            return Response.Success(new
            {
                totalAssets = assetGuids.Length,
                assetsByExtension = assetsByType,
                totalSizeBytes = totalSize,
                totalSizeMB = Math.Round(totalSize / (1024.0 * 1024.0), 2)
            });
        }

        private object GetProjectSettings()
        {
            return Response.Success(new
            {
                colorSpace = PlayerSettings.colorSpace.ToString(),
                apiCompatibilityLevel = PlayerSettings.GetApiCompatibilityLevel(EditorUserBuildSettings.selectedBuildTargetGroup).ToString(),
                scriptingBackend = PlayerSettings.GetScriptingBackend(EditorUserBuildSettings.selectedBuildTargetGroup).ToString(),
                il2CppCompilerConfiguration = PlayerSettings.GetIl2CppCompilerConfiguration(EditorUserBuildSettings.selectedBuildTargetGroup).ToString(),
                bundleVersion = PlayerSettings.bundleVersion,
                minimumSupportedOSVersion = PlayerSettings.macOS.minimumSystemVersion,
                graphicsAPI = SystemInfo.graphicsDeviceName,
                renderPipeline = GraphicsSettings.renderPipelineAsset?.name ?? "Built-in"
            });
        }

        private object GetSceneInfo()
        {
            var buildScenes = EditorBuildSettings.scenes
                .Select(scene => new
                {
                    path = scene.path,
                    enabled = scene.enabled,
                    guid = scene.guid.ToString()
                })
                .ToArray();

            var currentScene = EditorSceneManager.GetActiveScene();

            return Response.Success(new
            {
                currentScene = new
                {
                    name = currentScene.name,
                    path = currentScene.path,
                    isLoaded = currentScene.isLoaded,
                    isDirty = currentScene.isDirty,
                    gameObjectCount = currentScene.rootCount
                },
                buildScenes = buildScenes,
                totalBuildScenes = buildScenes.Length,
                enabledBuildScenes = buildScenes.Count(s => s.enabled)
            });
        }

        private object GetPackageInfo()
        {
            var request = UnityEditor.PackageManager.Client.List();
            while (!request.IsCompleted)
            {
                // Simple wait, might need async handling in real projects
                System.Threading.Thread.Sleep(10);
            }

            if (request.Status == UnityEditor.PackageManager.StatusCode.Success)
            {
                var packages = request.Result
                    .Select(package => new
                    {
                        name = package.name,
                        displayName = package.displayName,
                        version = package.version,
                        source = package.source.ToString(),
                        status = package.status.ToString()
                    })
                    .ToArray();

                return Response.Success(new
                {
                    packages = packages,
                    totalPackages = packages.Length
                });
            }
            else
            {
                return Response.Error($"Failed to get package information: {request.Error?.message}");
            }
        }
    }
}