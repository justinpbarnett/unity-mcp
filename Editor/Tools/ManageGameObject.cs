using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEditor;
using UnityEditor.SceneManagement;
using Newtonsoft.Json.Linq;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEditorInternal;
using UnityMCP.Editor.Helpers; // For Response class

namespace UnityMCP.Editor.Tools
{
    /// <summary>
    /// Handles GameObject manipulation within the current scene (CRUD, find, components).
    /// </summary>
    public static class ManageGameObject
    {
        // --- Main Handler ---

        public static object HandleCommand(JObject @params)
        {
            string action = @params["action"]?.ToString().ToLower();
            if (string.IsNullOrEmpty(action))
            {
                return Response.Error("Action parameter is required.");
            }

            // Parameters used by various actions
            JToken targetToken = @params["target"]; // Can be string (name/path) or int (instanceID)
            string searchMethod = @params["searchMethod"]?.ToString().ToLower();
            
            // Get common parameters (consolidated)
            string name = @params["name"]?.ToString();
            string tag = @params["tag"]?.ToString();
            string layer = @params["layer"]?.ToString();
            JToken parentToken = @params["parent"];
            
            // --- Prefab Redirection Check ---
            string targetPath = targetToken?.Type == JTokenType.String ? targetToken.ToString() : null;
            if (!string.IsNullOrEmpty(targetPath) && targetPath.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
            {
                // Allow 'create' (instantiate), 'find' (?), 'get_components' (?)
                if (action == "modify" || action == "set_component_property")
                {
                    Debug.Log($"[ManageGameObject->ManageAsset] Redirecting action '{action}' for prefab '{targetPath}' to ManageAsset.");
                    // Prepare params for ManageAsset.ModifyAsset
                    JObject assetParams = new JObject();
                    assetParams["action"] = "modify"; // ManageAsset uses "modify"
                    assetParams["path"] = targetPath;

                    // Extract properties. 
                    // For 'set_component_property', combine componentName and componentProperties.
                    // For 'modify', directly use componentProperties.
                    JObject properties = null;
                    if (action == "set_component_property")
                    {
                         string compName = @params["componentName"]?.ToString();
                         JObject compProps = @params["componentProperties"]?[compName] as JObject; // Handle potential nesting
                         if (string.IsNullOrEmpty(compName)) return Response.Error("Missing 'componentName' for 'set_component_property' on prefab.");
                         if (compProps == null) return Response.Error($"Missing or invalid 'componentProperties' for component '{compName}' for 'set_component_property' on prefab.");
                         
                         properties = new JObject();
                         properties[compName] = compProps; 
                    } 
                    else // action == "modify"
                    {
                         properties = @params["componentProperties"] as JObject;
                         if (properties == null) return Response.Error("Missing 'componentProperties' for 'modify' action on prefab.");
                    }
                    
                    assetParams["properties"] = properties;
                    
                    // Call ManageAsset handler
                    return ManageAsset.HandleCommand(assetParams);
                }
                 else if (action == "delete" || action == "add_component" || action == "remove_component" || action == "get_components") // Added get_components here too
                {
                     // Explicitly block other modifications on the prefab asset itself via manage_gameobject
                     return Response.Error($"Action '{action}' on a prefab asset ('{targetPath}') should be performed using the 'manage_asset' command.");
                }
                 // Allow 'create' (instantiation) and 'find' to proceed, although finding a prefab asset by path might be less common via manage_gameobject.
                 // No specific handling needed here, the code below will run.
            }
            // --- End Prefab Redirection Check ---

            try
            {
                switch (action)
                {
                    case "create":
                        return CreateGameObject(@params);
                    case "modify":
                        return ModifyGameObject(@params, targetToken, searchMethod);
                    case "delete":
                        return DeleteGameObject(targetToken, searchMethod);
                    case "find":
                         return FindGameObjects(@params, targetToken, searchMethod);
                    case "get_components":
                        string getCompTarget = targetToken?.ToString(); // Expect name, path, or ID string
                        if (getCompTarget == null) return Response.Error("'target' parameter required for get_components.");
                        return GetComponentsFromTarget(getCompTarget, searchMethod);
                    case "add_component":
                         return AddComponentToTarget(@params, targetToken, searchMethod);
                     case "remove_component":
                         return RemoveComponentFromTarget(@params, targetToken, searchMethod);
                     case "set_component_property":
                         return SetComponentPropertyOnTarget(@params, targetToken, searchMethod);

                    default:
                        return Response.Error($"Unknown action: '{action}'.");
                }
            }
            catch (Exception e)
            {
                 Debug.LogError($"[ManageGameObject] Action '{action}' failed: {e}");
                 return Response.Error($"Internal error processing action '{action}': {e.Message}");
            }
        }

        // --- Action Implementations ---

        private static object CreateGameObject(JObject @params)
        {
            string name = @params["name"]?.ToString();
            if (string.IsNullOrEmpty(name))
            {
                return Response.Error("'name' parameter is required for 'create' action.");
            }

            // Get prefab creation parameters
            bool saveAsPrefab = @params["saveAsPrefab"]?.ToObject<bool>() ?? false;
            string prefabPath = @params["prefabPath"]?.ToString();
            string tag = @params["tag"]?.ToString(); // Get tag for creation
            string primitiveType = @params["primitiveType"]?.ToString(); // Keep primitiveType check
            GameObject newGo = null; // Initialize as null

            // --- Try Instantiating Prefab First ---
            string originalPrefabPath = prefabPath; // Keep original for messages
            if (!string.IsNullOrEmpty(prefabPath))
            {
                // If no extension, search for the prefab by name
                if (!prefabPath.Contains("/") && !prefabPath.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                {
                    string prefabNameOnly = prefabPath;
                    Debug.Log($"[ManageGameObject.Create] Searching for prefab named: '{prefabNameOnly}'");
                    string[] guids = AssetDatabase.FindAssets($"t:Prefab {prefabNameOnly}");
                    if (guids.Length == 0)
                    {
                        return Response.Error($"Prefab named '{prefabNameOnly}' not found anywhere in the project.");
                    }
                    else if (guids.Length > 1)
                    {
                        string foundPaths = string.Join(", ", guids.Select(g => AssetDatabase.GUIDToAssetPath(g)));
                        return Response.Error($"Multiple prefabs found matching name '{prefabNameOnly}': {foundPaths}. Please provide a more specific path.");
                    }
                    else // Exactly one found
                    {
                        prefabPath = AssetDatabase.GUIDToAssetPath(guids[0]); // Update prefabPath with the full path
                        Debug.Log($"[ManageGameObject.Create] Found unique prefab at path: '{prefabPath}'");
                    }
                }
                else if (!prefabPath.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                {
                    // If it looks like a path but doesn't end with .prefab, assume user forgot it and append it.
                    // We could also error here, but appending might be more user-friendly.
                    Debug.LogWarning($"[ManageGameObject.Create] Provided prefabPath '{prefabPath}' does not end with .prefab. Assuming it's missing and appending.");
                    prefabPath += ".prefab";
                    // Note: This path might still not exist, AssetDatabase.LoadAssetAtPath will handle that.
                }

                // Removed the early return error for missing .prefab ending.
                // The logic above now handles finding or assuming the .prefab extension.

                GameObject prefabAsset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (prefabAsset != null)
                {
                    try
                    {
                        // Instantiate the prefab, initially place it at the root
                        // Parent will be set later if specified
                        newGo = PrefabUtility.InstantiatePrefab(prefabAsset) as GameObject;

                        if (newGo == null)
                        {
                             // This might happen if the asset exists but isn't a valid GameObject prefab somehow
                             Debug.LogError($"[ManageGameObject.Create] Failed to instantiate prefab at '{prefabPath}', asset might be corrupted or not a GameObject.");
                             return Response.Error($"Failed to instantiate prefab at '{prefabPath}'.");
                        }
                        
                        // Name the instance based on the 'name' parameter, not the prefab's default name
                        if (!string.IsNullOrEmpty(name))
                        {
                            newGo.name = name;
                        }
                        
                        // Register Undo for prefab instantiation
                        Undo.RegisterCreatedObjectUndo(newGo, $"Instantiate Prefab '{prefabAsset.name}' as '{newGo.name}'");
                        Debug.Log($"[ManageGameObject.Create] Instantiated prefab '{prefabAsset.name}' from path '{prefabPath}' as '{newGo.name}'.");

                    }
                    catch (Exception e)
                    {
                        return Response.Error($"Error instantiating prefab '{prefabPath}': {e.Message}");
                    }
                }
                else
                {
                     // Only return error if prefabPath was specified but not found.
                     // If prefabPath was empty/null, we proceed to create primitive/empty.
                     Debug.LogWarning($"[ManageGameObject.Create] Prefab asset not found at path: '{prefabPath}'. Will proceed to create new object if specified.");
                     // Do not return error here, allow fallback to primitive/empty creation
                }
            }

            // --- Fallback: Create Primitive or Empty GameObject ---
            bool createdNewObject = false; // Flag to track if we created (not instantiated)
            if (newGo == null) // Only proceed if prefab instantiation didn't happen
            {
                if (!string.IsNullOrEmpty(primitiveType))
                {
                    try
                    {
                        PrimitiveType type = (PrimitiveType)Enum.Parse(typeof(PrimitiveType), primitiveType, true);
                        newGo = GameObject.CreatePrimitive(type);
                        // Set name *after* creation for primitives
                        if (!string.IsNullOrEmpty(name)) newGo.name = name;
                        else return Response.Error("'name' parameter is required when creating a primitive."); // Name is essential
                        createdNewObject = true;
                    }
                    catch (ArgumentException)
                    {
                        return Response.Error($"Invalid primitive type: '{primitiveType}'. Valid types: {string.Join(", ", Enum.GetNames(typeof(PrimitiveType)))}");
                    }
                     catch (Exception e)
                     {
                         return Response.Error($"Failed to create primitive '{primitiveType}': {e.Message}");
                     }
                }
                else // Create empty GameObject
                {
                     if (string.IsNullOrEmpty(name))
                     {
                        return Response.Error("'name' parameter is required for 'create' action when not instantiating a prefab or creating a primitive.");
                     }
                    newGo = new GameObject(name);
                    createdNewObject = true;
                }
                
                // Record creation for Undo *only* if we created a new object
                if (createdNewObject)
                {
                    Undo.RegisterCreatedObjectUndo(newGo, $"Create GameObject '{newGo.name}'");
                }
            }

            // --- Common Setup (Parent, Transform, Tag, Components) - Applied AFTER object exists ---
            if (newGo == null)
            {
                 // Should theoretically not happen if logic above is correct, but safety check.
                 return Response.Error("Failed to create or instantiate the GameObject.");
            }
            
            // Record potential changes to the existing prefab instance or the new GO
            // Record transform separately in case parent changes affect it
            Undo.RecordObject(newGo.transform, "Set GameObject Transform");
            Undo.RecordObject(newGo, "Set GameObject Properties");

            // Set Parent
            JToken parentToken = @params["parent"];
            if (parentToken != null)
            {
                GameObject parentGo = FindObjectInternal(parentToken, "by_id_or_name_or_path"); // Flexible parent finding
                if (parentGo == null)
                {
                    UnityEngine.Object.DestroyImmediate(newGo); // Clean up created object
                    return Response.Error($"Parent specified ('{parentToken}') but not found.");
                }
                newGo.transform.SetParent(parentGo.transform, true); // worldPositionStays = true
            }

            // Set Transform
            Vector3? position = ParseVector3(@params["position"] as JArray);
            Vector3? rotation = ParseVector3(@params["rotation"] as JArray);
            Vector3? scale = ParseVector3(@params["scale"] as JArray);

            if (position.HasValue) newGo.transform.localPosition = position.Value;
            if (rotation.HasValue) newGo.transform.localEulerAngles = rotation.Value;
            if (scale.HasValue) newGo.transform.localScale = scale.Value;

            // Set Tag (added for create action)
            if (!string.IsNullOrEmpty(tag))
            {
                 // Similar logic as in ModifyGameObject for setting/creating tags
                string tagToSet = string.IsNullOrEmpty(tag) ? "Untagged" : tag;
                try {
                    newGo.tag = tagToSet;
                } catch (UnityException ex) {
                    if (ex.Message.Contains("is not defined")) {
                         Debug.LogWarning($"[ManageGameObject.Create] Tag '{tagToSet}' not found. Attempting to create it.");
                         try {
                            InternalEditorUtility.AddTag(tagToSet);
                            newGo.tag = tagToSet; // Retry
                            Debug.Log($"[ManageGameObject.Create] Tag '{tagToSet}' created and assigned successfully.");
                         } catch (Exception innerEx) {
                             UnityEngine.Object.DestroyImmediate(newGo); // Clean up
                             return Response.Error($"Failed to create or assign tag '{tagToSet}' during creation: {innerEx.Message}.");
                         }
                    } else {
                         UnityEngine.Object.DestroyImmediate(newGo); // Clean up
                         return Response.Error($"Failed to set tag to '{tagToSet}' during creation: {ex.Message}.");
                    }
                }
            }
            
            // Set Layer (new for create action)
            string layerName = @params["layer"]?.ToString();
            if (!string.IsNullOrEmpty(layerName))
            {
                int layerId = LayerMask.NameToLayer(layerName);
                if (layerId != -1)
                {
                    newGo.layer = layerId;
                }
                else
                {
                    Debug.LogWarning($"[ManageGameObject.Create] Layer '{layerName}' not found. Using default layer.");
                }
            }

            // Add Components
             if (@params["componentsToAdd"] is JArray componentsToAddArray)
             {
                 foreach (var compToken in componentsToAddArray)
                 {
                     string typeName = null;
                     JObject properties = null;

                     if (compToken.Type == JTokenType.String)
                     {
                         typeName = compToken.ToString();
                     }
                     else if (compToken is JObject compObj)
                     {
                         typeName = compObj["typeName"]?.ToString();
                         properties = compObj["properties"] as JObject;
                     }

                     if (!string.IsNullOrEmpty(typeName))
                     {
                         var addResult = AddComponentInternal(newGo, typeName, properties);
                         if (addResult != null) // Check if AddComponentInternal returned an error object
                         {
                             UnityEngine.Object.DestroyImmediate(newGo); // Clean up
                             return addResult; // Return the error response
                         }
                     }
                     else
                     {
                          Debug.LogWarning($"[ManageGameObject] Invalid component format in componentsToAdd: {compToken}");
                     }
                 }
             }

            // Save as Prefab ONLY if we *created* a new object AND saveAsPrefab is true
            GameObject finalInstance = newGo; // Use this for selection and return data
            if (createdNewObject && saveAsPrefab)
            {
                string finalPrefabPath = prefabPath; // Use a separate variable for saving path
                // This check should now happen *before* attempting to save
                 if (string.IsNullOrEmpty(finalPrefabPath))
                 {
                     // Clean up the created object before returning error
                     UnityEngine.Object.DestroyImmediate(newGo);
                     return Response.Error("'prefabPath' is required when 'saveAsPrefab' is true and creating a new object.");
                 }
                 // Ensure the *saving* path ends with .prefab
                 if (!finalPrefabPath.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                 {
                     Debug.Log($"[ManageGameObject.Create] Appending .prefab extension to save path: '{finalPrefabPath}' -> '{finalPrefabPath}.prefab'");
                     finalPrefabPath += ".prefab";
                 }
                 
                 // Removed the error check here as we now ensure the extension exists
                 // if (!prefabPath.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                 // {
                 //     UnityEngine.Object.DestroyImmediate(newGo);
                 //     return Response.Error($"'prefabPath' must end with '.prefab'. Provided: '{prefabPath}'");
                 // }
            
                try
                {
                    // Ensure directory exists using the final saving path
                    string directoryPath = System.IO.Path.GetDirectoryName(finalPrefabPath);
                    if (!string.IsNullOrEmpty(directoryPath) && !System.IO.Directory.Exists(directoryPath))
                    {
                        System.IO.Directory.CreateDirectory(directoryPath);
                         AssetDatabase.Refresh(); // Refresh asset database to recognize the new folder
                         Debug.Log($"[ManageGameObject.Create] Created directory for prefab: {directoryPath}");
                    }

                    // Use SaveAsPrefabAssetAndConnect with the final saving path
                    finalInstance = PrefabUtility.SaveAsPrefabAssetAndConnect(newGo, finalPrefabPath, InteractionMode.UserAction);
                    
                    if (finalInstance == null)
                    {
                         // Destroy the original if saving failed somehow (shouldn't usually happen if path is valid)
                         UnityEngine.Object.DestroyImmediate(newGo);
                         return Response.Error($"Failed to save GameObject '{name}' as prefab at '{finalPrefabPath}'. Check path and permissions.");
                    }
                    Debug.Log($"[ManageGameObject.Create] GameObject '{name}' saved as prefab to '{finalPrefabPath}' and instance connected.");
                    // Mark the new prefab asset as dirty? Not usually necessary, SaveAsPrefabAsset handles it.
                    // EditorUtility.SetDirty(finalInstance); // Instance is handled by SaveAsPrefabAssetAndConnect
                }
                catch (Exception e)
                {
                    // Clean up the instance if prefab saving fails
                    UnityEngine.Object.DestroyImmediate(newGo); // Destroy the original attempt
                    return Response.Error($"Error saving prefab '{finalPrefabPath}': {e.Message}");
                }
            }

            // Select the instance in the scene (either prefab instance or newly created/saved one)
            Selection.activeGameObject = finalInstance;
            
            // Determine appropriate success message using the potentially updated or original path
            string messagePrefabPath = finalInstance == null ? originalPrefabPath : AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(finalInstance) ?? (UnityEngine.Object)finalInstance);
            string successMessage;
            if (!createdNewObject && !string.IsNullOrEmpty(messagePrefabPath)) // Instantiated existing prefab
            {
                 successMessage = $"Prefab '{messagePrefabPath}' instantiated successfully as '{finalInstance.name}'.";
            }
            else if (createdNewObject && saveAsPrefab && !string.IsNullOrEmpty(messagePrefabPath)) // Created new and saved as prefab
            {
                 successMessage = $"GameObject '{finalInstance.name}' created and saved as prefab to '{messagePrefabPath}'.";
            }
            else // Created new primitive or empty GO, didn't save as prefab
            {
                 successMessage = $"GameObject '{finalInstance.name}' created successfully in scene.";
            }
                
            // Return data for the instance in the scene
            return Response.Success(successMessage, GetGameObjectData(finalInstance)); 
        }

        private static object ModifyGameObject(JObject @params, JToken targetToken, string searchMethod)
        {
            GameObject targetGo = FindObjectInternal(targetToken, searchMethod);
            if (targetGo == null)
            {
                return Response.Error($"Target GameObject ('{targetToken}') not found using method '{searchMethod ?? "default"}'.");
            }
            
            // Record state for Undo *before* modifications
            Undo.RecordObject(targetGo.transform, "Modify GameObject Transform");
            Undo.RecordObject(targetGo, "Modify GameObject Properties"); 

            bool modified = false;

            // Rename (using consolidated 'name' parameter)
            string name = @params["name"]?.ToString();
            if (!string.IsNullOrEmpty(name) && targetGo.name != name)
            {
                targetGo.name = name;
                modified = true;
            }

            // Change Parent (using consolidated 'parent' parameter)
            JToken parentToken = @params["parent"];
            if (parentToken != null)
            {
                 GameObject newParentGo = FindObjectInternal(parentToken, "by_id_or_name_or_path");
                 if (newParentGo == null && !(parentToken.Type == JTokenType.Null || (parentToken.Type == JTokenType.String && string.IsNullOrEmpty(parentToken.ToString()))))
                 {
                      return Response.Error($"New parent ('{parentToken}') not found.");
                 } 
                 // Check for hierarchy loops
                 if (newParentGo != null && newParentGo.transform.IsChildOf(targetGo.transform))
                 {
                     return Response.Error($"Cannot parent '{targetGo.name}' to '{newParentGo.name}', as it would create a hierarchy loop.");
                 }
                 if (targetGo.transform.parent != (newParentGo?.transform)) 
                 {
                    targetGo.transform.SetParent(newParentGo?.transform, true); // worldPositionStays = true
                    modified = true;
                 }
            }

            // Set Active State
            bool? setActive = @params["setActive"]?.ToObject<bool?>();
            if (setActive.HasValue && targetGo.activeSelf != setActive.Value)
            {
                targetGo.SetActive(setActive.Value);
                 modified = true;
            }

            // Change Tag (using consolidated 'tag' parameter)
            string tag = @params["tag"]?.ToString();
            // Only attempt to change tag if a non-null tag is provided and it's different from the current one.
            // Allow setting an empty string to remove the tag (Unity uses "Untagged").
            if (tag != null && targetGo.tag != tag)
            {
                // Ensure the tag is not empty, if empty, it means "Untagged" implicitly
                string tagToSet = string.IsNullOrEmpty(tag) ? "Untagged" : tag;

                try {
                    // First attempt to set the tag
                    targetGo.tag = tagToSet; 
                    modified = true;
                }
                catch (UnityException ex) 
                {
                     // Check if the error is specifically because the tag doesn't exist
                     if (ex.Message.Contains("is not defined")) 
                     {
                         Debug.LogWarning($"[ManageGameObject] Tag '{tagToSet}' not found. Attempting to create it.");
                         try 
                         {
                            // Attempt to create the tag using internal utility
                            InternalEditorUtility.AddTag(tagToSet);
                            // Wait a frame maybe? Not strictly necessary but sometimes helps editor updates.
                            // yield return null; // Cannot yield here, editor script limitation

                            // Retry setting the tag immediately after creation
                            targetGo.tag = tagToSet; 
                            modified = true; // Mark as modified on successful retry
                            Debug.Log($"[ManageGameObject] Tag '{tagToSet}' created and assigned successfully.");
                         } 
                         catch (Exception innerEx)
                         {
                             // Handle failure during tag creation or the second assignment attempt
                             Debug.LogError($"[ManageGameObject] Failed to create or assign tag '{tagToSet}' after attempting creation: {innerEx.Message}");
                             return Response.Error($"Failed to create or assign tag '{tagToSet}': {innerEx.Message}. Check Tag Manager and permissions.");
                         }
                     } 
                     else 
                     {
                         // If the exception was for a different reason, return the original error
                         return Response.Error($"Failed to set tag to '{tagToSet}': {ex.Message}.");
                     }
                }
            }

            // Change Layer (using consolidated 'layer' parameter)
            string layerName = @params["layer"]?.ToString();
            if (!string.IsNullOrEmpty(layerName))
            {
                int layerId = LayerMask.NameToLayer(layerName);
                if (layerId == -1 && layerName != "Default")
                {
                    return Response.Error($"Invalid layer specified: '{layerName}'. Use a valid layer name.");
                }
                if (layerId != -1 && targetGo.layer != layerId)
                {
                    targetGo.layer = layerId;
                    modified = true;
                }
            }

            // Transform Modifications
            Vector3? position = ParseVector3(@params["position"] as JArray);
            Vector3? rotation = ParseVector3(@params["rotation"] as JArray);
            Vector3? scale = ParseVector3(@params["scale"] as JArray);

            if (position.HasValue && targetGo.transform.localPosition != position.Value) 
            { 
                targetGo.transform.localPosition = position.Value; 
                modified = true;
            }
            if (rotation.HasValue && targetGo.transform.localEulerAngles != rotation.Value) 
            { 
                targetGo.transform.localEulerAngles = rotation.Value; 
                modified = true;
            }
            if (scale.HasValue && targetGo.transform.localScale != scale.Value) 
            { 
                targetGo.transform.localScale = scale.Value; 
                modified = true;
            }

            // --- Component Modifications --- 
            // Note: These might need more specific Undo recording per component

            // Remove Components
            if (@params["componentsToRemove"] is JArray componentsToRemoveArray)
            {
                foreach (var compToken in componentsToRemoveArray)
                {
                    string typeName = compToken.ToString();
                    if (!string.IsNullOrEmpty(typeName))
                    {
                        var removeResult = RemoveComponentInternal(targetGo, typeName);
                        if (removeResult != null) return removeResult; // Return error if removal failed
                         modified = true;
                    }
                }
            }

            // Add Components (similar to create)
             if (@params["componentsToAdd"] is JArray componentsToAddArrayModify)
             {
                 foreach (var compToken in componentsToAddArrayModify)
                 {
                     // ... (parsing logic as in CreateGameObject) ...
                     string typeName = null;
                     JObject properties = null;
                     if (compToken.Type == JTokenType.String) typeName = compToken.ToString();
                     else if (compToken is JObject compObj) { typeName = compObj["typeName"]?.ToString(); properties = compObj["properties"] as JObject; }

                     if (!string.IsNullOrEmpty(typeName))
                     {
                         var addResult = AddComponentInternal(targetGo, typeName, properties);
                         if (addResult != null) return addResult;
                         modified = true;
                     }
                 }
             }

            // Set Component Properties
             if (@params["componentProperties"] is JObject componentPropertiesObj)
             { 
                 foreach (var prop in componentPropertiesObj.Properties())
                 {
                     string compName = prop.Name;
                     JObject propertiesToSet = prop.Value as JObject;
                     if (propertiesToSet != null)
                     {
                         var setResult = SetComponentPropertiesInternal(targetGo, compName, propertiesToSet);
                         if (setResult != null) return setResult;
                         modified = true;
                     }
                 }
             }
             
            if (!modified)
            {
                return Response.Success($"No modifications applied to GameObject '{targetGo.name}'.", GetGameObjectData(targetGo));
            }

            EditorUtility.SetDirty(targetGo); // Mark scene as dirty
            return Response.Success($"GameObject '{targetGo.name}' modified successfully.", GetGameObjectData(targetGo));
        }

        private static object DeleteGameObject(JToken targetToken, string searchMethod)
        {
            // Find potentially multiple objects if name/tag search is used without find_all=false implicitly
            List<GameObject> targets = FindObjectsInternal(targetToken, searchMethod, true); // find_all=true for delete safety
            
            if (targets.Count == 0)
            {
                return Response.Error($"Target GameObject(s) ('{targetToken}') not found using method '{searchMethod ?? "default"}'.");
            }

            List<object> deletedObjects = new List<object>();
            foreach(var targetGo in targets)
            {
                 if (targetGo != null) 
                 {
                     string goName = targetGo.name;
                     int goId = targetGo.GetInstanceID();
                     // Use Undo.DestroyObjectImmediate for undo support
                     Undo.DestroyObjectImmediate(targetGo);
                     deletedObjects.Add(new { name = goName, instanceID = goId });
                 }
            }
            
            if (deletedObjects.Count > 0)
            {
                string message = targets.Count == 1
                    ? $"GameObject '{deletedObjects[0].GetType().GetProperty("name").GetValue(deletedObjects[0])}' deleted successfully."
                    : $"{deletedObjects.Count} GameObjects deleted successfully.";
                 return Response.Success(message, deletedObjects);
            }
            else
            {
                 // Should not happen if targets.Count > 0 initially, but defensive check
                 return Response.Error("Failed to delete target GameObject(s).");
            }
        }

        private static object FindGameObjects(JObject @params, JToken targetToken, string searchMethod)
        {
             bool findAll = @params["findAll"]?.ToObject<bool>() ?? false;
             List<GameObject> foundObjects = FindObjectsInternal(targetToken, searchMethod, findAll, @params);

             if (foundObjects.Count == 0)
             {
                  return Response.Success("No matching GameObjects found.", new List<object>());
             }

             var results = foundObjects.Select(go => GetGameObjectData(go)).ToList();
             return Response.Success($"Found {results.Count} GameObject(s).", results);
        }

        private static object GetComponentsFromTarget(string target, string searchMethod)
        {
            GameObject targetGo = FindObjectInternal(target, searchMethod);
             if (targetGo == null)
             {
                 return Response.Error($"Target GameObject ('{target}') not found using method '{searchMethod ?? "default"}'.");
             }

             try
             {
                 Component[] components = targetGo.GetComponents<Component>();
                 var componentData = components.Select(c => GetComponentData(c)).ToList();
                 return Response.Success($"Retrieved {componentData.Count} components from '{targetGo.name}'.", componentData);
             }
             catch (Exception e)
             {   
                 return Response.Error($"Error getting components from '{targetGo.name}': {e.Message}");
             }
        }
        
        private static object AddComponentToTarget(JObject @params, JToken targetToken, string searchMethod)
        {
             GameObject targetGo = FindObjectInternal(targetToken, searchMethod);
             if (targetGo == null) {
                 return Response.Error($"Target GameObject ('{targetToken}') not found using method '{searchMethod ?? "default"}'.");
             }

             string typeName = null;
             JObject properties = null;

             // Allow adding component specified directly or via componentsToAdd array (take first)
             if (@params["componentName"] != null) 
             {
                 typeName = @params["componentName"]?.ToString();
                 properties = @params["componentProperties"]?[typeName] as JObject; // Check if props are nested under name
             }
             else if (@params["componentsToAdd"] is JArray componentsToAddArray && componentsToAddArray.Count > 0)
             {
                 var compToken = componentsToAddArray.First;
                 if (compToken.Type == JTokenType.String) typeName = compToken.ToString();
                 else if (compToken is JObject compObj) { typeName = compObj["typeName"]?.ToString(); properties = compObj["properties"] as JObject; }
             }
             
             if (string.IsNullOrEmpty(typeName))
             {
                 return Response.Error("Component type name ('componentName' or first element in 'componentsToAdd') is required.");
             }
             
             var addResult = AddComponentInternal(targetGo, typeName, properties);
             if (addResult != null) return addResult; // Return error

             EditorUtility.SetDirty(targetGo);
             return Response.Success($"Component '{typeName}' added to '{targetGo.name}'.", GetGameObjectData(targetGo)); // Return updated GO data
        }

         private static object RemoveComponentFromTarget(JObject @params, JToken targetToken, string searchMethod)
         {
             GameObject targetGo = FindObjectInternal(targetToken, searchMethod);
             if (targetGo == null) {
                 return Response.Error($"Target GameObject ('{targetToken}') not found using method '{searchMethod ?? "default"}'.");
             }

             string typeName = null;
             // Allow removing component specified directly or via componentsToRemove array (take first)
             if (@params["componentName"] != null)
             {
                  typeName = @params["componentName"]?.ToString();
             }
             else if (@params["componentsToRemove"] is JArray componentsToRemoveArray && componentsToRemoveArray.Count > 0)
             {
                 typeName = componentsToRemoveArray.First?.ToString();
             }
             
             if (string.IsNullOrEmpty(typeName))
             {
                 return Response.Error("Component type name ('componentName' or first element in 'componentsToRemove') is required.");
             }

             var removeResult = RemoveComponentInternal(targetGo, typeName);
             if (removeResult != null) return removeResult; // Return error
             
             EditorUtility.SetDirty(targetGo);
             return Response.Success($"Component '{typeName}' removed from '{targetGo.name}'.", GetGameObjectData(targetGo));
         }

        private static object SetComponentPropertyOnTarget(JObject @params, JToken targetToken, string searchMethod)
        {
             GameObject targetGo = FindObjectInternal(targetToken, searchMethod);
             if (targetGo == null) {
                 return Response.Error($"Target GameObject ('{targetToken}') not found using method '{searchMethod ?? "default"}'.");
             }

             string compName = @params["componentName"]?.ToString();
             JObject propertiesToSet = null;

             if (!string.IsNullOrEmpty(compName))
             {
                 // Properties might be directly under componentProperties or nested under the component name
                 if (@params["componentProperties"] is JObject compProps) {
                     propertiesToSet = compProps[compName] as JObject ?? compProps; // Allow flat or nested structure
                 }
             }
             else {
                 return Response.Error("'componentName' parameter is required.");
             }
             
             if (propertiesToSet == null || !propertiesToSet.HasValues)
             {
                 return Response.Error("'componentProperties' dictionary for the specified component is required and cannot be empty.");
             }

             var setResult = SetComponentPropertiesInternal(targetGo, compName, propertiesToSet);
             if (setResult != null) return setResult; // Return error

             EditorUtility.SetDirty(targetGo); 
             return Response.Success($"Properties set for component '{compName}' on '{targetGo.name}'.", GetGameObjectData(targetGo));
        }


        // --- Internal Helpers ---
        
        /// <summary>
        /// Finds a single GameObject based on token (ID, name, path) and search method.
        /// </summary>
        private static GameObject FindObjectInternal(JToken targetToken, string searchMethod, JObject findParams = null)
        {
            // If find_all is not explicitly false, we still want only one for most single-target operations.
            bool findAll = findParams?["findAll"]?.ToObject<bool>() ?? false;
             // If a specific target ID is given, always find just that one.
            if (targetToken?.Type == JTokenType.Integer || (searchMethod == "by_id" && int.TryParse(targetToken?.ToString(), out _)))
            {
                 findAll = false;
            }
            List<GameObject> results = FindObjectsInternal(targetToken, searchMethod, findAll, findParams);
            return results.Count > 0 ? results[0] : null;
        }
        
        /// <summary>
        /// Core logic for finding GameObjects based on various criteria.
        /// </summary>
        private static List<GameObject> FindObjectsInternal(JToken targetToken, string searchMethod, bool findAll, JObject findParams = null)
        {
            List<GameObject> results = new List<GameObject>();
            string searchTerm = findParams?["searchTerm"]?.ToString() ?? targetToken?.ToString(); // Use searchTerm if provided, else the target itself
            bool searchInChildren = findParams?["searchInChildren"]?.ToObject<bool>() ?? false;
            bool searchInactive = findParams?["searchInactive"]?.ToObject<bool>() ?? false;
            
            // Default search method if not specified
            if (string.IsNullOrEmpty(searchMethod))
            {
                 if (targetToken?.Type == JTokenType.Integer) searchMethod = "by_id";
                 else if (!string.IsNullOrEmpty(searchTerm) && searchTerm.Contains('/')) searchMethod = "by_path";
                 else searchMethod = "by_name"; // Default fallback
            }

            GameObject rootSearchObject = null;
             // If searching in children, find the initial target first
             if (searchInChildren && targetToken != null)
             {
                  rootSearchObject = FindObjectInternal(targetToken, "by_id_or_name_or_path"); // Find the root for child search
                  if (rootSearchObject == null)
                  {
                      Debug.LogWarning($"[ManageGameObject.Find] Root object '{targetToken}' for child search not found.");
                      return results; // Return empty if root not found
                  }
             }

            switch (searchMethod)
            {
                case "by_id":
                    if (int.TryParse(searchTerm, out int instanceId))
                    {
                        // EditorUtility.InstanceIDToObject is slow, iterate manually if possible
                        // GameObject obj = EditorUtility.InstanceIDToObject(instanceId) as GameObject;
                        var allObjects = GetAllSceneObjects(searchInactive); // More efficient
                        GameObject obj = allObjects.FirstOrDefault(go => go.GetInstanceID() == instanceId);
                        if (obj != null) results.Add(obj);
                    }
                    break;
                case "by_name":
                    var searchPoolName = rootSearchObject ? rootSearchObject.GetComponentsInChildren<Transform>(searchInactive).Select(t => t.gameObject) :
                                                          GetAllSceneObjects(searchInactive);
                    results.AddRange(searchPoolName.Where(go => go.name == searchTerm));
                    break;
                case "by_path":
                    // Path is relative to scene root or rootSearchObject
                    Transform foundTransform = rootSearchObject ? rootSearchObject.transform.Find(searchTerm) : GameObject.Find(searchTerm)?.transform;
                    if(foundTransform != null) results.Add(foundTransform.gameObject);
                    break;
                case "by_tag":
                     var searchPoolTag = rootSearchObject ? rootSearchObject.GetComponentsInChildren<Transform>(searchInactive).Select(t => t.gameObject) :
                                                          GetAllSceneObjects(searchInactive);
                    results.AddRange(searchPoolTag.Where(go => go.CompareTag(searchTerm)));
                    break;
                case "by_layer":
                     var searchPoolLayer = rootSearchObject ? rootSearchObject.GetComponentsInChildren<Transform>(searchInactive).Select(t => t.gameObject) :
                                                           GetAllSceneObjects(searchInactive);
                    if (int.TryParse(searchTerm, out int layerIndex))
                    {
                         results.AddRange(searchPoolLayer.Where(go => go.layer == layerIndex));
                    }
                    else
                    {
                        int namedLayer = LayerMask.NameToLayer(searchTerm);
                        if(namedLayer != -1) results.AddRange(searchPoolLayer.Where(go => go.layer == namedLayer));
                    }
                    break;
                case "by_component":
                    Type componentType = FindType(searchTerm);
                    if (componentType != null)
                    {
                         // Determine FindObjectsInactive based on the searchInactive flag
                         FindObjectsInactive findInactive = searchInactive ? FindObjectsInactive.Include : FindObjectsInactive.Exclude;
                         // Replace FindObjectsOfType with FindObjectsByType, specifying the sorting mode and inactive state
                         var searchPoolComp = rootSearchObject 
                             ? rootSearchObject.GetComponentsInChildren(componentType, searchInactive).Select(c => (c as Component).gameObject) 
                             : UnityEngine.Object.FindObjectsByType(componentType, findInactive, FindObjectsSortMode.None).Select(c => (c as Component).gameObject);
                         results.AddRange(searchPoolComp.Where(go => go != null)); // Ensure GO is valid
                    }
                    else { Debug.LogWarning($"[ManageGameObject.Find] Component type not found: {searchTerm}"); }
                    break;
                case "by_id_or_name_or_path": // Helper method used internally
                     if (int.TryParse(searchTerm, out int id)) {
                          var allObjectsId = GetAllSceneObjects(true); // Search inactive for internal lookup
                          GameObject objById = allObjectsId.FirstOrDefault(go => go.GetInstanceID() == id);
                          if (objById != null) { results.Add(objById); break; }
                     }
                     GameObject objByPath = GameObject.Find(searchTerm);
                     if (objByPath != null) { results.Add(objByPath); break; }
                     
                     var allObjectsName = GetAllSceneObjects(true); 
                     results.AddRange(allObjectsName.Where(go => go.name == searchTerm));
                    break;
                default:
                    Debug.LogWarning($"[ManageGameObject.Find] Unknown search method: {searchMethod}");
                    break;
            }
            
             // If only one result is needed, return just the first one found.
             if (!findAll && results.Count > 1)
             {
                 return new List<GameObject> { results[0] };
             }

            return results.Distinct().ToList(); // Ensure uniqueness
        }
        
        // Helper to get all scene objects efficiently
        private static IEnumerable<GameObject> GetAllSceneObjects(bool includeInactive)
        {
            // SceneManager.GetActiveScene().GetRootGameObjects() is faster than FindObjectsOfType<GameObject>()
            var rootObjects = SceneManager.GetActiveScene().GetRootGameObjects();
            var allObjects = new List<GameObject>();
            foreach(var root in rootObjects)
            {
                 allObjects.AddRange(root.GetComponentsInChildren<Transform>(includeInactive).Select(t=>t.gameObject));
            }
            return allObjects;
        }

        /// <summary>
        /// Adds a component by type name and optionally sets properties.
        /// Returns null on success, or an error response object on failure.
        /// </summary>
        private static object AddComponentInternal(GameObject targetGo, string typeName, JObject properties)
        {
            Type componentType = FindType(typeName);
            if (componentType == null)
            {
                return Response.Error($"Component type '{typeName}' not found or is not a valid Component.");
            }
            if (!typeof(Component).IsAssignableFrom(componentType))
            {
                 return Response.Error($"Type '{typeName}' is not a Component.");
            }

            // Prevent adding Transform again
            if (componentType == typeof(Transform))
            {
                return Response.Error("Cannot add another Transform component.");
            }

            // Check for 2D/3D physics component conflicts
            bool isAdding2DPhysics = typeof(Rigidbody2D).IsAssignableFrom(componentType) || typeof(Collider2D).IsAssignableFrom(componentType);
            bool isAdding3DPhysics = typeof(Rigidbody).IsAssignableFrom(componentType) || typeof(Collider).IsAssignableFrom(componentType);

            if (isAdding2DPhysics)
            {
                // Check if the GameObject already has any 3D Rigidbody or Collider
                if (targetGo.GetComponent<Rigidbody>() != null || targetGo.GetComponent<Collider>() != null)
                {
                    return Response.Error($"Cannot add 2D physics component '{typeName}' because the GameObject '{targetGo.name}' already has a 3D Rigidbody or Collider.");
                }
            }
            else if (isAdding3DPhysics)
            {
                 // Check if the GameObject already has any 2D Rigidbody or Collider
                 if (targetGo.GetComponent<Rigidbody2D>() != null || targetGo.GetComponent<Collider2D>() != null)
                 {
                    return Response.Error($"Cannot add 3D physics component '{typeName}' because the GameObject '{targetGo.name}' already has a 2D Rigidbody or Collider.");
                 }
            }
            
            // Check if component already exists (optional, depending on desired behavior)
             // if (targetGo.GetComponent(componentType) != null) {
             //     return Response.Error($"Component '{typeName}' already exists on '{targetGo.name}'.");
             // }

            try
            {
                // Use Undo.AddComponent for undo support
                Component newComponent = Undo.AddComponent(targetGo, componentType);
                if (newComponent == null)
                {
                    return Response.Error($"Failed to add component '{typeName}' to '{targetGo.name}'. It might be disallowed (e.g., adding script twice).");
                }
                
                // Set default values for specific component types
                if (newComponent is Light light)
                {
                    // Default newly added lights to directional
                    light.type = LightType.Directional;
                }
                
                // Set properties if provided
                 if (properties != null)
                 {
                     var setResult = SetComponentPropertiesInternal(targetGo, typeName, properties, newComponent); // Pass the new component instance
                     if (setResult != null) {
                         // If setting properties failed, maybe remove the added component?
                         Undo.DestroyObjectImmediate(newComponent);
                         return setResult; // Return the error from setting properties
                     }
                 }

                 return null; // Success
            }
            catch (Exception e)
            {
                 return Response.Error($"Error adding component '{typeName}' to '{targetGo.name}': {e.Message}");
            }
        }

        /// <summary>
        /// Removes a component by type name.
        /// Returns null on success, or an error response object on failure.
        /// </summary>
        private static object RemoveComponentInternal(GameObject targetGo, string typeName)
        {
             Type componentType = FindType(typeName);
             if (componentType == null)
             {
                 return Response.Error($"Component type '{typeName}' not found for removal.");
             }

            // Prevent removing essential components
            if (componentType == typeof(Transform))
            {
                return Response.Error("Cannot remove the Transform component.");
            }

             Component componentToRemove = targetGo.GetComponent(componentType);
             if (componentToRemove == null)
             {
                  return Response.Error($"Component '{typeName}' not found on '{targetGo.name}' to remove.");
             }

             try
             {
                  // Use Undo.DestroyObjectImmediate for undo support
                  Undo.DestroyObjectImmediate(componentToRemove);
                  return null; // Success
             }
             catch (Exception e)
             {
                  return Response.Error($"Error removing component '{typeName}' from '{targetGo.name}': {e.Message}");
             }
        }
        
         /// <summary>
        /// Sets properties on a component.
        /// Returns null on success, or an error response object on failure.
        /// </summary>
        private static object SetComponentPropertiesInternal(GameObject targetGo, string compName, JObject propertiesToSet, Component targetComponentInstance = null)
        {
            Component targetComponent = targetComponentInstance ?? targetGo.GetComponent(compName);
            if (targetComponent == null)
            {
                return Response.Error($"Component '{compName}' not found on '{targetGo.name}' to set properties.");
            }

            Undo.RecordObject(targetComponent, "Set Component Properties");

            foreach (var prop in propertiesToSet.Properties())
            {
                string propName = prop.Name;
                JToken propValue = prop.Value;
                
                try
                {
                    if (!SetProperty(targetComponent, propName, propValue))
                    {
                         // Log warning if property could not be set
                         Debug.LogWarning($"[ManageGameObject] Could not set property '{propName}' on component '{compName}' ('{targetComponent.GetType().Name}'). Property might not exist, be read-only, or type mismatch.");
                         // Optionally return an error here instead of just logging
                         // return Response.Error($"Could not set property '{propName}' on component '{compName}'.");
                    }
                }
                catch (Exception e)
                {
                    Debug.LogError($"[ManageGameObject] Error setting property '{propName}' on '{compName}': {e.Message}");
                     // Optionally return an error here
                     // return Response.Error($"Error setting property '{propName}' on '{compName}': {e.Message}");
                }
            }
            EditorUtility.SetDirty(targetComponent);
            return null; // Success (or partial success if warnings were logged)
        }

        /// <summary>
        /// Helper to set a property or field via reflection, handling basic types.
        /// </summary>
        private static bool SetProperty(object target, string memberName, JToken value)
        {
            Type type = target.GetType();
            BindingFlags flags = BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase;

            try
            {
                // Handle special case for materials with dot notation (material.property)
                // Examples: material.color, sharedMaterial.color, materials[0].color
                if (memberName.Contains('.') || memberName.Contains('['))
                {
                    return SetNestedProperty(target, memberName, value);
                }

                PropertyInfo propInfo = type.GetProperty(memberName, flags);
                if (propInfo != null && propInfo.CanWrite)
                {
                    object convertedValue = ConvertJTokenToType(value, propInfo.PropertyType);
                    if (convertedValue != null)
                    {
                        propInfo.SetValue(target, convertedValue);
                        return true;
                    }
                }
                else
                {
                    FieldInfo fieldInfo = type.GetField(memberName, flags);
                    if (fieldInfo != null)
                    { 
                        object convertedValue = ConvertJTokenToType(value, fieldInfo.FieldType);
                        if (convertedValue != null) {
                            fieldInfo.SetValue(target, convertedValue);
                            return true;
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                 Debug.LogError($"[SetProperty] Failed to set '{memberName}' on {type.Name}: {ex.Message}");
            }
            return false;
        }

        /// <summary>
        /// Sets a nested property using dot notation (e.g., "material.color") or array access (e.g., "materials[0]")
        /// </summary>
        private static bool SetNestedProperty(object target, string path, JToken value)
        {
            try
            {
                // Split the path into parts (handling both dot notation and array indexing)
                string[] pathParts = SplitPropertyPath(path);
                if (pathParts.Length == 0) return false;

                object currentObject = target;
                Type currentType = currentObject.GetType();
                BindingFlags flags = BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase;

                // Traverse the path until we reach the final property
                for (int i = 0; i < pathParts.Length - 1; i++)
                {
                    string part = pathParts[i];
                    bool isArray = false;
                    int arrayIndex = -1;

                    // Check if this part contains array indexing
                    if (part.Contains("["))
                    {
                        int startBracket = part.IndexOf('[');
                        int endBracket = part.IndexOf(']');
                        if (startBracket > 0 && endBracket > startBracket)
                        {
                            string indexStr = part.Substring(startBracket + 1, endBracket - startBracket - 1);
                            if (int.TryParse(indexStr, out arrayIndex))
                            {
                                isArray = true;
                                part = part.Substring(0, startBracket);
                            }
                        }
                    }

                    // Get the property/field
                    PropertyInfo propInfo = currentType.GetProperty(part, flags);
                    FieldInfo fieldInfo = null;
                    if (propInfo == null)
                    {
                        fieldInfo = currentType.GetField(part, flags);
                        if (fieldInfo == null)
                        {
                            Debug.LogWarning($"[SetNestedProperty] Could not find property or field '{part}' on type '{currentType.Name}'");
                            return false;
                        }
                    }

                    // Get the value
                    currentObject = propInfo != null ? propInfo.GetValue(currentObject) : fieldInfo.GetValue(currentObject);
                    
                    // If the current property is null, we need to stop
                    if (currentObject == null)
                    {
                        Debug.LogWarning($"[SetNestedProperty] Property '{part}' is null, cannot access nested properties.");
                        return false;
                    }

                    // If this is an array/list access, get the element at the index
                    if (isArray)
                    {
                        if (currentObject is Material[])
                        {
                            var materials = currentObject as Material[];
                            if (arrayIndex < 0 || arrayIndex >= materials.Length)
                            {
                                Debug.LogWarning($"[SetNestedProperty] Material index {arrayIndex} out of range (0-{materials.Length-1})");
                                return false;
                            }
                            currentObject = materials[arrayIndex];
                        }
                        else if (currentObject is System.Collections.IList)
                        {
                            var list = currentObject as System.Collections.IList;
                            if (arrayIndex < 0 || arrayIndex >= list.Count)
                            {
                                Debug.LogWarning($"[SetNestedProperty] Index {arrayIndex} out of range (0-{list.Count-1})");
                                return false;
                            }
                            currentObject = list[arrayIndex];
                        }
                        else
                        {
                            Debug.LogWarning($"[SetNestedProperty] Property '{part}' is not an array or list, cannot access by index.");
                            return false;
                        }
                    }

                    // Update type for next iteration
                    currentType = currentObject.GetType();
                }

                // Set the final property
                string finalPart = pathParts[pathParts.Length - 1];
                
                // Special handling for Material properties (shader properties)
                if (currentObject is Material material && finalPart.StartsWith("_"))
                {
                    // Handle various material property types
                    if (value is JArray jArray)
                    {
                        if (jArray.Count == 4) // Color with alpha
                        {
                            Color color = new Color(
                                jArray[0].ToObject<float>(),
                                jArray[1].ToObject<float>(),
                                jArray[2].ToObject<float>(),
                                jArray[3].ToObject<float>()
                            );
                            material.SetColor(finalPart, color);
                            return true;
                        }
                        else if (jArray.Count == 3) // Color without alpha
                        {
                            Color color = new Color(
                                jArray[0].ToObject<float>(),
                                jArray[1].ToObject<float>(),
                                jArray[2].ToObject<float>(),
                                1.0f
                            );
                            material.SetColor(finalPart, color);
                            return true;
                        }
                        else if (jArray.Count == 2) // Vector2
                        {
                            Vector2 vec = new Vector2(
                                jArray[0].ToObject<float>(),
                                jArray[1].ToObject<float>()
                            );
                            material.SetVector(finalPart, vec);
                            return true;
                        }
                        else if (jArray.Count == 4) // Vector4
                        {
                            Vector4 vec = new Vector4(
                                jArray[0].ToObject<float>(),
                                jArray[1].ToObject<float>(),
                                jArray[2].ToObject<float>(),
                                jArray[3].ToObject<float>()
                            );
                            material.SetVector(finalPart, vec);
                            return true;
                        }
                    }
                    else if (value.Type == JTokenType.Float || value.Type == JTokenType.Integer)
                    {
                        material.SetFloat(finalPart, value.ToObject<float>());
                        return true;
                    }
                    else if (value.Type == JTokenType.Boolean)
                    {
                        material.SetFloat(finalPart, value.ToObject<bool>() ? 1f : 0f);
                        return true;
                    }
                    else if (value.Type == JTokenType.String)
                    {
                        // Might be a texture path
                        string texturePath = value.ToString();
                        if (texturePath.EndsWith(".png") || texturePath.EndsWith(".jpg") || texturePath.EndsWith(".tga"))
                        {
                            Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
                            if (texture != null)
                            {
                                material.SetTexture(finalPart, texture);
                                return true;
                            }
                        }
                        else
                        {
                            // Materials don't have SetString, use SetTextureOffset as workaround or skip
                            // material.SetString(finalPart, texturePath);
                            Debug.LogWarning($"[SetNestedProperty] String values not directly supported for material property {finalPart}");
                            return false;
                        }
                    }
                    
                    Debug.LogWarning($"[SetNestedProperty] Unsupported material property value type: {value.Type} for {finalPart}");
                    return false;
                }
                
                // For standard properties (not shader specific)
                PropertyInfo finalPropInfo = currentType.GetProperty(finalPart, flags);
                if (finalPropInfo != null && finalPropInfo.CanWrite)
                {
                    object convertedValue = ConvertJTokenToType(value, finalPropInfo.PropertyType);
                    if (convertedValue != null)
                    {
                        finalPropInfo.SetValue(currentObject, convertedValue);
                        return true;
                    }
                }
                else
                {
                    FieldInfo finalFieldInfo = currentType.GetField(finalPart, flags);
                    if (finalFieldInfo != null)
                    {
                        object convertedValue = ConvertJTokenToType(value, finalFieldInfo.FieldType);
                        if (convertedValue != null)
                        {
                            finalFieldInfo.SetValue(currentObject, convertedValue);
                            return true;
                        }
                    }
                    else
                    {
                        Debug.LogWarning($"[SetNestedProperty] Could not find final property or field '{finalPart}' on type '{currentType.Name}'");
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[SetNestedProperty] Error setting nested property '{path}': {ex.Message}");
            }
            
            return false;
        }
        
        /// <summary>
        /// Split a property path into parts, handling both dot notation and array indexers
        /// </summary>
        private static string[] SplitPropertyPath(string path)
        {
            // Handle complex paths with both dots and array indexers
            List<string> parts = new List<string>();
            int startIndex = 0;
            bool inBrackets = false;
            
            for (int i = 0; i < path.Length; i++)
            {
                char c = path[i];
                
                if (c == '[')
                {
                    inBrackets = true;
                }
                else if (c == ']')
                {
                    inBrackets = false;
                }
                else if (c == '.' && !inBrackets)
                {
                    // Found a dot separator outside of brackets
                    parts.Add(path.Substring(startIndex, i - startIndex));
                    startIndex = i + 1;
                }
            }
            
            // Add the final part
            if (startIndex < path.Length)
            {
                parts.Add(path.Substring(startIndex));
            }
            
            return parts.ToArray();
        }

        /// <summary>
        /// Simple JToken to Type conversion for common Unity types.
        /// </summary>
        private static object ConvertJTokenToType(JToken token, Type targetType)
        {
             try
             {
                 // Unwrap nested material properties if we're assigning to a Material
                 if (typeof(Material).IsAssignableFrom(targetType) && token is JObject materialProps)
                 {
                     // Handle case where we're passing shader properties directly in a nested object
                     string materialPath = token["path"]?.ToString();
                     if (!string.IsNullOrEmpty(materialPath))
                     {
                         // Load the material by path
                         Material material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
                         if (material != null)
                         {
                             // If there are additional properties, set them
                             foreach (var prop in materialProps.Properties())
                             {
                                 if (prop.Name != "path")
                                 {
                                     SetProperty(material, prop.Name, prop.Value);
                                 }
                             }
                             return material;
                         }
                         else
                         {
                             Debug.LogWarning($"[ConvertJTokenToType] Could not load material at path: '{materialPath}'");
                             return null;
                         }
                     }
                     
                     // If no path is specified, could be a dynamic material or instance set by reference                     
                     return null;
                 }
                 
                 // Basic types first
                 if (targetType == typeof(string)) return token.ToObject<string>();
                 if (targetType == typeof(int)) return token.ToObject<int>();
                 if (targetType == typeof(float)) return token.ToObject<float>();
                 if (targetType == typeof(bool)) return token.ToObject<bool>();
                 
                 // Vector/Quaternion/Color types
                 if (targetType == typeof(Vector2) && token is JArray arrV2 && arrV2.Count == 2) 
                     return new Vector2(arrV2[0].ToObject<float>(), arrV2[1].ToObject<float>());
                 if (targetType == typeof(Vector3) && token is JArray arrV3 && arrV3.Count == 3) 
                     return new Vector3(arrV3[0].ToObject<float>(), arrV3[1].ToObject<float>(), arrV3[2].ToObject<float>());
                if (targetType == typeof(Vector4) && token is JArray arrV4 && arrV4.Count == 4) 
                     return new Vector4(arrV4[0].ToObject<float>(), arrV4[1].ToObject<float>(), arrV4[2].ToObject<float>(), arrV4[3].ToObject<float>());
                 if (targetType == typeof(Quaternion) && token is JArray arrQ && arrQ.Count == 4)
                     return new Quaternion(arrQ[0].ToObject<float>(), arrQ[1].ToObject<float>(), arrQ[2].ToObject<float>(), arrQ[3].ToObject<float>());
                 if (targetType == typeof(Color) && token is JArray arrC && arrC.Count >= 3) // Allow RGB or RGBA
                     return new Color(arrC[0].ToObject<float>(), arrC[1].ToObject<float>(), arrC[2].ToObject<float>(), arrC.Count > 3 ? arrC[3].ToObject<float>() : 1.0f);
                 
                 // Enum types
                 if (targetType.IsEnum)
                    return Enum.Parse(targetType, token.ToString(), true); // Case-insensitive enum parsing

                 // Handle assigning Unity Objects (Assets, Scene Objects, Components)
                 if (typeof(UnityEngine.Object).IsAssignableFrom(targetType))
                 {
                     // CASE 1: Reference is a JSON Object specifying a scene object/component find criteria
                     if (token is JObject refObject)
                     {
                         JToken findToken = refObject["find"];
                         string findMethod = refObject["method"]?.ToString() ?? "by_id_or_name_or_path"; // Default search
                         string componentTypeName = refObject["component"]?.ToString();

                         if (findToken == null)
                         {
                             Debug.LogWarning($"[ConvertJTokenToType] Reference object missing 'find' property: {token}");
                             return null;
                         }

                         // Find the target GameObject
                         // Pass 'searchInactive: true' for internal lookups to be more robust
                         JObject findParams = new JObject(); 
                         findParams["searchInactive"] = true; 
                         GameObject foundGo = FindObjectInternal(findToken, findMethod, findParams);

                         if (foundGo == null)
                         {
                             Debug.LogWarning($"[ConvertJTokenToType] Could not find GameObject specified by reference object: {token}");
                             return null;
                         }

                         // If a component type is specified, try to get it
                         if (!string.IsNullOrEmpty(componentTypeName))
                         {
                             Type compType = FindType(componentTypeName);
                             if (compType == null)
                             {
                                 Debug.LogWarning($"[ConvertJTokenToType] Could not find component type '{componentTypeName}' specified in reference object: {token}");
                                 return null;
                             }
                             
                             // Ensure the targetType is assignable from the found component type
                             if (!targetType.IsAssignableFrom(compType))
                             {
                                Debug.LogWarning($"[ConvertJTokenToType] Found component '{componentTypeName}' but it is not assignable to the target property type '{targetType.Name}'. Reference: {token}");
                                return null;
                             }

                             Component foundComp = foundGo.GetComponent(compType);
                             if (foundComp == null)
                             {
                                 Debug.LogWarning($"[ConvertJTokenToType] Found GameObject '{foundGo.name}' but could not find component '{componentTypeName}' on it. Reference: {token}");
                                 return null;
                             }
                             return foundComp; // Return the found component
                         }
                         else
                         {
                             // Otherwise, return the GameObject itself, ensuring it's assignable
                             if (!targetType.IsAssignableFrom(typeof(GameObject)))
                             {
                                  Debug.LogWarning($"[ConvertJTokenToType] Found GameObject '{foundGo.name}' but it is not assignable to the target property type '{targetType.Name}' (component name was not specified). Reference: {token}");
                                  return null;
                             }
                             return foundGo; // Return the found GameObject
                         }
                     }
                     // CASE 2: Reference is a string, assume it's an asset path
                     else if (token.Type == JTokenType.String)
                     {
                         string assetPath = token.ToString();
                         if (!string.IsNullOrEmpty(assetPath))
                         {
                              // Attempt to load the asset from the provided path using the target type
                              UnityEngine.Object loadedAsset = AssetDatabase.LoadAssetAtPath(assetPath, targetType);
                              if (loadedAsset != null)
                              {
                                  return loadedAsset; // Return the loaded asset if successful
                              }
                              else
                              {
                                  // Log a warning if the asset could not be found at the path
                                  Debug.LogWarning($"[ConvertJTokenToType] Could not load asset of type '{targetType.Name}' from path: '{assetPath}'. Make sure the path is correct and the asset exists.");
                                  return null;
                             }
                         }
                         else
                         {
                             // Handle cases where an empty string might be intended to clear the reference
                             return null; // Assign null if the path is empty
                         }
                     }
                    // CASE 3: Reference is null or empty JToken, assign null
                    else if (token.Type == JTokenType.Null || string.IsNullOrEmpty(token.ToString()))
                    {
                        return null; 
                    }
                     // CASE 4: Invalid format for Unity Object reference
                     else
                     {
                          Debug.LogWarning($"[ConvertJTokenToType] Expected a string asset path or a reference object to assign Unity Object of type '{targetType.Name}', but received token type '{token.Type}'. Value: {token}");
                          return null;
                     }
                 }

                 // Fallback: Try direct conversion (might work for other simple value types)
                 // Be cautious here, this might throw errors for complex types not handled above
                 try {
                     return token.ToObject(targetType); 
                 } catch (Exception directConversionEx) {
                      Debug.LogWarning($"[ConvertJTokenToType] Direct conversion failed for JToken '{token}' to type '{targetType.Name}': {directConversionEx.Message}. Specific handling might be needed.");
                      return null;
                 }
             }
             catch (Exception ex)
             {
                 Debug.LogWarning($"[ConvertJTokenToType] Could not convert JToken '{token}' to type '{targetType.Name}': {ex.Message}");
                 return null;
             }
        }


        /// <summary>
        /// Helper to find a Type by name, searching relevant assemblies.
        /// </summary>
        private static Type FindType(string typeName)
        {
            if (string.IsNullOrEmpty(typeName)) return null;

            // Handle common Unity namespaces implicitly
            var type = Type.GetType($"UnityEngine.{typeName}, UnityEngine.CoreModule") ??
                       Type.GetType($"UnityEngine.{typeName}, UnityEngine.PhysicsModule") ?? // Example physics
                       Type.GetType($"UnityEngine.UI.{typeName}, UnityEngine.UI") ?? // Example UI
                       Type.GetType($"UnityEditor.{typeName}, UnityEditor.CoreModule") ?? 
                       Type.GetType(typeName); // Try direct name (if fully qualified or in mscorlib)

            if (type != null) return type;

            // If not found, search all loaded assemblies (slower)
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                type = assembly.GetType(typeName);
                if (type != null) return type;
                // Also check with namespaces if simple name given
                type = assembly.GetType("UnityEngine." + typeName);
                if (type != null) return type;
                 type = assembly.GetType("UnityEditor." + typeName);
                if (type != null) return type;
                 type = assembly.GetType("UnityEngine.UI." + typeName);
                 if (type != null) return type;
            }

            return null; // Not found
        }

        /// <summary>
        /// Parses a JArray like [x, y, z] into a Vector3.
        /// </summary>
        private static Vector3? ParseVector3(JArray array)
        {
            if (array != null && array.Count == 3)
            {
                try
                {
                    return new Vector3(
                        array[0].ToObject<float>(),
                        array[1].ToObject<float>(),
                        array[2].ToObject<float>()
                    );
                }
                catch { /* Ignore parsing errors */ }
            }
            return null;
        }

        // --- Data Serialization ---

        /// <summary>
        /// Creates a serializable representation of a GameObject.
        /// </summary>
        private static object GetGameObjectData(GameObject go)
        {
            if (go == null) return null;
            return new
            {
                name = go.name,
                instanceID = go.GetInstanceID(),
                tag = go.tag,
                layer = go.layer,
                activeSelf = go.activeSelf,
                activeInHierarchy = go.activeInHierarchy,
                isStatic = go.isStatic,
                scenePath = go.scene.path, // Identify which scene it belongs to
                transform = new // Serialize transform components carefully to avoid JSON issues
                {
                    // Serialize Vector3 components individually to prevent self-referencing loops.
                    // The default serializer can struggle with properties like Vector3.normalized.
                    position = new { x = go.transform.position.x, y = go.transform.position.y, z = go.transform.position.z },
                    localPosition = new { x = go.transform.localPosition.x, y = go.transform.localPosition.y, z = go.transform.localPosition.z },
                    rotation = new { x = go.transform.rotation.eulerAngles.x, y = go.transform.rotation.eulerAngles.y, z = go.transform.rotation.eulerAngles.z },
                    localRotation = new { x = go.transform.localRotation.eulerAngles.x, y = go.transform.localRotation.eulerAngles.y, z = go.transform.localRotation.eulerAngles.z },
                    scale = new { x = go.transform.localScale.x, y = go.transform.localScale.y, z = go.transform.localScale.z },
                    forward = new { x = go.transform.forward.x, y = go.transform.forward.y, z = go.transform.forward.z },
                    up = new { x = go.transform.up.x, y = go.transform.up.y, z = go.transform.up.z },
                    right = new { x = go.transform.right.x, y = go.transform.right.y, z = go.transform.right.z }
                },
                parentInstanceID = go.transform.parent?.gameObject.GetInstanceID() ?? 0, // 0 if no parent
                // Optionally include components, but can be large
                 // components = go.GetComponents<Component>().Select(c => GetComponentData(c)).ToList()
                 // Or just component names:
                 componentNames = go.GetComponents<Component>().Select(c => c.GetType().FullName).ToList()
            };
        }

        /// <summary>
        /// Creates a serializable representation of a Component.
        /// TODO: Add property serialization.
        /// </summary>
         private static object GetComponentData(Component c)
         {
             if (c == null) return null;
             var data = new Dictionary<string, object> {
                 { "typeName", c.GetType().FullName },
                 { "instanceID", c.GetInstanceID() }
             };

             // Attempt to serialize public properties/fields (can be noisy/complex)
             /*
             try {
                 var properties = new Dictionary<string, object>();
                 var type = c.GetType();
                 BindingFlags flags = BindingFlags.Public | BindingFlags.Instance;
                 
                 foreach (var prop in type.GetProperties(flags).Where(p => p.CanRead && p.GetIndexParameters().Length == 0)) {
                     try { properties[prop.Name] = prop.GetValue(c); } catch { }
                 }
                 foreach (var field in type.GetFields(flags)) {
                      try { properties[field.Name] = field.GetValue(c); } catch { }
                 }
                 data["properties"] = properties;
             } catch (Exception ex) {
                 data["propertiesError"] = ex.Message;
             }
             */
             return data;
         }
    }
} 