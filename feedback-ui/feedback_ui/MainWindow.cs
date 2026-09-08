using System;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shell;
using System.Windows.Threading;

namespace feedback_ui;

public class MainWindow : Window, IComponentConnector
{
	private string? _userResponse;

	private bool _cancelled;

	private bool _hasOutputResponse;

	private string? _folderPath;

	private List<string> _allFiles = new List<string>();

	private ObservableCollection<string> _filteredFiles = new ObservableCollection<string>();

	private int _autocompleteStartPosition = -1;

	private bool _isAutocompleteActive;

	private HashSet<string> _gitIgnorePatterns = new HashSet<string>();

	private List<string>? _suggestedActions;

	internal Button CopySummaryButton;

	internal RichTextBox MessageDisplay;

	internal Run MessageContent;

	internal StackPanel SuggestedActionsPanel;

	internal ItemsControl SuggestedActionsContainer;

	internal TextBox FeedbackTextBox;

	internal Popup AutocompletePopup;

	internal ListBox AutocompleteList;

	internal TextBlock PlaceholderText;

	internal Button CancelButton;

	internal Button SubmitButton;

	internal TextBlock VersionText;

	private bool _contentLoaded;

	public MainWindow()
	{
		InitializeComponent();
		base.Loaded += MainWindow_Loaded;
		base.Closing += MainWindow_Closing;
		FeedbackTextBox.TextChanged += FeedbackTextBox_TextChanged;
		base.SourceInitialized += MainWindow_SourceInitialized;
		AutocompleteList.ItemsSource = _filteredFiles;
	}

	public MainWindow(string message, string? folderPath = null, List<string>? suggestedActions = null)
		: this()
	{
		MainWindow mainWindow = this;
		_folderPath = folderPath;
		_suggestedActions = suggestedActions;
		base.Loaded += delegate
		{
			mainWindow.SetFormattedMessage(message);
			mainWindow.UpdateTitle(folderPath);
			mainWindow.SetVersionInfo();
			mainWindow.LoadFilesForAutocomplete();
			mainWindow.SetupSuggestedActions();
			if (mainWindow.MessageDisplay.Document.Blocks.Count > 0)
			{
				mainWindow.ApplyDocumentTheming(mainWindow.MessageDisplay.Document);
			}
		};
	}

	private void SetupSuggestedActions()
	{
		if (_suggestedActions == null || _suggestedActions.Count == 0)
		{
			SuggestedActionsPanel.Visibility = Visibility.Collapsed;
			return;
		}
		SuggestedActionsPanel.Visibility = Visibility.Visible;
		SuggestedActionsContainer.Items.Clear();
		foreach (string suggestedAction in _suggestedActions)
		{
			Button button = new Button
			{
				Content = suggestedAction,
				Style = (Style)FindResource("SuggestedActionButtonStyle"),
				Tag = suggestedAction
			};
			button.Click += SuggestedActionButton_Click;
			SuggestedActionsContainer.Items.Add(button);
		}
	}

	private void SuggestedActionButton_Click(object sender, RoutedEventArgs e)
	{
		if (sender is Button { Tag: string tag })
		{
			FeedbackTextBox.Text = tag;
			FeedbackTextBox.CaretIndex = FeedbackTextBox.Text.Length;
			FeedbackTextBox.Focus();
		}
	}

	private void SetFormattedMessage(string message)
	{
		try
		{
			FlowDocument flowDocument = new MarkdownConverter(true).Convert(message);
			flowDocument.FontFamily = new FontFamily("Segoe UI");
			flowDocument.FontSize = 13.0;
			flowDocument.LineHeight = 1.4;
			flowDocument.Background = Brushes.Transparent;
			MessageDisplay.Document = flowDocument;
			MessageDisplay.IsDocumentEnabled = true;
			MessageDisplay.Cursor = Cursors.IBeam;
		}
		catch (Exception ex)
		{
			FlowDocument flowDocument2 = new FlowDocument();
			flowDocument2.FontFamily = new FontFamily("Segoe UI");
			flowDocument2.FontSize = 13.0;
			flowDocument2.Foreground = (Brush)base.Resources["ForegroundBrush"];
			Paragraph paragraph = new Paragraph();
			paragraph.Foreground = (Brush)base.Resources["ForegroundBrush"];
			paragraph.Inlines.Add(new Run("Error rendering markdown: " + ex.Message + "\n\n" + message));
			flowDocument2.Blocks.Add(paragraph);
			MessageDisplay.Document = flowDocument2;
		}
	}

	private void ApplyDocumentTheming(FlowDocument document)
	{
		bool isDarkTheme = true;
		Brush foregroundBrush = (Brush)base.Resources["ForegroundBrush"];
		Brush accentBrush = (Brush)base.Resources["AccentBrush"];
		foreach (Block block in document.Blocks)
		{
			if (block is Paragraph paragraph && paragraph.Inlines.Count > 0)
			{
				int num = 0;
				foreach (Inline inline in paragraph.Inlines)
				{
					num++;
					if (inline is Run run)
					{
						if (run.Text != null && run.Text.Length > 0)
						{
							run.Text.Substring(0, Math.Min(50, run.Text.Length));
						}
					}
					else
					{
						if (!(inline is Span span))
						{
							continue;
						}
						foreach (Inline inline2 in span.Inlines)
						{
							if (inline2 is Run { Text: not null } run2 && run2.Text.Length > 0)
							{
								run2.Text.Substring(0, Math.Min(50, run2.Text.Length));
							}
						}
					}
				}
			}
			ApplyThemeToBlock(block, foregroundBrush, accentBrush, isDarkTheme);
		}
		EnsureAllContentVisible(document, isDarkTheme);
	}

	private void EnsureAllContentVisible(FlowDocument document, bool isDarkTheme)
	{
		SolidColorBrush safeTextColor = (isDarkTheme ? new SolidColorBrush(Color.FromRgb(220, 220, 220)) : new SolidColorBrush(Color.FromRgb(30, 30, 30)));
		foreach (Block block in document.Blocks)
		{
			ForceBlockVisibility(block, safeTextColor, isDarkTheme);
		}
	}

	private void ForceBlockVisibility(Block block, Brush safeTextColor, bool isDarkTheme)
	{
		if (block is Section section)
		{
			{
				foreach (Block block2 in section.Blocks)
				{
					ForceBlockVisibility(block2, safeTextColor, isDarkTheme);
				}
				return;
			}
		}
		if (block is Paragraph paragraph)
		{
			{
				foreach (Inline inline in paragraph.Inlines)
				{
					ForceInlineVisibility(inline, safeTextColor, isDarkTheme);
				}
				return;
			}
		}
		if (!(block is List list))
		{
			return;
		}
		foreach (ListItem listItem in list.ListItems)
		{
			foreach (Block block3 in listItem.Blocks)
			{
				ForceBlockVisibility(block3, safeTextColor, isDarkTheme);
			}
		}
	}

	private void ForceInlineVisibility(Inline inline, Brush safeTextColor, bool isDarkTheme)
	{
		if (inline is Run run)
		{
			if (run.Foreground is SolidColorBrush solidColorBrush && run.Background is SolidColorBrush solidColorBrush2)
			{
				Color color = solidColorBrush.Color;
				Color color2 = solidColorBrush2.Color;
				double num = (double)(color.R + color.G + color.B) / 3.0;
				double num2 = (double)(color2.R + color2.G + color2.B) / 3.0;
				if (Math.Abs(num - num2) < 50.0)
				{
					run.Foreground = safeTextColor;
				}
			}
			else if (run.Foreground == null)
			{
				run.Foreground = safeTextColor;
			}
		}
		else
		{
			if (!(inline is Span span))
			{
				return;
			}
			foreach (Inline inline2 in span.Inlines)
			{
				ForceInlineVisibility(inline2, safeTextColor, isDarkTheme);
			}
		}
	}

	private void ApplyThemeToBlock(Block block, Brush foregroundBrush, Brush accentBrush, bool isDarkTheme)
	{
		block.Foreground = foregroundBrush;
		bool flag;
		string text;
		if (block is Paragraph paragraph)
		{
			flag = false;
			bool flag2 = false;
			foreach (Inline inline in paragraph.Inlines)
			{
				if (inline is Run { Background: not null, Background: SolidColorBrush { Color: { A: >0 } } })
				{
					flag2 = true;
					break;
				}
			}
			if (!flag2 && paragraph.Inlines.Count > 1 && paragraph.Inlines.FirstInline is Run run2)
			{
				text = run2.Text?.Trim().ToLower();
				if (string.IsNullOrEmpty(text))
				{
					goto IL_01b8;
				}
				switch (text)
				{
				case "typescript":
				case "javascript":
				case "python":
				case "csharp":
				case "c#":
				case "java":
				case "html":
				case "css":
				case "json":
				case "xml":
				case "sql":
				case "bash":
				case "powershell":
				case "sh":
				case "cmd":
					break;
				default:
					goto IL_01b8;
				}
				flag = true;
			}
			goto IL_0212;
		}
		if (block is Section section)
		{
			if (isDarkTheme)
			{
				section.Background = new SolidColorBrush(Color.FromRgb(22, 27, 34));
				section.BorderBrush = new SolidColorBrush(Color.FromRgb(100, 110, 120));
			}
			else
			{
				section.Background = new SolidColorBrush(Color.FromRgb(240, 244, 248));
				section.BorderBrush = new SolidColorBrush(Color.FromRgb(180, 190, 200));
			}
			section.BorderThickness = new Thickness(2.0);
			section.Padding = new Thickness(14.0, 12.0, 14.0, 12.0);
			section.Margin = new Thickness(0.0, 12.0, 0.0, 12.0);
			{
				foreach (Block block2 in section.Blocks)
				{
					ApplyThemeToBlock(block2, foregroundBrush, accentBrush, isDarkTheme);
					if (!(block2 is Paragraph paragraph2))
					{
						continue;
					}
					paragraph2.LineHeight = 1.6;
					foreach (Inline inline2 in paragraph2.Inlines)
					{
						if (inline2 is Run run3)
						{
							run3.FontFamily = new FontFamily("Consolas, 'Courier New', monospace");
							run3.FontSize = 11.5;
							if (isDarkTheme)
							{
								run3.Foreground = new SolidColorBrush(Color.FromRgb(201, 209, 217));
							}
							else
							{
								run3.Foreground = new SolidColorBrush(Color.FromRgb(36, 41, 46));
							}
						}
						else
						{
							if (!(inline2 is Span span))
							{
								continue;
							}
							foreach (Inline inline3 in span.Inlines)
							{
								if (inline3 is Run run4)
								{
									run4.FontFamily = new FontFamily("Consolas, 'Courier New', monospace");
									run4.FontSize = 11.5;
									if (isDarkTheme)
									{
										run4.Foreground = new SolidColorBrush(Color.FromRgb(201, 209, 217));
									}
									else
									{
										run4.Foreground = new SolidColorBrush(Color.FromRgb(36, 41, 46));
									}
								}
							}
						}
					}
				}
				return;
			}
		}
		if (block is List list)
		{
			{
				foreach (ListItem listItem in list.ListItems)
				{
					foreach (Block block3 in listItem.Blocks)
					{
						ApplyThemeToBlock(block3, foregroundBrush, accentBrush, isDarkTheme);
					}
				}
				return;
			}
		}
		if (block is BlockUIContainer blockUIContainer)
		{
			if (isDarkTheme)
			{
				blockUIContainer.Background = new SolidColorBrush(Color.FromRgb(22, 27, 34));
				blockUIContainer.BorderBrush = new SolidColorBrush(Color.FromRgb(68, 77, 86));
			}
			else
			{
				blockUIContainer.Background = new SolidColorBrush(Color.FromRgb(246, 248, 250));
				blockUIContainer.BorderBrush = new SolidColorBrush(Color.FromRgb(208, 215, 222));
			}
			blockUIContainer.BorderThickness = new Thickness(1.0);
			blockUIContainer.Margin = new Thickness(0.0, 10.0, 0.0, 10.0);
		}
		else if (block is Table table)
		{
			table.BorderBrush = (Brush)base.Resources["BorderBrush"];
			table.BorderThickness = new Thickness(1.0);
		}
		return;
		IL_01b8:
		if (text != null && (text.Contains("//") || text.Contains("/*") || text.Contains("const ") || text.Contains("function") || text.Contains("var ") || text.Contains("let ")))
		{
			flag = true;
		}
		goto IL_0212;
		IL_0212:
		if (flag)
		{
			if (isDarkTheme)
			{
				paragraph.Background = new SolidColorBrush(Color.FromRgb(22, 27, 34));
				paragraph.BorderBrush = new SolidColorBrush(Color.FromRgb(100, 110, 120));
			}
			else
			{
				paragraph.Background = new SolidColorBrush(Color.FromRgb(240, 244, 248));
				paragraph.BorderBrush = new SolidColorBrush(Color.FromRgb(180, 190, 200));
			}
			paragraph.BorderThickness = new Thickness(2.0);
			paragraph.Padding = new Thickness(14.0, 12.0, 14.0, 12.0);
			paragraph.Margin = new Thickness(0.0, 12.0, 0.0, 12.0);
			paragraph.LineHeight = 1.6;
			{
				foreach (Inline inline4 in paragraph.Inlines)
				{
					if (inline4 is Run run5)
					{
						run5.FontFamily = new FontFamily("Consolas, 'Courier New', monospace");
						run5.FontSize = 11.5;
						if (isDarkTheme)
						{
							run5.Foreground = new SolidColorBrush(Color.FromRgb(201, 209, 217));
						}
						else
						{
							run5.Foreground = new SolidColorBrush(Color.FromRgb(36, 41, 46));
						}
					}
				}
				return;
			}
		}
		foreach (Inline inline5 in paragraph.Inlines)
		{
			if (inline5 is Run run6 && run6.FontWeight == FontWeights.Bold)
			{
				if (run6.FontSize > 16.0)
				{
					run6.FontSize = 14.0;
				}
				else if (run6.FontSize > 14.0)
				{
					run6.FontSize = 13.0;
				}
			}
			ApplyThemeToInline(inline5, foregroundBrush, accentBrush, isDarkTheme);
		}
	}

	private void ApplyThemeToInline(Inline inline, Brush foregroundBrush, Brush accentBrush, bool isDarkTheme)
	{
		if (inline is Span span)
		{
			{
				foreach (Inline inline2 in span.Inlines)
				{
					ApplyThemeToInline(inline2, foregroundBrush, accentBrush, isDarkTheme);
				}
				return;
			}
		}
		if (inline is Run run)
		{
			bool flag = false;
			if (run.Background != null)
			{
				flag = !(run.Background is SolidColorBrush { Color: var color }) || color.A > 0;
			}
			if (flag)
			{
				run.FontFamily = new FontFamily("Consolas, 'Courier New', monospace");
				run.FontSize = 11.5;
				if (isDarkTheme)
				{
					run.Background = new SolidColorBrush(Color.FromRgb(56, 58, 66));
					run.Foreground = new SolidColorBrush(Color.FromRgb(232, 135, 98));
				}
				else
				{
					run.Background = new SolidColorBrush(Color.FromRgb(240, 242, 245));
					run.Foreground = new SolidColorBrush(Color.FromRgb(212, 73, 80));
				}
			}
			else
			{
				inline.Foreground = foregroundBrush;
			}
		}
		else
		{
			if (!(inline is Hyperlink hyperlink))
			{
				return;
			}
			hyperlink.Foreground = accentBrush;
			foreach (Inline inline3 in hyperlink.Inlines)
			{
				ApplyThemeToInline(inline3, accentBrush, accentBrush, isDarkTheme);
			}
		}
	}

	private FlowDocument ParseMarkdown(string markdown)
	{
		FlowDocument flowDocument = new FlowDocument();
		flowDocument.FontFamily = new FontFamily("Segoe UI");
		flowDocument.FontSize = 13.0;
		flowDocument.Foreground = (Brush)base.Resources["ForegroundBrush"];
		flowDocument.LineHeight = 1.4;
		string[] array = markdown.Split('\n');
		Paragraph paragraph = null;
		bool flag = false;
		string text = "";
		string language = "";
		new Stack<string>();
		string[] array2 = array;
		foreach (string obj in array2)
		{
			string text2 = obj.Trim();
			string text3 = obj;
			if (text2.StartsWith("```"))
			{
				if (flag)
				{
					if (!string.IsNullOrEmpty(text))
					{
						AddCodeBlock(flowDocument, text.TrimEnd(), language);
					}
					flag = false;
					text = "";
					language = "";
					paragraph = null;
				}
				else
				{
					flag = true;
					language = text2.Substring(3).Trim();
					paragraph = null;
				}
			}
			else if (flag)
			{
				text = text + text3 + "\n";
			}
			else if (text2.StartsWith("# "))
			{
				AddHeader(flowDocument, text2.Substring(2), 2);
				paragraph = null;
			}
			else if (text2.StartsWith("## "))
			{
				AddHeader(flowDocument, text2.Substring(3), 3);
				paragraph = null;
			}
			else if (text2.StartsWith("### "))
			{
				AddHeader(flowDocument, text2.Substring(4), 4);
				paragraph = null;
			}
			else if (text2.StartsWith("#### "))
			{
				AddHeader(flowDocument, text2.Substring(5), 4);
				paragraph = null;
			}
			else if (Regex.IsMatch(text2, "^[\\s]*[-*+]\\s+"))
			{
				Match match = Regex.Match(text2, "^(\\s*)([-*+])\\s+(.*)");
				if (match.Success)
				{
					int length = match.Groups[1].Value.Length;
					string value = match.Groups[3].Value;
					AddListItem(flowDocument, value, "bullet", length);
				}
				paragraph = null;
			}
			else if (Regex.IsMatch(text2, "^[\\s]*\\d+\\.\\s+"))
			{
				Match match2 = Regex.Match(text2, "^(\\s*)(\\d+)\\.\\s+(.*)");
				if (match2.Success)
				{
					int length2 = match2.Groups[1].Value.Length;
					string value2 = match2.Groups[2].Value;
					string value3 = match2.Groups[3].Value;
					AddListItem(flowDocument, value3, "numbered", length2, value2);
				}
				paragraph = null;
			}
			else if (text2.StartsWith("> "))
			{
				AddBlockquote(flowDocument, text2.Substring(2));
				paragraph = null;
			}
			else if (Regex.IsMatch(text2, "^[-*_]{3,}$"))
			{
				AddHorizontalRule(flowDocument);
				paragraph = null;
			}
			else if (string.IsNullOrWhiteSpace(text2))
			{
				paragraph = null;
			}
			else
			{
				if (paragraph == null)
				{
					paragraph = new Paragraph();
					paragraph.Margin = new Thickness(0.0, 4.0, 0.0, 4.0);
					paragraph.LineHeight = 1.4;
					flowDocument.Blocks.Add(paragraph);
				}
				else
				{
					paragraph.Inlines.Add(new LineBreak());
				}
				AddFormattedText(paragraph, text3);
			}
		}
		return flowDocument;
	}

	private void AddHeader(FlowDocument document, string text, int level)
	{
		Paragraph paragraph = new Paragraph();
		Run run = new Run(text);
		switch (level)
		{
		case 1:
			run.FontSize = 15.0;
			run.FontWeight = FontWeights.Bold;
			paragraph.Margin = new Thickness(0.0, 8.0, 0.0, 4.0);
			paragraph.BorderBrush = (Brush)base.Resources["BorderBrush"];
			paragraph.BorderThickness = new Thickness(0.0, 0.0, 0.0, 1.0);
			paragraph.Padding = new Thickness(0.0, 0.0, 0.0, 4.0);
			break;
		case 2:
			run.FontSize = 14.0;
			run.FontWeight = FontWeights.Bold;
			paragraph.Margin = new Thickness(0.0, 6.0, 0.0, 3.0);
			break;
		case 3:
			run.FontSize = 13.5;
			run.FontWeight = FontWeights.Bold;
			paragraph.Margin = new Thickness(0.0, 5.0, 0.0, 2.0);
			break;
		case 4:
			run.FontSize = 13.0;
			run.FontWeight = FontWeights.Bold;
			paragraph.Margin = new Thickness(0.0, 4.0, 0.0, 2.0);
			break;
		}
		paragraph.Inlines.Add(run);
		document.Blocks.Add(paragraph);
	}

	private void AddCodeBlock(FlowDocument document, string code, string language)
	{
		bool num = ThemeDetector.ShouldUseDarkTheme();
		Section section = new Section();
		if (num)
		{
			section.Background = new SolidColorBrush(Color.FromRgb(22, 27, 34));
			section.BorderBrush = new SolidColorBrush(Color.FromRgb(68, 77, 86));
		}
		else
		{
			section.Background = new SolidColorBrush(Color.FromRgb(246, 248, 250));
			section.BorderBrush = new SolidColorBrush(Color.FromRgb(208, 215, 222));
		}
		section.BorderThickness = new Thickness(1.0);
		section.Padding = new Thickness(12.0, 10.0, 12.0, 10.0);
		section.Margin = new Thickness(0.0, 10.0, 0.0, 10.0);
		Paragraph paragraph = new Paragraph
		{
			Margin = new Thickness(0.0),
			LineHeight = 1.5
		};
		Run run = new Run(code)
		{
			FontFamily = new FontFamily("Consolas, 'Courier New', monospace"),
			FontSize = 11.5
		};
		if (num)
		{
			run.Foreground = new SolidColorBrush(Color.FromRgb(201, 209, 217));
		}
		else
		{
			run.Foreground = new SolidColorBrush(Color.FromRgb(36, 41, 46));
		}
		paragraph.Inlines.Add(run);
		section.Blocks.Add(paragraph);
		document.Blocks.Add(section);
	}

	private void AddListItem(FlowDocument document, string content, string type, int indent, string? number = null)
	{
		Paragraph paragraph = new Paragraph();
		paragraph.Margin = new Thickness(20 + indent * 20, 2.0, 0.0, 2.0);
		if (type == "bullet")
		{
			Run run = new Run("• ");
			run.FontWeight = FontWeights.Bold;
			run.Foreground = (Brush)base.Resources["AccentBrush"];
			paragraph.Inlines.Add(run);
		}
		else if (type == "numbered" && number != null)
		{
			Run run2 = new Run(number + ". ");
			run2.FontWeight = FontWeights.Bold;
			run2.Foreground = (Brush)base.Resources["AccentBrush"];
			paragraph.Inlines.Add(run2);
		}
		AddFormattedText(paragraph, content);
		document.Blocks.Add(paragraph);
	}

	private void AddBlockquote(FlowDocument document, string content)
	{
		Paragraph paragraph = new Paragraph();
		paragraph.Margin = new Thickness(20.0, 8.0, 0.0, 8.0);
		paragraph.Padding = new Thickness(16.0, 8.0, 16.0, 8.0);
		paragraph.Background = new SolidColorBrush(Color.FromRgb(246, 248, 250));
		paragraph.BorderBrush = new SolidColorBrush(Color.FromRgb(208, 215, 222));
		paragraph.BorderThickness = new Thickness(4.0, 0.0, 0.0, 0.0);
		paragraph.FontStyle = FontStyles.Italic;
		AddFormattedText(paragraph, content);
		document.Blocks.Add(paragraph);
	}

	private void AddHorizontalRule(FlowDocument document)
	{
		Paragraph paragraph = new Paragraph();
		paragraph.Margin = new Thickness(0.0, 16.0, 0.0, 16.0);
		paragraph.BorderBrush = (Brush)base.Resources["BorderBrush"];
		paragraph.BorderThickness = new Thickness(0.0, 1.0, 0.0, 0.0);
		document.Blocks.Add(paragraph);
	}

	private void AddFormattedText(Paragraph paragraph, string text)
	{
		Dictionary<string, Regex> obj = new Dictionary<string, Regex>
		{
			["code"] = new Regex("`([^`]+)`"),
			["bold"] = new Regex("\\*\\*([^*]+)\\*\\*"),
			["italic"] = new Regex("\\*([^*]+)\\*"),
			["strikethrough"] = new Regex("~~([^~]+)~~"),
			["link"] = new Regex("\\[([^\\]]+)\\]\\(([^)]+)\\)"),
			["emphasis"] = new Regex("_([^_]+)_")
		};
		List<(string, string)> list = new List<(string, string)>();
		int num = 0;
		List<(Match, string, int, int)> list2 = new List<(Match, string, int, int)>();
		foreach (KeyValuePair<string, Regex> item3 in obj)
		{
			foreach (Match item4 in item3.Value.Matches(text))
			{
				list2.Add((item4, item3.Key, item4.Index, item4.Length));
			}
		}
		list2.Sort(((Match match, string type, int start, int length) a, (Match match, string type, int start, int length) b) => a.start.CompareTo(b.start));
		foreach (var (match2, text2, num2, num3) in list2)
		{
			if (num2 > num)
			{
				string text3 = text.Substring(num, num2 - num);
				if (!string.IsNullOrEmpty(text3))
				{
					list.Add((text3, "normal"));
				}
			}
			string value = match2.Groups[1].Value;
			if (text2 == "link" && match2.Groups.Count > 2)
			{
				list.Add((value, text2));
			}
			else
			{
				list.Add((value, text2));
			}
			num = num2 + num3;
		}
		if (num < text.Length)
		{
			string text4 = text.Substring(num);
			if (!string.IsNullOrEmpty(text4))
			{
				list.Add((text4, "normal"));
			}
		}
		if (list.Count == 0)
		{
			list.Add((text, "normal"));
		}
		foreach (var item5 in list)
		{
			string item = item5.Item1;
			string item2 = item5.Item2;
			Run run = new Run(item);
			switch (item2)
			{
			case "code":
			{
				bool num4 = ThemeDetector.ShouldUseDarkTheme();
				run.FontFamily = new FontFamily("Consolas, 'Courier New', monospace");
				if (num4)
				{
					run.Background = new SolidColorBrush(Color.FromRgb(56, 58, 66));
					run.Foreground = new SolidColorBrush(Color.FromRgb(232, 135, 98));
				}
				else
				{
					run.Background = new SolidColorBrush(Color.FromRgb(240, 242, 245));
					run.Foreground = new SolidColorBrush(Color.FromRgb(212, 73, 80));
				}
				run.FontSize = 11.5;
				break;
			}
			case "bold":
				run.FontWeight = FontWeights.Bold;
				break;
			case "italic":
			case "emphasis":
				run.FontStyle = FontStyles.Italic;
				break;
			case "strikethrough":
				run.TextDecorations = TextDecorations.Strikethrough;
				break;
			case "link":
				run.Foreground = (Brush)base.Resources["AccentBrush"];
				run.TextDecorations = TextDecorations.Underline;
				run.Cursor = Cursors.Hand;
				break;
			}
			paragraph.Inlines.Add(run);
		}
	}

	private void UpdateTitle(string? folderPath)
	{
		if (!string.IsNullOrEmpty(folderPath))
		{
			base.Title = "Human-in-the-Loop Feedback - " + folderPath;
		}
		else
		{
			base.Title = "Human-in-the-Loop Feedback";
		}
	}

	private string GetBuildDate()
	{
		try
		{
			return File.GetCreationTime(AppContext.BaseDirectory).ToString("yyyy.MM.dd-HHmm");
		}
		catch
		{
			return DateTime.Now.ToString("yyyy.MM.dd-HHmm");
		}
	}

	private void SetVersionInfo()
	{
		Version version = Assembly.GetExecutingAssembly().GetName().Version;
		string buildDate = GetBuildDate();
		VersionText.Text = $"v{version?.ToString(3) ?? "1.0.0"} ({buildDate})";
	}

	private void ApplySystemTheme()
	{
		ApplyDarkTheme();
	}

	private void ApplyDarkTheme()
	{
		try
		{
			base.Resources["BackgroundBrush"] = new SolidColorBrush(Color.FromRgb(43, 43, 43));
			base.Resources["ForegroundBrush"] = new SolidColorBrush(Color.FromRgb(240, 240, 240));
			base.Resources["BorderBrush"] = new SolidColorBrush(Color.FromRgb(70, 70, 70));
			base.Resources["TextBoxBrush"] = new SolidColorBrush(Color.FromRgb(55, 55, 55));
			base.Resources["AccentBrush"] = new SolidColorBrush(Color.FromRgb(237, 64, 64));
			base.Resources["HoverBrush"] = new SolidColorBrush(Color.FromRgb(200, 50, 50));
			base.Resources["SecondaryBrush"] = new SolidColorBrush(Color.FromRgb(170, 170, 170));
			base.Resources["TitleBrush"] = new SolidColorBrush(Color.FromRgb(byte.MaxValue, byte.MaxValue, byte.MaxValue));
			base.Resources["CursorBrush"] = new SolidColorBrush(Color.FromRgb(byte.MaxValue, byte.MaxValue, byte.MaxValue));
			InvalidateVisual();
			UpdateLayout();
			if (MessageDisplay.Document.Blocks.Count > 0)
			{
				ApplyDocumentTheming(MessageDisplay.Document);
			}
		}
		catch
		{
		}
	}

	private void MainWindow_SourceInitialized(object? sender, EventArgs e)
	{
		WindowHelper.SetDarkTitleBar(this, true);
		SetThemeIcon(true);
	}

	private void SetThemeIcon(bool isDarkTheme)
	{
		try
		{
			string text = (isDarkTheme ? "user-check-dark.png" : "user-check-light.png");
			Uri uriSource = new Uri("pack://application:,,,/" + text);
			BitmapImage bitmapImage = new BitmapImage();
			bitmapImage.BeginInit();
			bitmapImage.UriSource = uriSource;
			bitmapImage.CacheOption = BitmapCacheOption.OnLoad;
			bitmapImage.EndInit();
			bitmapImage.Freeze();
			base.Icon = bitmapImage;
			base.TaskbarItemInfo = new TaskbarItemInfo
			{
				Overlay = bitmapImage
			};
		}
		catch
		{
		}
	}

	private void MainWindow_Loaded(object? sender, RoutedEventArgs e)
	{
		ApplySystemTheme();
		AddBrandingHeader();
		SetOptimalWindowSizeAndPosition();
		FeedbackTextBox.Focus();
		UpdatePlaceholderVisibility();
	}

	private void AddBrandingHeader()
	{
		var existingContent = (UIElement)this.Content;
		var wrapper = new DockPanel();

		var logo = new Image
		{
			Source = new BitmapImage(new Uri("pack://application:,,,/HITL.png")),
			Height = 36,
			Stretch = System.Windows.Media.Stretch.Uniform,
			HorizontalAlignment = HorizontalAlignment.Center,
			Margin = new Thickness(0, 6, 0, 2)
		};

		var headerBorder = new Border { Child = logo, Padding = new Thickness(12, 2, 12, 2) };
		DockPanel.SetDock(headerBorder, Dock.Top);

		var copyrightText = new TextBlock
		{
			Text = "\u00A9 Copyright HITL Solutions 2025",
			FontSize = 10,
			Foreground = new SolidColorBrush(Color.FromRgb(140, 140, 140)),
			HorizontalAlignment = HorizontalAlignment.Left,
			VerticalAlignment = VerticalAlignment.Center,
			Margin = new Thickness(12, 4, 0, 6)
		};
		var footerBorder = new Border { Child = copyrightText, Padding = new Thickness(0) };
		DockPanel.SetDock(footerBorder, Dock.Bottom);

		this.Content = null;
		wrapper.Children.Add(headerBorder);
		wrapper.Children.Add(footerBorder);
		wrapper.Children.Add(existingContent);
		this.Content = wrapper;
	}

	private void MainWindow_Closing(object? sender, CancelEventArgs e)
	{
		if (_userResponse == null && !_cancelled)
		{
			_cancelled = true;
			OutputCancellation();
		}
	}

	private void FeedbackTextBox_TextChanged(object sender, TextChangedEventArgs e)
	{
		UpdatePlaceholderVisibility();
	}

	private void UpdatePlaceholderVisibility()
	{
		PlaceholderText.Visibility = ((!string.IsNullOrEmpty(FeedbackTextBox.Text)) ? Visibility.Collapsed : Visibility.Visible);
	}

	private void SetOptimalWindowSizeAndPosition()
	{
		try
		{
			Rect workArea = SystemParameters.WorkArea;
			double width = Math.Min(Math.Max(workArea.Width * 0.9, base.MinWidth), 1200.0);
			double height = Math.Min(Math.Max(workArea.Height * 0.9, base.MinHeight), 800.0);
			base.Width = width;
			base.Height = height;
			base.Left = workArea.Left + (workArea.Width - base.Width) / 2.0;
			base.Top = workArea.Top + (workArea.Height - base.Height) / 2.0;
			if (base.Left < workArea.Left)
			{
				base.Left = workArea.Left;
			}
			if (base.Top < workArea.Top)
			{
				base.Top = workArea.Top;
			}
			if (base.Left + base.Width > workArea.Right)
			{
				base.Left = workArea.Right - base.Width;
			}
			if (base.Top + base.Height > workArea.Bottom)
			{
				base.Top = workArea.Bottom - base.Height;
			}
		}
		catch
		{
			base.WindowStartupLocation = WindowStartupLocation.CenterScreen;
		}
	}

	private void FeedbackTextBox_PreviewKeyDown(object sender, KeyEventArgs e)
	{
		if (_isAutocompleteActive && AutocompletePopup.IsOpen && _filteredFiles.Count > 0)
		{
			switch (e.Key)
			{
			case Key.Down:
				e.Handled = true;
				MoveAutocompleteSelection(1);
				break;
			case Key.Up:
				e.Handled = true;
				MoveAutocompleteSelection(-1);
				break;
			case Key.Return:
				e.Handled = true;
				SelectCurrentAutocompleteItem();
				break;
			case Key.Tab:
				e.Handled = true;
				SelectCurrentAutocompleteItem();
				break;
			case Key.Escape:
				e.Handled = true;
				HideAutocomplete();
				break;
			}
		}
	}

	private void FeedbackTextBox_KeyDown(object sender, KeyEventArgs e)
	{
		if (e.Key == Key.Return && (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control)
		{
			e.Handled = true;
			SubmitFeedback();
		}
		else if (_isAutocompleteActive && AutocompletePopup.IsOpen && e.Key == Key.Space)
		{
			HideAutocomplete();
		}
	}

	private void FeedbackTextBox_TextChanged_Autocomplete(object sender, TextChangedEventArgs e)
	{
		HandleAutocompleteTextChange();
	}

	private void LoadFilesForAutocomplete()
	{
		_allFiles.Clear();
		_gitIgnorePatterns.Clear();
		if (string.IsNullOrEmpty(_folderPath) || !Directory.Exists(_folderPath))
		{
			return;
		}
		try
		{
			LoadGitIgnorePatterns();
			string[] files = Directory.GetFiles(_folderPath, "*", SearchOption.AllDirectories);
			foreach (string path in files)
			{
				string relativePath = Path.GetRelativePath(_folderPath, path);
				if (!ShouldIgnoreFile(relativePath))
				{
					_allFiles.Add(relativePath);
				}
			}
			_allFiles.Sort();
		}
		catch (Exception)
		{
		}
	}

	private void LoadGitIgnorePatterns()
	{
		string path = Path.Combine(_folderPath, ".gitignore");
		if (!File.Exists(path))
		{
			return;
		}
		try
		{
			string[] array = File.ReadAllLines(path);
			for (int i = 0; i < array.Length; i++)
			{
				string text = array[i].Trim();
				if (!string.IsNullOrEmpty(text) && !text.StartsWith("#"))
				{
					_gitIgnorePatterns.Add(text);
				}
			}
		}
		catch (Exception)
		{
		}
	}

	private bool ShouldIgnoreFile(string relativePath)
	{
		string path = relativePath.Replace('\\', '/');
		string[] array = new string[12]
		{
			".git/", ".vs/", "node_modules/", "bin/", "obj/", "dist/", "build/", "Debug/", "Release/", ".vscode/",
			"*.tmp", "*.temp"
		};
		foreach (string pattern in array)
		{
			if (MatchesGitIgnorePattern(path, pattern))
			{
				return true;
			}
		}
		foreach (string gitIgnorePattern in _gitIgnorePatterns)
		{
			if (MatchesGitIgnorePattern(path, gitIgnorePattern))
			{
				return true;
			}
		}
		return false;
	}

	private bool MatchesGitIgnorePattern(string path, string pattern)
	{
		if (pattern.EndsWith("/"))
		{
			string text = pattern.TrimEnd('/');
			if (!path.StartsWith(text + "/") && !path.Contains("/" + text + "/"))
			{
				return path == text;
			}
			return true;
		}
		if (pattern.Contains("/"))
		{
			if (!path.StartsWith(pattern))
			{
				return path.Contains("/" + pattern);
			}
			return true;
		}
		if (pattern.Contains("*"))
		{
			string pattern2 = "^" + Regex.Escape(pattern).Replace("\\*", ".*") + "$";
			if (!Regex.IsMatch(Path.GetFileName(path), pattern2, RegexOptions.IgnoreCase))
			{
				return Regex.IsMatch(path, pattern2, RegexOptions.IgnoreCase);
			}
			return true;
		}
		if (!(Path.GetFileName(path) == pattern) && !path.EndsWith("/" + pattern))
		{
			return path.Contains("/" + pattern + "/");
		}
		return true;
	}

	private void HandleAutocompleteTextChange()
	{
		string text = FeedbackTextBox.Text;
		int caretIndex = FeedbackTextBox.CaretIndex;
		if (ShouldStartAutocomplete(text, caretIndex))
		{
			StartAutocomplete(caretIndex);
		}
		else if (_isAutocompleteActive)
		{
			if (ShouldContinueAutocomplete(text, caretIndex))
			{
				UpdateAutocompleteFilter(text, caretIndex);
			}
			else
			{
				HideAutocomplete();
			}
		}
	}

	private bool ShouldStartAutocomplete(string text, int caretIndex)
	{
		if (caretIndex == 0 || _isAutocompleteActive)
		{
			return false;
		}
		if (caretIndex > 0 && text[caretIndex - 1] == '#')
		{
			if (caretIndex != 1)
			{
				return char.IsWhiteSpace(text[caretIndex - 2]);
			}
			return true;
		}
		return false;
	}

	private bool ShouldContinueAutocomplete(string text, int caretIndex)
	{
		if (caretIndex < _autocompleteStartPosition)
		{
			return false;
		}
		string text2 = text.Substring(_autocompleteStartPosition, caretIndex - _autocompleteStartPosition);
		if (text2.StartsWith("#") && !text2.Contains(' '))
		{
			return !text2.Contains('\n');
		}
		return false;
	}

	private void StartAutocomplete(int caretIndex)
	{
		_isAutocompleteActive = true;
		_autocompleteStartPosition = caretIndex - 1;
		UpdateAutocompleteFilter(FeedbackTextBox.Text, caretIndex);
		ShowAutocomplete();
	}

	private void UpdateAutocompleteFilter(string text, int caretIndex)
	{
		string filterText = "";
		if (caretIndex > _autocompleteStartPosition + 1)
		{
			filterText = text.Substring(_autocompleteStartPosition + 1, caretIndex - _autocompleteStartPosition - 1);
		}
		_filteredFiles.Clear();
		foreach (string item in _allFiles.Where((string file) => file.Contains(filterText, StringComparison.OrdinalIgnoreCase)).Take(10).ToList())
		{
			_filteredFiles.Add(item);
		}
		if (_filteredFiles.Count > 0)
		{
			AutocompleteList.SelectedIndex = 0;
			AutocompleteList.ScrollIntoView(_filteredFiles[0]);
		}
	}

	private void ShowAutocomplete()
	{
		if (_filteredFiles.Count > 0)
		{
			AutocompletePopup.IsOpen = true;
			PositionAutocompletePopup();
		}
	}

	private void PositionAutocompletePopup()
	{
		try
		{
			TextBox feedbackTextBox = FeedbackTextBox;
			int charIndex = Math.Max(0, Math.Min(feedbackTextBox.CaretIndex, feedbackTextBox.Text.Length));
			Rect rectFromCharacterIndex = feedbackTextBox.GetRectFromCharacterIndex(charIndex);
			AutocompletePopup.PlacementTarget = feedbackTextBox;
			AutocompletePopup.Placement = PlacementMode.Relative;
			AutocompletePopup.HorizontalOffset = rectFromCharacterIndex.Left;
			AutocompletePopup.VerticalOffset = rectFromCharacterIndex.Bottom + 2.0;
			if (AutocompletePopup.IsOpen)
			{
				double originalPosition = AutocompletePopup.VerticalOffset;
				AutocompletePopup.VerticalOffset = originalPosition + 1.0;
				base.Dispatcher.BeginInvoke((Action)delegate
				{
					AutocompletePopup.VerticalOffset = originalPosition;
				}, DispatcherPriority.Background);
			}
		}
		catch (Exception)
		{
			AutocompletePopup.PlacementTarget = FeedbackTextBox;
			AutocompletePopup.Placement = PlacementMode.Bottom;
			AutocompletePopup.HorizontalOffset = 0.0;
			AutocompletePopup.VerticalOffset = 5.0;
		}
	}

	private void HideAutocomplete()
	{
		_isAutocompleteActive = false;
		AutocompletePopup.IsOpen = false;
		_autocompleteStartPosition = -1;
	}

	private void MoveAutocompleteSelection(int direction)
	{
		if (_filteredFiles.Count != 0)
		{
			int num = AutocompleteList.SelectedIndex;
			if (num < 0)
			{
				num = ((direction > 0) ? (-1) : _filteredFiles.Count);
			}
			int num2 = num + direction;
			if (num2 < 0)
			{
				num2 = _filteredFiles.Count - 1;
			}
			else if (num2 >= _filteredFiles.Count)
			{
				num2 = 0;
			}
			AutocompleteList.SelectedIndex = num2;
			if (num2 >= 0 && num2 < _filteredFiles.Count)
			{
				AutocompleteList.ScrollIntoView(_filteredFiles[num2]);
			}
		}
	}

	private void SelectCurrentAutocompleteItem()
	{
		if (AutocompleteList.SelectedItem is string fileName)
		{
			InsertFileReference(fileName);
		}
	}

	private void InsertFileReference(string fileName)
	{
		string text = FeedbackTextBox.Text;
		int caretIndex = FeedbackTextBox.CaretIndex;
		string text2 = text.Substring(0, _autocompleteStartPosition);
		string text3 = text.Substring(caretIndex);
		string text4 = "#file:" + fileName;
		string text5 = text2 + text4 + text3;
		int caretIndex2 = text2.Length + text4.Length;
		FeedbackTextBox.Text = text5;
		FeedbackTextBox.CaretIndex = caretIndex2;
		HideAutocomplete();
		FeedbackTextBox.Focus();
	}

	private void AutocompleteList_KeyDown(object sender, KeyEventArgs e)
	{
		if (e.Key == Key.Return)
		{
			e.Handled = true;
			SelectCurrentAutocompleteItem();
		}
		else if (e.Key == Key.Escape)
		{
			e.Handled = true;
			HideAutocomplete();
			FeedbackTextBox.Focus();
		}
	}

	private void AutocompleteList_MouseDoubleClick(object sender, MouseButtonEventArgs e)
	{
		if (AutocompleteList.SelectedItem is string fileName)
		{
			InsertFileReference(fileName);
		}
	}

	private void CopySummaryButton_Click(object sender, RoutedEventArgs e)
	{
		try
		{
			Clipboard.SetText(new TextRange(MessageDisplay.Document.ContentStart, MessageDisplay.Document.ContentEnd).Text);
			Button button = sender as Button;
			if (button != null)
			{
				object originalContent = button.ToolTip;
				button.ToolTip = "Copied!";
				DispatcherTimer timer = new DispatcherTimer();
				timer.Interval = TimeSpan.FromSeconds(2.0);
				timer.Tick += delegate
				{
					button.ToolTip = originalContent;
					timer.Stop();
				};
				timer.Start();
			}
		}
		catch (Exception ex)
		{
			MessageBox.Show("Failed to copy summary: " + ex.Message, "Copy Error", MessageBoxButton.OK, MessageBoxImage.Hand);
		}
	}

	private void SubmitButton_Click(object sender, RoutedEventArgs e)
	{
		SubmitFeedback();
	}

	private void SubmitFeedback()
	{
		if (!_hasOutputResponse)
		{
			_hasOutputResponse = true;
			_userResponse = FeedbackTextBox.Text.Trim();
			Console.WriteLine("MCP_RESPONSE_START");
			Console.WriteLine(_userResponse);
			Console.WriteLine("MCP_RESPONSE_END");
			base.DialogResult = true;
			Close();
		}
	}

	private void CancelButton_Click(object sender, RoutedEventArgs e)
	{
		_cancelled = true;
		OutputCancellation();
		base.DialogResult = false;
		Close();
	}

	private void OutputCancellation()
	{
		if (!_hasOutputResponse)
		{
			_hasOutputResponse = true;
			Console.WriteLine("MCP_RESPONSE_START");
			Console.WriteLine("CANCELLED");
			Console.WriteLine("MCP_RESPONSE_END");
		}
	}

	public string? GetUserResponse()
	{
		if (!_cancelled)
		{
			return _userResponse;
		}
		return null;
	}

	public bool WasCancelled()
	{
		return _cancelled;
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "9.0.14.0")]
	public void InitializeComponent()
	{
		if (!_contentLoaded)
		{
			_contentLoaded = true;
			Uri resourceLocator = new Uri("/feedback-ui;V1.2026.0317.2158;component/mainwindow.xaml", UriKind.Relative);
			Application.LoadComponent(this, resourceLocator);
		}
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "9.0.14.0")]
	[EditorBrowsable(EditorBrowsableState.Never)]
	void IComponentConnector.Connect(int connectionId, object target)
	{
		switch (connectionId)
		{
		case 1:
			CopySummaryButton = (Button)target;
			CopySummaryButton.Click += CopySummaryButton_Click;
			break;
		case 2:
			MessageDisplay = (RichTextBox)target;
			break;
		case 3:
			MessageContent = (Run)target;
			break;
		case 4:
			SuggestedActionsPanel = (StackPanel)target;
			break;
		case 5:
			SuggestedActionsContainer = (ItemsControl)target;
			break;
		case 6:
			FeedbackTextBox = (TextBox)target;
			FeedbackTextBox.KeyDown += FeedbackTextBox_KeyDown;
			FeedbackTextBox.TextChanged += FeedbackTextBox_TextChanged_Autocomplete;
			FeedbackTextBox.PreviewKeyDown += FeedbackTextBox_PreviewKeyDown;
			break;
		case 7:
			AutocompletePopup = (Popup)target;
			break;
		case 8:
			AutocompleteList = (ListBox)target;
			AutocompleteList.KeyDown += AutocompleteList_KeyDown;
			AutocompleteList.MouseDoubleClick += AutocompleteList_MouseDoubleClick;
			break;
		case 9:
			PlaceholderText = (TextBlock)target;
			break;
		case 10:
			CancelButton = (Button)target;
			CancelButton.Click += CancelButton_Click;
			break;
		case 11:
			SubmitButton = (Button)target;
			SubmitButton.Click += SubmitButton_Click;
			break;
		case 12:
			VersionText = (TextBlock)target;
			break;
		default:
			_contentLoaded = true;
			break;
		}
	}
}
