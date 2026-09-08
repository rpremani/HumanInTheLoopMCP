using System;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text.Json;
using System.Windows;

namespace feedback_ui;

public class App : Application
{
	protected override void OnStartup(StartupEventArgs e)
	{
		base.OnStartup(e);
		string message = "## **\ud83c\udf89 Improved Log File Naming - COMPLETE! \ud83c\udf89**\n\n### **✅ What's Been Improved:**\n\nUpdated RequestLogger to create **meaningful, descriptive filenames** based on the API endpoint, making it easy to identify what each log file contains at a glance!\n\n### **\ud83d\udccb New Filename Patterns:**\n\n#### **Harness Logs** (`/harness/`):\n- `01_execute_DOE_K8S_Rolling_Deploy.json` - Pipeline execution trigger\n- `02_execution_v2_AJZZkW-5RM_summary.json` - Execution status summary\n- `03_execution_v2_AJZZkW-5RM_detailed.json` - Detailed execution with stage info\n- `04_approval_harness_activity.json` - Approval API call\n- `05_execution_v2_AJZZkW-5RM_summary.json` - Final status check\n\n#### **OpenShift Logs** (`/openshift/`):\n- `01_1mri-sit_mri-explainabilityagent.json` - Deployment info from namespace\n- `02_1mri-dev2_mri-explainabilityagent.json` - Another deployment\n\n#### **GitHub Logs** (`/github/`):\n- `01_workflow_runs_aida-ui.json` - Workflow runs for repo\n- `02_run_jobs_12345.json` - Jobs for specific run\n- `03_job_logs_67890.json` - Logs for specific job\n\n### **\ud83c\udfaf Key Improvements:**\n\n1. **Harness Approvals**: Now shows `approval_harness_activity` instead of `response`\n2. **Execution Tracking**: Distinguishes between:\n   - `execution_v2_XXX_summary` - Basic status check\n   - `execution_v2_XXX_detailed` - Full execution graph with stage info\n3. **Pipeline Executions**: Shows stage identifier like `execute_DOE_K8S_Rolling_Deploy`\n4. **Fallback Logic**: For unknown patterns, extracts last 2-3 URL segments\n\n### **\ud83d\ude80 Benefits:**\n\n- **Quick Identification**: Know what each file contains without opening it\n- **Easier Debugging**: Find specific API calls instantly\n- **Better Organization**: Related logs grouped by execution ID\n- **Detailed Tracking**: See the full API call sequence at a glance\n\n### **\ud83d\udcdd Example Log Structure:**\n\n```\nlogs/2025-12-24/15-44-12_e8afd4992a2f21a1/\n  ├── index.json\n  ├── general.json\n  ├── harness/\n  │   ├── 01_execute_DOE_K8S_Rolling_Deploy.json\n  │   ├── 02_execution_v2_VYojkSDLQP_summary.json\n  │   ├── 03_execution_v2_VYojkSDLQP_detailed.json\n  │   ├── 04_approval_harness_activity.json\n  │   └── 05_execution_v2_VYojkSDLQP_summary.json\n  ├── openshift/\n  │   ├── 01_1mri-sit_mri-explainabilityagent.json\n  │   └── 02_1mri-sit2_mri-explainabilityagent.json\n  └── github/\n      └── 01_workflow_runs_aida-ui.json\n```\n\n**Now you can easily see what's happening just by looking at the file names!** \ud83c\udf89\n\n**Ready to test with the new naming?** Restart backend and run another deployment!";
		string folderPath = null;
		List<string> suggestedActions = null;
		if (e.Args.Length != 0)
		{
			message = e.Args[0];
			if (e.Args.Length > 1)
			{
				folderPath = e.Args[1];
			}
			if (e.Args.Length > 2)
			{
				try
				{
					suggestedActions = JsonSerializer.Deserialize<List<string>>(e.Args[2]);
				}
				catch (JsonException)
				{
					suggestedActions = null;
				}
			}
		}
		new MainWindow(message, folderPath, suggestedActions).ShowDialog();
		Shutdown();
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "9.0.14.0")]
	public void InitializeComponent()
	{
		base.StartupUri = new Uri("MainWindow.xaml", UriKind.Relative);
	}

	[STAThread]
	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "9.0.14.0")]
	public static void Main()
	{
		App app = new App();
		app.InitializeComponent();
		app.Run();
	}
}
