using System;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityMcpBridge.Editor.Models;
using UnityMcpBridge.Editor.Helpers;

namespace Examples.CustomMcpTools
{
    /// <summary>
    /// Custom MCP Tool Example: Editor UI Interaction Tool
    /// 
    /// Demonstrates how to create custom MCP tools that interact with Unity Editor UI
    /// </summary>
    public class EditorUITool : IUnityMcpTool
    {
        public string CommandType => "editor_ui";
        
        public string Description => "Interact with Unity Editor UI including window operations, layout management, selection operations etc.";
        
        public object HandleCommand(JObject parameters)
        {
            try
            {
                string action = parameters["action"]?.ToString()?.ToLower();
                if (string.IsNullOrEmpty(action))
                {
                    return Response.Error("action parameter is required");
                }

                return action switch
                {
                    "get_windows" => GetOpenWindows(),
                    "focus_window" => FocusWindow(parameters),
                    "get_selection" => GetCurrentSelection(),
                    "select_objects" => SelectObjects(parameters),
                    "get_layout" => GetCurrentLayout(),
                    "maximize_window" => MaximizeWindow(parameters),
                    "show_notification" => ShowNotification(parameters),
                    "create_popup" => CreatePopup(parameters),
                    _ => Response.Error($"Unknown action: {action}. Supported actions: get_windows, focus_window, get_selection, select_objects, get_layout, maximize_window, show_notification, create_popup")
                };
            }
            catch (Exception ex)
            {
                return Response.Error($"Error executing editor UI operation: {ex.Message}");
            }
        }

        private object GetOpenWindows()
        {
            var windows = Resources.FindObjectsOfTypeAll<EditorWindow>()
                .Select(window => new
                {
                    title = window.titleContent.text,
                    type = window.GetType().Name,
                    position = new
                    {
                        x = window.position.x,
                        y = window.position.y,
                        width = window.position.width,
                        height = window.position.height
                    },
                    hasFocus = EditorWindow.focusedWindow == window,
                    maximized = window.maximized
                })
                .ToArray();

            return Response.Success(new
            {
                windows = windows,
                totalWindows = windows.Length,
                focusedWindow = EditorWindow.focusedWindow?.titleContent.text ?? "None"
            });
        }

        private object FocusWindow(JObject parameters)
        {
            string windowType = parameters["windowType"]?.ToString();
            string windowTitle = parameters["windowTitle"]?.ToString();

            if (string.IsNullOrEmpty(windowType) && string.IsNullOrEmpty(windowTitle))
            {
                return Response.Error("windowType or windowTitle parameter is required");
            }

            var windows = Resources.FindObjectsOfTypeAll<EditorWindow>();
            EditorWindow targetWindow = null;

            if (!string.IsNullOrEmpty(windowType))
            {
                targetWindow = windows.FirstOrDefault(w => w.GetType().Name.Equals(windowType, StringComparison.OrdinalIgnoreCase));
            }
            else if (!string.IsNullOrEmpty(windowTitle))
            {
                targetWindow = windows.FirstOrDefault(w => w.titleContent.text.Equals(windowTitle, StringComparison.OrdinalIgnoreCase));
            }

            if (targetWindow == null)
            {
                return Response.Error($"Window not found: {windowType ?? windowTitle}");
            }

            targetWindow.Focus();
            return Response.Success(new
            {
                message = $"Focused to window: {targetWindow.titleContent.text}",
                windowType = targetWindow.GetType().Name
            });
        }

        private object GetCurrentSelection()
        {
            var selectedObjects = Selection.objects;
            var selectedGameObjects = Selection.gameObjects;

            var selectionInfo = selectedObjects.Select(obj => new
            {
                name = obj.name,
                type = obj.GetType().Name,
                instanceId = obj.GetInstanceID(),
                assetPath = AssetDatabase.GetAssetPath(obj),
                isGameObject = obj is GameObject,
                isAsset = AssetDatabase.Contains(obj)
            }).ToArray();

            return Response.Success(new
            {
                selectedCount = selectedObjects.Length,
                gameObjectCount = selectedGameObjects.Length,
                activeObject = Selection.activeObject?.name,
                activeGameObject = Selection.activeGameObject?.name,
                selectionDetails = selectionInfo
            });
        }

        private object SelectObjects(JObject parameters)
        {
            var objectNames = parameters["objectNames"]?.ToObject<string[]>();
            var objectPaths = parameters["objectPaths"]?.ToObject<string[]>();

            if (objectNames == null && objectPaths == null)
            {
                return Response.Error("objectNames or objectPaths parameter is required");
            }

            var objectsToSelect = new System.Collections.Generic.List<UnityEngine.Object>();

            if (objectNames != null)
            {
                foreach (string name in objectNames)
                {
                    var obj = GameObject.Find(name);
                    if (obj != null)
                    {
                        objectsToSelect.Add(obj);
                    }
                }
            }

            if (objectPaths != null)
            {
                foreach (string path in objectPaths)
                {
                    var obj = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(path);
                    if (obj != null)
                    {
                        objectsToSelect.Add(obj);
                    }
                }
            }

            if (objectsToSelect.Count == 0)
            {
                return Response.Error("No specified objects found");
            }

            Selection.objects = objectsToSelect.ToArray();

            return Response.Success(new
            {
                message = $"Selected {objectsToSelect.Count} objects",
                selectedObjects = objectsToSelect.Select(obj => obj.name).ToArray()
            });
        }

        private object GetCurrentLayout()
        {
            return Response.Success(new
            {
                isMaximized = EditorWindow.focusedWindow?.maximized ?? false,
                focusedWindow = EditorWindow.focusedWindow?.titleContent.text ?? "None",
                windowCount = Resources.FindObjectsOfTypeAll<EditorWindow>().Length,
                mouseOverWindow = EditorWindow.mouseOverWindow?.titleContent.text ?? "None"
            });
        }

        private object MaximizeWindow(JObject parameters)
        {
            string windowType = parameters["windowType"]?.ToString();
            bool maximize = parameters["maximize"]?.ToObject<bool>() ?? true;

            if (string.IsNullOrEmpty(windowType))
            {
                // If no window specified, operate on the currently focused window
                if (EditorWindow.focusedWindow != null)
                {
                    EditorWindow.focusedWindow.maximized = maximize;
                    return Response.Success(new
                    {
                        message = $"{(maximize ? "Maximized" : "Restored")} current window: {EditorWindow.focusedWindow.titleContent.text}"
                    });
                }
                else
                {
                    return Response.Error("No focused window to operate on");
                }
            }

            var window = Resources.FindObjectsOfTypeAll<EditorWindow>()
                .FirstOrDefault(w => w.GetType().Name.Equals(windowType, StringComparison.OrdinalIgnoreCase));

            if (window == null)
            {
                return Response.Error($"Window of type {windowType} not found");
            }

            window.maximized = maximize;
            return Response.Success(new
            {
                message = $"{(maximize ? "Maximized" : "Restored")} window: {window.titleContent.text}"
            });
        }

        private object ShowNotification(JObject parameters)
        {
            string message = parameters["message"]?.ToString();
            float duration = parameters["duration"]?.ToObject<float>() ?? 3.0f;

            if (string.IsNullOrEmpty(message))
            {
                return Response.Error("message parameter is required");
            }

            var window = EditorWindow.focusedWindow ?? EditorWindow.GetWindow<SceneView>();
            window?.ShowNotification(new GUIContent(message), duration);

            return Response.Success(new
            {
                message = "Notification shown",
                content = message,
                duration = duration
            });
        }

        private object CreatePopup(JObject parameters)
        {
            string title = parameters["title"]?.ToString() ?? "Message";
            string message = parameters["message"]?.ToString();
            string ok = parameters["ok"]?.ToString() ?? "OK";
            string cancel = parameters["cancel"]?.ToString();

            if (string.IsNullOrEmpty(message))
            {
                return Response.Error("message parameter is required");
            }

            bool result;
            if (string.IsNullOrEmpty(cancel))
            {
                EditorUtility.DisplayDialog(title, message, ok);
                result = true;
            }
            else
            {
                result = EditorUtility.DisplayDialog(title, message, ok, cancel);
            }

            return Response.Success(new
            {
                dialogResult = result,
                title = title,
                message = message
            });
        }
    }
}