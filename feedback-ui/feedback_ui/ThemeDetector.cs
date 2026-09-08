using System;
using Microsoft.Win32;

namespace feedback_ui;

public static class ThemeDetector
{
	public static void DebugThemeInfo()
	{
		try
		{
			Console.WriteLine("=== Theme Detection Debug ===");
			using (RegistryKey registryKey = Registry.CurrentUser.OpenSubKey("Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize"))
			{
				if (registryKey != null)
				{
					object value = registryKey.GetValue("AppsUseLightTheme");
					object value2 = registryKey.GetValue("SystemUsesLightTheme");
					Console.WriteLine($"AppsUseLightTheme: {value}");
					Console.WriteLine($"SystemUsesLightTheme: {value2}");
					bool value3 = value != null && (int)value == 0;
					bool value4 = value2 != null && (int)value2 == 0;
					Console.WriteLine($"Apps Dark Mode: {value3}");
					Console.WriteLine($"System Dark Mode: {value4}");
					Console.WriteLine("All registry values:");
					string[] valueNames = registryKey.GetValueNames();
					foreach (string text in valueNames)
					{
						object value5 = registryKey.GetValue(text);
						Console.WriteLine($"  {text} = {value5} (type: {value5?.GetType().Name})");
					}
				}
				else
				{
					Console.WriteLine("Could not access theme registry key");
				}
			}
			Console.WriteLine("=== End Debug ===");
		}
		catch (Exception ex)
		{
			Console.WriteLine("Theme debug error: " + ex.Message);
		}
	}

	public static bool ShouldUseDarkTheme()
	{
		try
		{
			using RegistryKey registryKey = Registry.CurrentUser.OpenSubKey("Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize");
			if (registryKey != null)
			{
				object value = registryKey.GetValue("AppsUseLightTheme");
				return value != null && (int)value == 0;
			}
		}
		catch
		{
		}
		return false;
	}
}
