using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace feedback_ui;

public static class WindowHelper
{
	public struct MARGINS
	{
		public int cxLeftWidth;

		public int cxRightWidth;

		public int cyTopHeight;

		public int cyBottomHeight;
	}

	private const int DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19;

	private const int DWMWA_USE_IMMERSIVE_DARK_MODE = 20;

	private const int DWMWA_CAPTION_COLOR = 35;

	private const int DWMWA_TEXT_COLOR = 36;

	private const uint SWP_NOSIZE = 1u;

	private const uint SWP_NOMOVE = 2u;

	private const uint SWP_NOZORDER = 4u;

	private const uint SWP_FRAMECHANGED = 32u;

	[DllImport("dwmapi.dll")]
	private static extern int DwmSetWindowAttribute(nint hwnd, int attr, ref int attrValue, int attrSize);

	[DllImport("dwmapi.dll")]
	private static extern int DwmExtendFrameIntoClientArea(nint hWnd, ref MARGINS pMarInset);

	[DllImport("user32.dll")]
	private static extern bool SetWindowPos(nint hWnd, nint hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

	public static bool SetDarkTitleBar(Window window, bool useDarkMode)
	{
		try
		{
			nint handle = new WindowInteropHelper(window).Handle;
			if (handle == IntPtr.Zero)
			{
				return false;
			}
			int attrValue = (useDarkMode ? 1 : 0);
			int num = DwmSetWindowAttribute(handle, 20, ref attrValue, 4);
			if (num != 0)
			{
				num = DwmSetWindowAttribute(handle, 19, ref attrValue, 4);
			}
			if (useDarkMode)
			{
				int attrValue2 = 16777215;
				DwmSetWindowAttribute(handle, 36, ref attrValue2, 4);
			}
			else
			{
				int attrValue3 = 0;
				DwmSetWindowAttribute(handle, 36, ref attrValue3, 4);
			}
			SetWindowPos(handle, IntPtr.Zero, 0, 0, 0, 0, 39u);
			return num == 0;
		}
		catch
		{
			return false;
		}
	}
}
