using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Windows.Forms;

class Launcher {
    static string Quote(string value) {
        var result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in value) {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') result.Append('\\', slashes * 2 + 1);
            else result.Append('\\', slashes);
            result.Append(c); slashes = 0;
        }
        result.Append('\\', slashes * 2).Append('"');
        return result.ToString();
    }
    [STAThread]
    static int Main(string[] args) {
        bool headless = Array.IndexOf(args, "--headless") >= 0 || Array.IndexOf(args, "--shutdown") >= 0;
        try {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            var arguments = new StringBuilder("-I -m epivra.desktop");
            foreach (string arg in args) arguments.Append(" ").Append(Quote(arg));
            var start = new ProcessStartInfo(Path.Combine(root, "runtime", "pythonw.exe"), arguments.ToString());
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.WorkingDirectory = root;
            using (var process = Process.Start(start)) {
                process.WaitForExit();
                if (process.ExitCode != 0 && !headless)
                    MessageBox.Show("Epivra could not start. Check the desktop.log file in your Epivra data folder.\n\nEpivra 无法启动，请检查数据文件夹中的 desktop.log。", "Epivra");
                return process.ExitCode;
            }
        } catch (Exception error) {
            if (!headless) MessageBox.Show(error.Message, "Epivra");
            return 1;
        }
    }
}
