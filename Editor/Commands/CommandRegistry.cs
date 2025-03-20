using System;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;

namespace UnityMCP.Editor.Commands
{
    /// <summary>
    /// Registry for all MCP command handlers
    /// </summary>
    public static class CommandRegistry
    {
        private static readonly Dictionary<string, Func<JObject, object>> _handlers = new()
        {
            // Scene management commands
            { "GET_SCENE_INFO", _ => SceneCommandHandler.GetSceneInfo() },
            { "OPEN_SCENE", parameters => SceneCommandHandler.OpenScene(parameters) },
            { "SAVE_SCENE", _ => SceneCommandHandler.SaveScene() },
            { "NEW_SCENE", parameters => SceneCommandHandler.NewScene(parameters) },
            { "CHANGE_SCENE", parameters => SceneCommandHandler.ChangeScene(parameters) },

            // Asset management commands
            { "IMPORT_ASSET", parameters => AssetCommandHandler.ImportAsset(parameters) },
            { "INSTANTIATE_PREFAB", parameters => AssetCommandHandler.InstantiatePrefab(parameters) },
            { "CREATE_PREFAB", parameters => AssetCommandHandler.CreatePrefab(parameters) },
            { "APPLY_PREFAB", parameters => AssetCommandHandler.ApplyPrefab(parameters) },
            { "GET_ASSET_LIST", parameters => AssetCommandHandler.GetAssetList(parameters) },

            // Object management commands
            { "GET_OBJECT_PROPERTIES", parameters => ObjectCommandHandler.GetObjectProperties(parameters) },
            { "GET_COMPONENT_PROPERTIES", parameters => ObjectCommandHandler.GetComponentProperties(parameters) },
            { "FIND_OBJECTS_BY_NAME", parameters => ObjectCommandHandler.FindObjectsByName(parameters) },
            { "FIND_OBJECTS_BY_TAG", parameters => ObjectCommandHandler.FindObjectsByTag(parameters) },
            { "GET_HIERARCHY", _ => ObjectCommandHandler.GetHierarchy() },
            { "SELECT_OBJECT", parameters => ObjectCommandHandler.SelectObject(parameters) },
            { "GET_SELECTED_OBJECT", _ => ObjectCommandHandler.GetSelectedObject() },

            // Editor control commands
            { "EDITOR_CONTROL", parameters => EditorControlHandler.HandleEditorControl(parameters) },

            // Hyper3D Rodin commands
            { "GET_HYPER3D_STATUS", _ => Hyper3DRodin.Hyper3DRodinCommandHandler.GetHyper3DStatus() },
            { "CREATE_RODIN_JOB", parameters => Hyper3DRodin.Hyper3DRodinCommandHandler.CreateRodinJob(parameters) },
            { "POLL_RODIN_JOB_STATUS", parameters => Hyper3DRodin.Hyper3DRodinCommandHandler.PollRodinJobStatus(parameters) },
            { "DOWNLOAD_RODIN_JOB_RESULT", parameters => Hyper3DRodin.Hyper3DRodinCommandHandler.DownloadRodinJobResult(parameters) },
        };

        /// <summary>
        /// Gets a command handler by name
        /// </summary>
        /// <param name="commandName">Name of the command to get</param>
        /// <returns>The command handler function if found, null otherwise</returns>
        public static Func<JObject, object> GetHandler(string commandName)
        {
            return _handlers.TryGetValue(commandName, out var handler) ? handler : null;
        }
    }
}