using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using GluonGui.Dialog;
using MCPServer.Editor.Commands;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

#if UNITY_EDITOR
namespace Hyper3DRodin{
    public static class Hyper3DRodinCommandHandler
    {
        public static object GetHyper3DStatus()
        {
            // Access settings globally
            bool enabled = SettingsManager.enabled;
            string apiKey = SettingsManager.apiKey;
            ServiceProvider mode = SettingsManager.serviceProvider;

            if (enabled)
            {
                if (string.IsNullOrEmpty(apiKey))
                {
                    return new
                    {
                        enabled = false,
                        message = @"Hyper3D Rodin integration is currently enabled, but no API key is provided. To enable it:
1. Open Unity's menu and go to **Window > Unity MCP > Hyper3D Rodin**.
2. Ensure the **'Enable Hyper3D Rodin Service'** checkbox is checked.
3. Select the appropriate **service provider**.
4. Enter your **API Key** in the provided input field.
5. Restart the connection for changes to take effect."
                    };
                }

                string keyType = apiKey == Constants.GetFreeTrialKey() ? "free_trial" : "private";
                string message = $"Hyper3D Rodin integration is enabled and ready to use. Provider: {mode}. " +
                                 $"Key type: {keyType}";

                return new
                {
                    enabled = true,
                    message = message
                };
            }
            else
            {
                return new
                {
                    enabled = false,
                    message = @"Hyper3D Rodin integration is currently disabled. To enable it:
1. Open Unity's menu and go to **Window > Unity MCP > Hyper3D Rodin**.
2. Check the **'Enable Hyper3D Rodin Service'** option.
3. Restart the connection for changes to take effect."
                };
            }
        }

        public static object CreateRodinJob(JObject @params)
        {
            switch (SettingsManager.serviceProvider)
            {
                case ServiceProvider.MAIN_SITE:
                    return CreateRodinJobMainSite(@params);
                case ServiceProvider.FAL_AI:
                    return CreateRodinJobFalAi(@params);
                default:
                    return new { error = "Error: Unknown Hyper3D Rodin mode!" };
            }
        }

        private static object CreateRodinJobMainSite(JObject @params)
        {
            HttpClient client = new HttpClient();
            try
            {
                var formData = new MultipartFormDataContent();
                if (@params["images"] is JArray imagesArray)
                {
                    int i = 0;
                    foreach (var img in imagesArray)
                    {
                        string imgSuffix = img["suffix"]?.ToString();
                        string imgPath = img["path"]?.ToString();
                        if (!string.IsNullOrEmpty(imgPath) && File.Exists(imgPath))
                        {
                            formData.Add(new ByteArrayContent(File.ReadAllBytes(imgPath)), "images", $"{i:D4}{imgSuffix}");
                            i++;
                        }
                    }
                }

                formData.Add(new StringContent("Sketch"), "tier");
                formData.Add(new StringContent("Raw"), "mesh_mode");


                if (@params["text_prompt"] != null)
                    formData.Add(new StringContent(@params["text_prompt"].ToString()), "prompt");

                if (@params["bbox_condition"] != null)
                    formData.Add(new StringContent(@params["bbox_condition"].ToString()), "bbox_condition");

                var request = new HttpRequestMessage(HttpMethod.Post, "https://hyperhuman.deemos.com/api/v2/rodin")
                {
                    Headers = { { "Authorization", $"Bearer {SettingsManager.apiKey}" } },
                    Content = formData
                };

                HttpResponseMessage response = client.SendAsync(request).Result;
                string responseBody = response.Content.ReadAsStringAsync().Result;
                return JObject.Parse(responseBody);
            }
            catch (Exception e)
            {
                return new JObject { ["error"] = e.Message };
            }
        }

        private static object CreateRodinJobFalAi(JObject @params)
        {
            HttpClient client = new HttpClient();
            try
            {
                var requestData = new JObject
                {
                    ["tier"] = "Sketch",
                };

                if (@params["images"] is JArray imagesArray)
                    requestData["input_image_urls"] = imagesArray;

                if (@params["text_prompt"] != null)
                    requestData["prompt"] = @params["text_prompt"].ToString();

                if (@params["bbox_condition"] != null)
                    requestData["bbox_condition"] = @params["bbox_condition"];

                var request = new HttpRequestMessage(HttpMethod.Post, "https://queue.fal.run/fal-ai/hyper3d/rodin")
                {
                    Headers = { { "Authorization", $"Key {SettingsManager.apiKey}" } },
                    Content = new StringContent(requestData.ToString(), Encoding.UTF8, "application/json")
                };

                HttpResponseMessage response = client.SendAsync(request).Result;
                string responseBody = response.Content.ReadAsStringAsync().Result;
                return JObject.Parse(responseBody);
            }
            catch (Exception e)
            {
                return new JObject { ["error"] = e.Message };
            }
        }

        public static object PollRodinJobStatus(JObject @params)
        {
            switch (SettingsManager.serviceProvider)
            {
                case ServiceProvider.MAIN_SITE:
                    return PollRodinJobStatusMainSite(@params);
                case ServiceProvider.FAL_AI:
                    return PollRodinJobStatusFalAi(@params);
                default:
                    return new JObject { ["error"] = "Error: Unknown Hyper3D Rodin mode!" };
            }
        }

        private static object PollRodinJobStatusMainSite(JObject @params)
        {
            HttpClient client = new HttpClient();
            try
            {
                var requestData = new JObject
                {
                    ["subscription_key"] = @params["subscription_key"]
                };

                var request = new HttpRequestMessage(HttpMethod.Post, "https://hyperhuman.deemos.com/api/v2/status")
                {
                    Headers = { { "Authorization", $"Bearer {SettingsManager.apiKey}" } },
                    Content = new StringContent(requestData.ToString(), Encoding.UTF8, "application/json"),
                };

                HttpResponseMessage response = client.SendAsync(request).Result;
                string responseBody = response.Content.ReadAsStringAsync().Result;
                return JObject.Parse(responseBody);
            }
            catch (Exception e)
            {
                return new JObject { ["error"] = e.Message };
            }
        }

        private static object PollRodinJobStatusFalAi(JObject @params)
        {
            HttpClient client = new HttpClient();
            try
            {
                string requestId = @params["request_id"]?.ToString();
                if (string.IsNullOrEmpty(requestId))
                    return new JObject { ["error"] = "Invalid request ID" };

                var request = new HttpRequestMessage(HttpMethod.Get, $"https://queue.fal.run/fal-ai/hyper3d/requests/{requestId}/status")
                {
                    Headers = { { "Authorization", $"Key {SettingsManager.apiKey}" } }
                };

                HttpResponseMessage response = client.SendAsync(request).Result;
                string responseBody = response.Content.ReadAsStringAsync().Result;
                return JObject.Parse(responseBody);
            }
            catch (Exception e)
            {
                return new JObject { ["error"] = e.Message };
            }
        }

        public static object DownloadRodinJobResult(JObject @params)
        {
            switch (SettingsManager.serviceProvider)
            {
                case ServiceProvider.MAIN_SITE:
                    return DownloadRodinJobResultMainSite(@params);
                case ServiceProvider.FAL_AI:
                    return DownloadRodinJobResultFalAi(@params);
                default:
                    return new JObject { ["error"] = "Error: Unknown Hyper3D Rodin mode!" };
            }
        }

        private static object DownloadRodinJobResultMainSite(JObject @params)
        {
            HttpClient client = new HttpClient();
            try
            {
                // Extract parameters
                string taskUuid = @params["task_uuid"]?.ToString();
                string savePath = @params["path"]?.ToString();

                if (string.IsNullOrEmpty(taskUuid) || string.IsNullOrEmpty(savePath))
                    return new JObject { ["error"] = "Missing required parameters: task_uuid or path" };

                // Prepare API request
                var request = new HttpRequestMessage(HttpMethod.Post, "https://hyperhuman.deemos.com/api/v2/download")
                {
                    Headers = { { "Authorization", $"Bearer {SettingsManager.apiKey}" } },
                    Content = new StringContent(new JObject { ["task_uuid"] = taskUuid }.ToString(), Encoding.UTF8, "application/json")
                };

                // Send request
                HttpResponseMessage response = client.SendAsync(request).Result;
                string responseBody = response.Content.ReadAsStringAsync().Result;
                JObject data = JObject.Parse(responseBody);

                // Find GLB file URL
                foreach (var item in data["list"])
                {
                    if (item["name"].ToString().EndsWith(".glb"))
                    {
                        JObject @result = JObject.FromObject(
                            DownloadFile(item["url"].ToString(), savePath + "/" + item["name"])
                        );
                        if (@result["error"] != null){
                            return result;
                        }
                    }
                }

                return new JObject { ["succeed"] = true };
            }
            catch (Exception e)
            {
                return new JObject { ["error"] = e.Message };
            }
        }

        private static object DownloadRodinJobResultFalAi(JObject @params)
        {
            HttpClient client = new HttpClient();
            try
            {
                // Extract parameters
                string requestId = @params["request_id"]?.ToString();
                string savePath = @params["path"]?.ToString();

                if (string.IsNullOrEmpty(requestId) || string.IsNullOrEmpty(savePath))
                    return new JObject { ["error"] = "Missing required parameters: request_id or path" };

                // Prepare API request
                var request = new HttpRequestMessage(HttpMethod.Get, $"https://queue.fal.run/fal-ai/hyper3d/requests/{requestId}")
                {
                    Headers = { { "Authorization", $"Key {SettingsManager.apiKey}" } }
                };

                // Send request
                HttpResponseMessage response = client.SendAsync(request).Result;
                string responseBody = response.Content.ReadAsStringAsync().Result;
                JObject data = JObject.Parse(responseBody);

                // Find GLB file URL
                string fileUrl = data["model_mesh"]?["url"]?.ToString();
                if (string.IsNullOrEmpty(fileUrl))
                    return new JObject { ["error"] = "No .glb file found in response" };

                return DownloadFile(fileUrl, savePath);
            }
            catch (Exception e)
            {
                return new JObject { ["error"] = e.Message };
            }
        }

        private static object DownloadFile(string fileUrl, string filePath)
        {
            HttpClient client = new HttpClient();
            try
            {
                // Ensure filePath starts with "Assets/"
                if (!filePath.StartsWith("Assets/"))
                    return new JObject { ["error"] = "Invalid file path. Path must start with 'Assets/'" };

                // Convert Unity-relative path to absolute system path
                string absolutePath = Path.Combine(Application.dataPath, filePath.Substring(7)); // Remove "Assets/" prefix

                // Ensure directory exists
                string directory = Path.GetDirectoryName(absolutePath);
                if (!Directory.Exists(directory))
                    Directory.CreateDirectory(directory);

                // Prepare download request
                var request = new HttpRequestMessage(HttpMethod.Get, fileUrl);
                HttpResponseMessage response = client.SendAsync(request).Result;

                if (!response.IsSuccessStatusCode)
                    return new JObject { ["error"] = $"Failed to download file. HTTP Status: {response.StatusCode}" };

                // Save file to path
                using (var fs = new FileStream(absolutePath, FileMode.Create, FileAccess.Write))
                {
                    response.Content.CopyToAsync(fs).Wait();
                }

                // Return Unity-relative path
                return new JObject { ["succeed"] = true, ["path"] = filePath };
            }
            catch (Exception e)
            {
                return new JObject { ["error"] = e.Message };
            }
        }
    }
}
#endif