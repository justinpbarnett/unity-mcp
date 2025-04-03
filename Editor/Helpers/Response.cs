using System;
using System.Collections.Generic;

namespace UnityMCP.Editor.Helpers
{
    /// <summary>
    /// Provides static methods for creating standardized success and error response objects.
    /// Ensures consistent JSON structure for communication back to the Python server.
    /// </summary>
    public static class Response
    {
        /// <summary>
        /// Creates a standardized success response object.
        /// </summary>
        /// <param name="message">A message describing the successful operation.</param>
        /// <param name="data">Optional additional data to include in the response.</param>
        /// <returns>An object representing the success response.</returns>
        public static object Success(string message, object data = null)
        {
            if (data != null)
            {
                return new { success = true, message = message, data = data };
            }
            else
            {
                return new { success = true, message = message };
            }
        }

        /// <summary>
        /// Creates a standardized error response object.
        /// </summary>
        /// <param name="errorMessage">A message describing the error.</param>
        /// <param name="data">Optional additional data (e.g., error details) to include.</param>
        /// <returns>An object representing the error response.</returns>
        public static object Error(string errorMessage, object data = null)
        {
             if (data != null)
            {
                // Note: The key is "error" for error messages, not "message"
                return new { success = false, error = errorMessage, data = data };
            }
            else
            {
                return new { success = false, error = errorMessage };
            }
        }
    }
} 