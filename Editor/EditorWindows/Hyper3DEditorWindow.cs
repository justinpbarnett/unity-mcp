using UnityEngine;
using UnityEditor;
using System.Collections.Generic;
using System;
using System.Runtime.CompilerServices;
using System.ComponentModel;
using Newtonsoft.Json.Linq;

#if UNITY_EDITOR
namespace Hyper3DRodin{
    // Enum definition
    public enum ServiceProvider
    {
        MAIN_SITE,
        FAL_AI
    }

    static class Constants
    {
        private const string FREE_TRIAL_KEY = "k9TcfFoEhNd9cCPP2guHAHHHkctZHIRhZDywZ1euGUXwihbYLpOjQhofby80NJez";

        public static string GetFreeTrialKey()
        {
            return FREE_TRIAL_KEY;
        }
    }

    [Serializable]
    public class Settings
    {
        public bool enabled = false;
        public string apiKey = "";

        // Enum for service status
        public ServiceProvider serviceProvider = ServiceProvider.MAIN_SITE;
    }

    public static class SettingsManager
    {
        private const string EnableServiceKey = "UnityMCP.Hyper3D.EnableService";
        private const string ApiKeyKey = "UnityMCP.Hyper3D.ApiKey";
        private const string ServiceProviderKey = "UnityMCP.Hyper3D.ServiceProvider";

        public static bool enabled
        {
            get => EditorPrefs.GetBool(EnableServiceKey, false);
            set => EditorPrefs.SetBool(EnableServiceKey, value);
        }

        public static string apiKey
        {
            get => EditorPrefs.GetString(ApiKeyKey, "");
            set => EditorPrefs.SetString(ApiKeyKey, value);
        }

        public static ServiceProvider serviceProvider
        {
            get => (ServiceProvider)EditorPrefs.GetInt(ServiceProviderKey, (int)ServiceProvider.MAIN_SITE);
            set => EditorPrefs.SetInt(ServiceProviderKey, (int)value);
        }
    }

    public class SettingsEditorWindow : EditorWindow
    {
        [MenuItem("Window/Unity MCP Modules/Hyper3D Rodin")]
        public static void ShowWindow()
        {
            GetWindow<SettingsEditorWindow>("Hyper3D Rodin Settings");
        }

        private void OnGUI()
        {
            SettingsManager.enabled = EditorGUILayout.Toggle("Enable Hyper3D Rodin Service", SettingsManager.enabled);
            SettingsManager.apiKey = EditorGUILayout.PasswordField("API Key", SettingsManager.apiKey);
            // "Set Free Trial Key" button
            if (GUILayout.Button("Set Free Trial Key"))
            {
                SettingsManager.apiKey = Constants.GetFreeTrialKey();
                SettingsManager.serviceProvider = ServiceProvider.MAIN_SITE;
            }

            // Custom Enum Popup with Friendly Names
            SettingsManager.serviceProvider = (ServiceProvider)EditorGUILayout.Popup(
                "Service Provider", 
                (int)SettingsManager.serviceProvider, 
                GetEnumDisplayNames()
            );
        }

        private string[] GetEnumDisplayNames()
        {
            Dictionary<ServiceProvider, string> enumDisplayNames = new Dictionary<ServiceProvider, string>
            {
                { ServiceProvider.MAIN_SITE, "hyper3d.ai" },
                { ServiceProvider.FAL_AI, "fal.ai" },
            };

            string[] displayNames = new string[enumDisplayNames.Count];
            int i = 0;
            foreach (var value in Enum.GetValues(typeof(ServiceProvider)))
            {
                displayNames[i++] = enumDisplayNames[(ServiceProvider)value];
            }
            return displayNames;
        }
    }
}
#endif
