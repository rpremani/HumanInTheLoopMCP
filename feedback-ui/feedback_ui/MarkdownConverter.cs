using System;
using System.Windows;
using System.Windows.Documents;
using System.Windows.Media;
using Markdig;
using Markdig.Syntax;
using Markdig.Syntax.Inlines;

namespace feedback_ui;

public class MarkdownConverter
{
	private readonly bool _isDarkTheme;

	private readonly SolidColorBrush _textBrush;

	private readonly SolidColorBrush _headingBrush;

	private readonly SolidColorBrush _codeBrush;

	private readonly SolidColorBrush _codeBackgroundBrush;

	private readonly SolidColorBrush _codeBorderBrush;

	private readonly SolidColorBrush _inlineCodeBrush;

	private readonly SolidColorBrush _inlineCodeBackgroundBrush;

	private readonly SolidColorBrush _linkBrush;

	public MarkdownConverter(bool isDarkTheme)
	{
		_isDarkTheme = isDarkTheme;
		if (isDarkTheme)
		{
			_textBrush = new SolidColorBrush(Color.FromRgb(220, 220, 220));
			_headingBrush = new SolidColorBrush(Color.FromRgb(byte.MaxValue, byte.MaxValue, byte.MaxValue));
			_codeBrush = new SolidColorBrush(Color.FromRgb(201, 209, 217));
			_codeBackgroundBrush = new SolidColorBrush(Color.FromRgb(22, 27, 34));
			_codeBorderBrush = new SolidColorBrush(Color.FromRgb(100, 110, 120));
			_inlineCodeBrush = new SolidColorBrush(Color.FromRgb(232, 135, 98));
			_inlineCodeBackgroundBrush = new SolidColorBrush(Color.FromRgb(56, 58, 66));
			_linkBrush = new SolidColorBrush(Color.FromRgb(88, 166, byte.MaxValue));
		}
		else
		{
			_textBrush = new SolidColorBrush(Color.FromRgb(30, 30, 30));
			_headingBrush = new SolidColorBrush(Color.FromRgb(0, 0, 0));
			_codeBrush = new SolidColorBrush(Color.FromRgb(36, 41, 46));
			_codeBackgroundBrush = new SolidColorBrush(Color.FromRgb(240, 244, 248));
			_codeBorderBrush = new SolidColorBrush(Color.FromRgb(180, 190, 200));
			_inlineCodeBrush = new SolidColorBrush(Color.FromRgb(212, 73, 80));
			_inlineCodeBackgroundBrush = new SolidColorBrush(Color.FromRgb(240, 242, 245));
			_linkBrush = new SolidColorBrush(Color.FromRgb(0, 102, 204));
		}
	}

	public FlowDocument Convert(string markdown)
	{
		FlowDocument flowDocument = new FlowDocument();
		MarkdownPipeline pipeline = new MarkdownPipelineBuilder().Build();
		foreach (Markdig.Syntax.Block item in Markdown.Parse(markdown, pipeline))
		{
			System.Windows.Documents.Block block = ConvertBlock(item);
			if (block != null)
			{
				flowDocument.Blocks.Add(block);
			}
		}
		return flowDocument;
	}

	private System.Windows.Documents.Block ConvertBlock(Markdig.Syntax.Block block)
	{
		if (!(block is HeadingBlock heading))
		{
			if (!(block is ParagraphBlock paragraph))
			{
				if (!(block is FencedCodeBlock codeBlock))
				{
					if (!(block is CodeBlock codeBlock2))
					{
						if (block is ListBlock listBlock)
						{
							return ConvertList(listBlock);
						}
						return null;
					}
					return ConvertIndentedCodeBlock(codeBlock2);
				}
				return ConvertCodeBlock(codeBlock);
			}
			return ConvertParagraph(paragraph);
		}
		return ConvertHeading(heading);
	}

	private Paragraph ConvertHeading(HeadingBlock heading)
	{
		Paragraph paragraph = new Paragraph
		{
			Foreground = _headingBrush,
			FontWeight = FontWeights.Bold,
			Margin = new Thickness(0.0, 12.0, 0.0, 6.0)
		};
		Paragraph paragraph2 = paragraph;
		paragraph2.FontSize = heading.Level switch
		{
			1 => 20, 
			2 => 18, 
			3 => 16, 
			_ => 14, 
		};
		AddInlines(paragraph, heading.Inline);
		return paragraph;
	}

	private Paragraph ConvertParagraph(ParagraphBlock paragraph)
	{
		Paragraph paragraph2 = new Paragraph
		{
			Foreground = _textBrush,
			Margin = new Thickness(0.0, 6.0, 0.0, 6.0),
			FontSize = 13.0
		};
		AddInlines(paragraph2, paragraph.Inline);
		return paragraph2;
	}

	private Section ConvertCodeBlock(FencedCodeBlock codeBlock)
	{
		Section obj = new Section
		{
			Background = _codeBackgroundBrush,
			BorderBrush = _codeBorderBrush,
			BorderThickness = new Thickness(2.0),
			Padding = new Thickness(14.0, 12.0, 14.0, 12.0),
			Margin = new Thickness(0.0, 12.0, 0.0, 12.0)
		};
		string text = codeBlock.Lines.ToString();
		Paragraph paragraph = new Paragraph
		{
			FontFamily = new FontFamily("Consolas, 'Courier New', monospace"),
			FontSize = 11.5,
			Foreground = _codeBrush,
			Margin = new Thickness(0.0),
			LineHeight = 1.6
		};
		paragraph.Inlines.Add(new Run(text));
		obj.Blocks.Add(paragraph);
		return obj;
	}

	private Section ConvertIndentedCodeBlock(CodeBlock codeBlock)
	{
		Section obj = new Section
		{
			Background = _codeBackgroundBrush,
			BorderBrush = _codeBorderBrush,
			BorderThickness = new Thickness(2.0),
			Padding = new Thickness(14.0, 12.0, 14.0, 12.0),
			Margin = new Thickness(0.0, 12.0, 0.0, 12.0)
		};
		string text = codeBlock.Lines.ToString();
		Paragraph paragraph = new Paragraph
		{
			FontFamily = new FontFamily("Consolas, 'Courier New', monospace"),
			FontSize = 11.5,
			Foreground = _codeBrush,
			Margin = new Thickness(0.0),
			LineHeight = 1.6
		};
		paragraph.Inlines.Add(new Run(text));
		obj.Blocks.Add(paragraph);
		return obj;
	}

	private List ConvertList(ListBlock listBlock)
	{
		List list = new List
		{
			Foreground = _textBrush,
			Margin = new Thickness(0.0, 6.0, 0.0, 6.0)
		};
		if (listBlock.IsOrdered)
		{
			list.MarkerStyle = TextMarkerStyle.Decimal;
		}
		else
		{
			list.MarkerStyle = TextMarkerStyle.Disc;
		}
		foreach (Markdig.Syntax.Block item in listBlock)
		{
			if (!(item is ListItemBlock listItemBlock))
			{
				continue;
			}
			ListItem listItem = new ListItem();
			foreach (Markdig.Syntax.Block item2 in listItemBlock)
			{
				System.Windows.Documents.Block block = ConvertBlock(item2);
				if (block != null)
				{
					listItem.Blocks.Add(block);
				}
			}
			list.ListItems.Add(listItem);
		}
		return list;
	}

	private void AddInlines(Paragraph paragraph, ContainerInline inlineContainer)
	{
		if (inlineContainer == null)
		{
			return;
		}
		foreach (Markdig.Syntax.Inlines.Inline item in inlineContainer)
		{
			AddInline(paragraph, item);
		}
	}

	private void AddInline(Paragraph paragraph, Markdig.Syntax.Inlines.Inline inline)
	{
		if (!(inline is LiteralInline literalInline))
		{
			if (!(inline is CodeInline codeInline))
			{
				if (!(inline is EmphasisInline emphasisInline))
				{
					if (!(inline is LinkInline linkInline))
					{
						if (!(inline is LineBreakInline))
						{
							if (!(inline is ContainerInline containerInline))
							{
								return;
							}
							{
								foreach (Markdig.Syntax.Inlines.Inline item2 in containerInline)
								{
									AddInline(paragraph, item2);
								}
								return;
							}
						}
						paragraph.Inlines.Add(new LineBreak());
					}
					else
					{
						Hyperlink hyperlink = new Hyperlink
						{
							NavigateUri = new Uri(linkInline.Url, UriKind.RelativeOrAbsolute),
							Foreground = _linkBrush
						};
						AddInlinesToHyperlink(hyperlink, linkInline);
						paragraph.Inlines.Add(hyperlink);
					}
				}
				else if (emphasisInline.DelimiterCount == 2)
				{
					Bold bold = new Bold
					{
						Foreground = _textBrush
					};
					AddInlinesToSpan(bold, emphasisInline);
					paragraph.Inlines.Add(bold);
				}
				else
				{
					Italic italic = new Italic
					{
						Foreground = _textBrush
					};
					AddInlinesToSpan(italic, emphasisInline);
					paragraph.Inlines.Add(italic);
				}
			}
			else
			{
				Run item = new Run(codeInline.Content)
				{
					FontFamily = new FontFamily("Consolas, 'Courier New', monospace"),
					FontSize = 11.5,
					Foreground = _inlineCodeBrush,
					Background = _inlineCodeBackgroundBrush
				};
				paragraph.Inlines.Add(item);
			}
		}
		else
		{
			paragraph.Inlines.Add(new Run(literalInline.Content.ToString())
			{
				Foreground = _textBrush
			});
		}
	}

	private void AddInlinesToSpan(Span span, ContainerInline container)
	{
		foreach (Markdig.Syntax.Inlines.Inline item in container)
		{
			AddInlineToSpan(span, item);
		}
	}

	private void AddInlineToSpan(Span span, Markdig.Syntax.Inlines.Inline inline)
	{
		if (!(inline is LiteralInline literalInline))
		{
			if (!(inline is ContainerInline containerInline))
			{
				return;
			}
			{
				foreach (Markdig.Syntax.Inlines.Inline item in containerInline)
				{
					AddInlineToSpan(span, item);
				}
				return;
			}
		}
		span.Inlines.Add(new Run(literalInline.Content.ToString()));
	}

	private void AddInlinesToHyperlink(Hyperlink hyperlink, ContainerInline container)
	{
		foreach (Markdig.Syntax.Inlines.Inline item in container)
		{
			AddInlineToHyperlink(hyperlink, item);
		}
	}

	private void AddInlineToHyperlink(Hyperlink hyperlink, Markdig.Syntax.Inlines.Inline inline)
	{
		if (!(inline is LiteralInline literalInline))
		{
			if (!(inline is ContainerInline containerInline))
			{
				return;
			}
			{
				foreach (Markdig.Syntax.Inlines.Inline item in containerInline)
				{
					AddInlineToHyperlink(hyperlink, item);
				}
				return;
			}
		}
		hyperlink.Inlines.Add(new Run(literalInline.Content.ToString()));
	}
}
