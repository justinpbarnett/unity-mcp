using UnityEngine;
using Newtonsoft.Json.Linq;
using System;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine.SceneManagement;
using UnityEditor.SceneManagement;
using UnityMCP.Editor.Helpers;
using System.Reflection;

namespace UnityMCP.Editor.Commands
{
    /// <summary>
    /// Handles object-related commands
    /// </summary>
    public static class ObjectCommandHandler
    {
        /// <summary>
        /// Gets information about a specific object
        /// </summary>
        public static object GetObjectInfo(JObject @params)
        {
            string name = (string)@params["name"] ?? throw new Exception("Parameter 'name' is required.");
            var obj = GameObject.Find(name) ?? throw new Exception($"Object '{name}' not found.");
            return new
            {
                obj.name,
                position = new[] { obj.transform.position.x, obj.transform.position.y, obj.transform.position.z },
                rotation = new[] { obj.transform.eulerAngles.x, obj.transform.eulerAngles.y, obj.transform.eulerAngles.z },
                scale = new[] { obj.transform.localScale.x, obj.transform.localScale.y, obj.transform.localScale.z }
            };
        }

        /// <summary>
        /// Creates a new object in the scene
        /// </summary>
        public static object CreateObject(JObject @params)
        {
            string type = (string)@params["type"] ?? throw new Exception("Parameter 'type' is required.");
            GameObject obj = type.ToUpper() switch
            {
                "CUBE" => GameObject.CreatePrimitive(PrimitiveType.Cube),
                "SPHERE" => GameObject.CreatePrimitive(PrimitiveType.Sphere),
                "CYLINDER" => GameObject.CreatePrimitive(PrimitiveType.Cylinder),
                "CAPSULE" => GameObject.CreatePrimitive(PrimitiveType.Capsule),
                "PLANE" => GameObject.CreatePrimitive(PrimitiveType.Plane),
                "EMPTY" => new GameObject(),
                "CAMERA" => new GameObject("Camera") { }.AddComponent<Camera>().gameObject,
                "LIGHT" => new GameObject("Light") { }.AddComponent<Light>().gameObject,
                "DIRECTIONAL_LIGHT" => CreateDirectionalLight(),
                _ => throw new Exception($"Unsupported object type: {type}")
            };

            if (@params.ContainsKey("name")) obj.name = (string)@params["name"];
            if (@params.ContainsKey("location")) obj.transform.position = Vector3Helper.ParseVector3((JArray)@params["location"]);
            if (@params.ContainsKey("rotation")) obj.transform.eulerAngles = Vector3Helper.ParseVector3((JArray)@params["rotation"]);
            if (@params.ContainsKey("scale")) obj.transform.localScale = Vector3Helper.ParseVector3((JArray)@params["scale"]);

            return new { obj.name };
        }

        /// <summary>
        /// Modifies an existing object's properties
        /// </summary>
        public static object ModifyObject(JObject @params)
        {
            string name = (string)@params["name"] ?? throw new Exception("Parameter 'name' is required.");
            var obj = GameObject.Find(name) ?? throw new Exception($"Object '{name}' not found.");

            // Handle basic transform properties
            if (@params.ContainsKey("location")) obj.transform.position = Vector3Helper.ParseVector3((JArray)@params["location"]);
            if (@params.ContainsKey("rotation")) obj.transform.eulerAngles = Vector3Helper.ParseVector3((JArray)@params["rotation"]);
            if (@params.ContainsKey("scale")) obj.transform.localScale = Vector3Helper.ParseVector3((JArray)@params["scale"]);
            if (@params.ContainsKey("visible")) obj.SetActive((bool)@params["visible"]);

            // Handle parent setting
            if (@params.ContainsKey("set_parent"))
            {
                string parentName = (string)@params["set_parent"];
                var parent = GameObject.Find(parentName) ?? throw new Exception($"Parent object '{parentName}' not found.");
                obj.transform.SetParent(parent.transform);
            }

            // Handle component operations
            if (@params.ContainsKey("add_component"))
            {
                string componentType = (string)@params["add_component"];
                Type type = componentType switch
                {
                    "Rigidbody" => typeof(Rigidbody),
                    "BoxCollider" => typeof(BoxCollider),
                    "SphereCollider" => typeof(SphereCollider),
                    "CapsuleCollider" => typeof(CapsuleCollider),
                    "MeshCollider" => typeof(MeshCollider),
                    "Camera" => typeof(Camera),
                    "Light" => typeof(Light),
                    "Renderer" => typeof(Renderer),
                    "MeshRenderer" => typeof(MeshRenderer),
                    "SkinnedMeshRenderer" => typeof(SkinnedMeshRenderer),
                    "Animator" => typeof(Animator),
                    "AudioSource" => typeof(AudioSource),
                    "AudioListener" => typeof(AudioListener),
                    "ParticleSystem" => typeof(ParticleSystem),
                    "ParticleSystemRenderer" => typeof(ParticleSystemRenderer),
                    "TrailRenderer" => typeof(TrailRenderer),
                    "LineRenderer" => typeof(LineRenderer),
                    "TextMesh" => typeof(TextMesh),
                    "TextMeshPro" => typeof(TMPro.TextMeshPro),
                    "TextMeshProUGUI" => typeof(TMPro.TextMeshProUGUI),
                    _ => Type.GetType($"UnityEngine.{componentType}") ??
                         Type.GetType(componentType) ??
                         FindTypeInLoadedAssemblies(componentType) ??
                         throw new Exception($"Component type '{componentType}' not found.")
                };
                obj.AddComponent(type);
            }

            if (@params.ContainsKey("remove_component"))
            {
                string componentType = (string)@params["remove_component"];
                Type type = Type.GetType($"UnityEngine.{componentType}") ??
                           Type.GetType(componentType) ??
                           throw new Exception($"Component type '{componentType}' not found.");
                var component = obj.GetComponent(type);
                if (component != null)
                    UnityEngine.Object.DestroyImmediate(component);
            }

            // Handle property setting
            if (@params.ContainsKey("set_property"))
            {
                var propertyData = (JObject)@params["set_property"];
                string componentType = (string)propertyData["component"];
                string propertyName = (string)propertyData["property"];
                var value = propertyData["value"];

                // Handle GameObject properties separately
                if (componentType == "GameObject")
                {
                    var gameObjectProperty = typeof(GameObject).GetProperty(propertyName) ??
                                 throw new Exception($"Property '{propertyName}' not found on GameObject.");

                    // Convert value based on property type
                    object gameObjectValue = Convert.ChangeType(value, gameObjectProperty.PropertyType);
                    gameObjectProperty.SetValue(obj, gameObjectValue);
                    return new { obj.name };
                }

                // Handle component properties
                Type type = componentType switch
                {
                    "Rigidbody" => typeof(Rigidbody),
                    "BoxCollider" => typeof(BoxCollider),
                    "SphereCollider" => typeof(SphereCollider),
                    "CapsuleCollider" => typeof(CapsuleCollider),
                    "MeshCollider" => typeof(MeshCollider),
                    "Camera" => typeof(Camera),
                    "Light" => typeof(Light),
                    "Renderer" => typeof(Renderer),
                    "MeshRenderer" => typeof(MeshRenderer),
                    "SkinnedMeshRenderer" => typeof(SkinnedMeshRenderer),
                    "Animator" => typeof(Animator),
                    "AudioSource" => typeof(AudioSource),
                    "AudioListener" => typeof(AudioListener),
                    "ParticleSystem" => typeof(ParticleSystem),
                    "ParticleSystemRenderer" => typeof(ParticleSystemRenderer),
                    "TrailRenderer" => typeof(TrailRenderer),
                    "LineRenderer" => typeof(LineRenderer),
                    "TextMesh" => typeof(TextMesh),
                    "TextMeshPro" => typeof(TMPro.TextMeshPro),
                    "TextMeshProUGUI" => typeof(TMPro.TextMeshProUGUI),
                    _ => Type.GetType($"UnityEngine.{componentType}") ??
                         Type.GetType(componentType) ??
                         FindTypeInLoadedAssemblies(componentType) ??
                         throw new Exception($"Component type '{componentType}' not found.")
                };

                var component = obj.GetComponent(type) ??
                               throw new Exception($"Component '{componentType}' not found on object '{name}'.");

                var property = type.GetProperty(propertyName) ??
                              throw new Exception($"Property '{propertyName}' not found on component '{componentType}'.");

                // Convert value based on property type
                object propertyValue = Convert.ChangeType(value, property.PropertyType);
                property.SetValue(component, propertyValue);
            }

            return new { obj.name };
        }

        /// <summary>
        /// Deletes an object from the scene
        /// </summary>
        public static object DeleteObject(JObject @params)
        {
            string name = (string)@params["name"] ?? throw new Exception("Parameter 'name' is required.");
            var obj = GameObject.Find(name) ?? throw new Exception($"Object '{name}' not found.");
            UnityEngine.Object.DestroyImmediate(obj);
            return new { name };
        }

        /// <summary>
        /// Gets all properties of a specified game object
        /// </summary>
        public static object GetObjectProperties(JObject @params)
        {
            string name = (string)@params["name"] ?? throw new Exception("Parameter 'name' is required.");
            var obj = GameObject.Find(name) ?? throw new Exception($"Object '{name}' not found.");

            var components = obj.GetComponents<Component>()
                .Select(c => new
                {
                    type = c.GetType().Name,
                    properties = GetComponentProperties(c)
                })
                .ToList();

            return new
            {
                obj.name,
                obj.tag,
                obj.layer,
                active = obj.activeSelf,
                transform = new
                {
                    position = new[] { obj.transform.position.x, obj.transform.position.y, obj.transform.position.z },
                    rotation = new[] { obj.transform.eulerAngles.x, obj.transform.eulerAngles.y, obj.transform.eulerAngles.z },
                    scale = new[] { obj.transform.localScale.x, obj.transform.localScale.y, obj.transform.localScale.z }
                },
                components
            };
        }

        /// <summary>
        /// Gets properties of a specific component
        /// </summary>
        public static object GetComponentProperties(JObject @params)
        {
            string objectName = (string)@params["object_name"] ?? throw new Exception("Parameter 'object_name' is required.");
            string componentType = (string)@params["component_type"] ?? throw new Exception("Parameter 'component_type' is required.");

            var obj = GameObject.Find(objectName) ?? throw new Exception($"Object '{objectName}' not found.");
            var component = obj.GetComponent(componentType) ?? throw new Exception($"Component '{componentType}' not found on object '{objectName}'.");

            return GetComponentProperties(component);
        }

        /// <summary>
        /// Finds objects by name in the scene
        /// </summary>
        public static object FindObjectsByName(JObject @params)
        {
            string name = (string)@params["name"] ?? throw new Exception("Parameter 'name' is required.");
            var objects = GameObject.FindObjectsByType<GameObject>(FindObjectsSortMode.None)
                .Where(o => o.name.Contains(name))
                .Select(o => new
                {
                    o.name,
                    path = GetGameObjectPath(o)
                })
                .ToList();

            return new { objects };
        }

        /// <summary>
        /// Finds objects by tag in the scene
        /// </summary>
        public static object FindObjectsByTag(JObject @params)
        {
            string tag = (string)@params["tag"] ?? throw new Exception("Parameter 'tag' is required.");
            var objects = GameObject.FindGameObjectsWithTag(tag)
                .Select(o => new
                {
                    o.name,
                    path = GetGameObjectPath(o)
                })
                .ToList();

            return new { objects };
        }

        /// <summary>
        /// Gets the current hierarchy of game objects in the scene
        /// </summary>
        public static object GetHierarchy()
        {
            var rootObjects = SceneManager.GetActiveScene().GetRootGameObjects();
            var hierarchy = rootObjects.Select(o => BuildHierarchyNode(o)).ToList();

            return new { hierarchy };
        }

        /// <summary>
        /// Selects a specified game object in the editor
        /// </summary>
        public static object SelectObject(JObject @params)
        {
            string name = (string)@params["name"] ?? throw new Exception("Parameter 'name' is required.");
            var obj = GameObject.Find(name) ?? throw new Exception($"Object '{name}' not found.");

            Selection.activeGameObject = obj;
            return new { obj.name };
        }

        /// <summary>
        /// Gets the currently selected game object in the editor
        /// </summary>
        public static object GetSelectedObject()
        {
            var selected = Selection.activeGameObject;
            if (selected == null)
                return new { selected = (object)null };

            return new
            {
                selected = new
                {
                    selected.name,
                    path = GetGameObjectPath(selected)
                }
            };
        }

        // Helper methods
        private static Dictionary<string, object> GetComponentProperties(Component component)
        {
            var properties = new Dictionary<string, object>();
            var serializedObject = new SerializedObject(component);
            var property = serializedObject.GetIterator();

            while (property.Next(true))
            {
                properties[property.name] = GetPropertyValue(property);
            }

            return properties;
        }

        private static object GetPropertyValue(SerializedProperty property)
        {
            switch (property.propertyType)
            {
                case SerializedPropertyType.Integer:
                    return property.intValue;
                case SerializedPropertyType.Float:
                    return property.floatValue;
                case SerializedPropertyType.Boolean:
                    return property.boolValue;
                case SerializedPropertyType.String:
                    return property.stringValue;
                case SerializedPropertyType.Vector3:
                    return new[] { property.vector3Value.x, property.vector3Value.y, property.vector3Value.z };
                case SerializedPropertyType.Vector2:
                    return new[] { property.vector2Value.x, property.vector2Value.y };
                case SerializedPropertyType.Color:
                    return new[] { property.colorValue.r, property.colorValue.g, property.colorValue.b, property.colorValue.a };
                case SerializedPropertyType.ObjectReference:
                    return property.objectReferenceValue ? property.objectReferenceValue.name : null;
                default:
                    return property.propertyType.ToString();
            }
        }

        private static string GetGameObjectPath(GameObject obj)
        {
            var path = obj.name;
            var parent = obj.transform.parent;

            while (parent != null)
            {
                path = parent.name + "/" + path;
                parent = parent.parent;
            }

            return path;
        }

        private static object BuildHierarchyNode(GameObject obj)
        {
            return new
            {
                obj.name,
                children = Enumerable.Range(0, obj.transform.childCount)
                    .Select(i => BuildHierarchyNode(obj.transform.GetChild(i).gameObject))
                    .ToList()
            };
        }

        /// <summary>
        /// Creates a directional light game object
        /// </summary>
        private static GameObject CreateDirectionalLight()
        {
            var obj = new GameObject("DirectionalLight");
            var light = obj.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.0f;
            light.shadows = LightShadows.Soft;
            return obj;
        }

        /// <summary>
        /// Executes a context menu method on a component of a game object
        /// </summary>
        public static object ExecuteContextMenuItem(JObject @params)
        {
            string objectName = (string)@params["object_name"] ?? throw new Exception("Parameter 'object_name' is required.");
            string componentName = (string)@params["component"] ?? throw new Exception("Parameter 'component' is required.");
            string contextMenuItemName = (string)@params["context_menu_item"] ?? throw new Exception("Parameter 'context_menu_item' is required.");

            // Find the game object
            var obj = GameObject.Find(objectName) ?? throw new Exception($"Object '{objectName}' not found.");

            // Find the component type
            Type componentType = FindTypeInLoadedAssemblies(componentName) ??
                throw new Exception($"Component type '{componentName}' not found.");

            // Get the component from the game object
            var component = obj.GetComponent(componentType) ??
                throw new Exception($"Component '{componentName}' not found on object '{objectName}'.");

            // Find methods with ContextMenu attribute matching the context menu item name
            var methods = componentType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                .Where(m => m.GetCustomAttributes(typeof(ContextMenuItemAttribute), true).Any() ||
                           m.GetCustomAttributes(typeof(ContextMenu), true)
                               .Cast<ContextMenu>()
                               .Any(attr => attr.menuItem == contextMenuItemName))
                .ToList();

            // If no methods with ContextMenuItemAttribute are found, look for methods with name matching the context menu item
            if (methods.Count == 0)
            {
                methods = componentType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                    .Where(m => m.Name == contextMenuItemName)
                    .ToList();
            }

            if (methods.Count == 0)
                throw new Exception($"No context menu method '{contextMenuItemName}' found on component '{componentName}'.");

            // If multiple methods match, use the first one and log a warning
            if (methods.Count > 1)
            {
                Debug.LogWarning($"Found multiple methods for context menu item '{contextMenuItemName}' on component '{componentName}'. Using the first one.");
            }

            var method = methods[0];

            // Execute the method
            try
            {
                method.Invoke(component, null);
                return new 
                { 
                    success = true, 
                    message = $"Successfully executed context menu item '{contextMenuItemName}' on component '{componentName}' of object '{objectName}'."
                };
            }
            catch (Exception ex)
            {
                throw new Exception($"Error executing context menu item: {ex.Message}");
            }
        }

        // Add this helper method to find types across all loaded assemblies
        private static Type FindTypeInLoadedAssemblies(string typeName)
        {
            // First try standard approach
            Type type = Type.GetType(typeName);
            if (type != null)
                return type;

            type = Type.GetType($"UnityEngine.{typeName}");
            if (type != null)
                return type;

            // Then search all loaded assemblies
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                // Try with the simple name
                type = assembly.GetType(typeName);
                if (type != null)
                    return type;

                // Try with the fully qualified name (assembly.GetTypes() can be expensive, so we do this last)
                var types = assembly.GetTypes().Where(t => t.Name == typeName).ToArray();

                if (types.Length > 0)
                {
                    // If we found multiple types with the same name, log a warning
                    if (types.Length > 1)
                    {
                        Debug.LogWarning(
                            $"Found multiple types named '{typeName}'. Using the first one: {types[0].FullName}"
                        );
                    }
                    return types[0];
                }
            }

            return null;
        }
    }
}